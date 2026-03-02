"""MNI 2.2.2 SOAP client for electronic filing with Brazilian courts.

Uses zeep for SOAP/WSDL communication and mTLS via A1 ICP-Brasil certificates.
Key MNI 2.2.2 rules:
  - numeroProcesso: 20 pure digits (no dots/dashes)
  - Initial petition: "00000000000000000000" (20 zeros)
  - Documents: base64Binary (changed from hexBinary in v2.2.2)
  - orgaoJulgador: required (code, name, instance, IBGE municipality)
  - polo[]: required (AT=ativo, PA=passivo) with partes and advogados
  - assunto[]: required (codigoNacional per TPU/CNJ)
  - idManifestante: pure CPF digits
"""

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
from zeep import Client as ZeepClient
from zeep.cache import SqliteCache
from zeep.transports import Transport

from app.config import settings
from app.core.services.certificados.crypto import CertificateCryptoService

logger = logging.getLogger(__name__)

# TNU codes per Resolução CNJ 46 — mapped to TipoDocumento enum values
TNU_CODES = {
    "peticao_principal": "60",   # Petição
    "procuracao": "37",          # Procuração
    "anexo": "41",               # Documento
    "comprovante": "41",         # Documento
}


@dataclass
class MniFilingResult:
    """Result of entregarManifestacaoProcessual call."""
    sucesso: bool
    numero_protocolo: Optional[str] = None
    recibo_base64: Optional[str] = None
    mensagem: str = ""
    dados_resposta: dict = field(default_factory=dict)


# ─── Helpers: JSON → zeep SOAP structures ──────────────────────────────────────


def _build_pessoa(p: dict) -> dict:
    """Convert Pessoa JSON → tipoPessoa MNI."""
    pessoa = {
        "nome": p["nome"],
        "tipoPessoa": p.get("tipo_pessoa", "fisica"),
        "sexo": p.get("sexo", "D"),
        "nacionalidade": p.get("nacionalidade", "BR"),
    }
    cpf = p.get("cpf")
    cnpj = p.get("cnpj")
    if cpf:
        pessoa["numeroDocumentoPrincipal"] = cpf.replace(".", "").replace("-", "")
    elif cnpj:
        pessoa["numeroDocumentoPrincipal"] = cnpj.replace(".", "").replace("-", "").replace("/", "")
    if p.get("data_nascimento"):
        pessoa["dataNascimento"] = p["data_nascimento"]
    if p.get("nome_genitor"):
        pessoa["nomeGenitor"] = p["nome_genitor"]
    if p.get("nome_genitora"):
        pessoa["nomeGenitora"] = p["nome_genitora"]
    return pessoa


def _build_advogado(a: dict) -> dict:
    """Convert Advogado JSON → tipoRepresentanteProcessual MNI."""
    adv = {
        "nome": a["nome"],
        "intimacao": a.get("intimacao", True),
        "tipoRepresentante": a.get("tipo_representante", "A"),
    }
    if a.get("inscricao_oab"):
        adv["inscricao"] = a["inscricao_oab"]
    if a.get("cpf"):
        adv["numeroDocumentoPrincipal"] = a["cpf"].replace(".", "").replace("-", "")
    return adv


def _build_polo(polo_json: dict) -> dict:
    """Convert Polo JSON → tipoPoloProcessual MNI."""
    partes_mni = []
    for p in polo_json.get("partes", []):
        parte = {"pessoa": _build_pessoa(p)}
        partes_mni.append(parte)

    advogados = polo_json.get("advogados", [])
    if advogados and partes_mni:
        # Advogados são vinculados à primeira parte do polo
        partes_mni[0]["advogado"] = [_build_advogado(a) for a in advogados]

    return {
        "polo": polo_json["polo"],  # AT, PA, TC, etc.
        "parte": partes_mni,
    }


def _build_assunto(a: dict) -> dict:
    """Convert AssuntoProcessual JSON → tipoAssuntoProcessual MNI."""
    return {
        "codigoNacional": a["codigo_nacional"],
        "principal": a.get("principal", False),
    }


def _build_orgao_julgador(oj: dict) -> dict:
    """Convert OrgaoJulgador JSON → tipoOrgaoJulgador MNI."""
    return {
        "codigoOrgao": str(oj["codigo_orgao"]),
        "nomeOrgao": oj["nome_orgao"],
        "codigoMunicipioIBGE": int(oj["codigo_municipio_ibge"]),
        "instancia": oj.get("instancia", "ORIG"),
    }


def build_dados_basicos(
    dados_json: dict,
    numero_processo: str,
) -> dict:
    """Build tipoCabecalhoProcesso from dados_basicos_json + numero_processo."""
    db = {
        "numero": numero_processo,
        "classeProcessual": dados_json.get("classe_processual", 60),
        "codigoLocalidade": dados_json.get("codigo_localidade", "0001"),
        "competencia": dados_json.get("competencia", 0),
        "nivelSigilo": dados_json.get("nivel_sigilo", 0),
        "dataAjuizamento": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    }

    # polo[] — obrigatório
    polos = dados_json.get("polos", [])
    if polos:
        db["polo"] = [_build_polo(p) for p in polos]

    # assunto[] — obrigatório
    assuntos = dados_json.get("assuntos", [])
    if assuntos:
        db["assunto"] = [_build_assunto(a) for a in assuntos]

    # orgaoJulgador — obrigatório
    oj = dados_json.get("orgao_julgador")
    if oj:
        db["orgaoJulgador"] = _build_orgao_julgador(oj)

    # Opcionais
    if dados_json.get("valor_causa") is not None:
        db["valorCausa"] = dados_json["valor_causa"]
    if dados_json.get("prioridade"):
        db["prioridade"] = dados_json["prioridade"]

    return db


class MniSoapClient:
    """
    SOAP client for MNI 2.2.2 protocol.

    Creates a new zeep Client per call to avoid stale session issues.
    mTLS handled via CertificateCryptoService.mtls_tempfiles().
    """

    def __init__(self, crypto: CertificateCryptoService):
        self.crypto = crypto

    def consultar_processo(
        self,
        *,
        wsdl_url: str,
        pfx_encrypted: bytes,
        pfx_password_encrypted: bytes,
        numero_processo: str,
        id_consultante: str,
    ) -> dict:
        """
        Consult a process via MNI consultarProcesso.

        Args:
            wsdl_url: Tribunal WSDL endpoint
            pfx_encrypted: Fernet-encrypted PFX bytes
            pfx_password_encrypted: Fernet-encrypted PFX password
            numero_processo: 20-digit process number
            id_consultante: CPF digits (no dots)

        Returns:
            Dict with response data
        """
        numero_normalizado = self._normalize_processo(numero_processo)

        with self.crypto.mtls_tempfiles(pfx_encrypted, pfx_password_encrypted) as (
            cert_path, key_path,
        ):
            client = self._create_client(wsdl_url, cert_path, key_path)

            try:
                resposta = client.service.consultarProcesso(
                    idConsultante=id_consultante,
                    senhaConsultante="",
                    numeroProcesso=numero_normalizado,
                    movimentos=True,
                    incluirCabecalho=True,
                    incluirDocumentos=False,
                )

                return {
                    "sucesso": getattr(resposta, "sucesso", False),
                    "mensagem": str(getattr(resposta, "mensagem", "")),
                    "processo": self._serialize_zeep(resposta),
                }
            except Exception as e:
                logger.error("consultarProcesso failed", extra={"url": wsdl_url, "error": str(e)})
                return {"sucesso": False, "mensagem": f"Erro: {e}"}

    def entregar_manifestacao_processual(
        self,
        *,
        wsdl_url: str,
        pfx_encrypted: bytes,
        pfx_password_encrypted: bytes,
        id_manifestante: str,
        numero_processo: str,
        documentos: list[dict],
        dados_basicos_json: Optional[dict] = None,
        classe_processual: int = 60,
        sigilo: int = 0,
    ) -> MniFilingResult:
        """
        Send entregarManifestacaoProcessual SOAP call.

        Args:
            wsdl_url: Tribunal WSDL endpoint
            pfx_encrypted: Fernet-encrypted PFX bytes
            pfx_password_encrypted: Fernet-encrypted PFX password
            id_manifestante: CPF digits (no dots)
            numero_processo: 20-digit string, "00000000000000000000" for initial
            documentos: List of {conteudo: bytes, nome: str, tipo_documento: str}
            dados_basicos_json: Full MNI dadosBasicos from petition DB
            classe_processual: Classe processual code (fallback if dados_basicos_json missing)
            sigilo: Secrecy level (0-5) (fallback if dados_basicos_json missing)

        Returns:
            MniFilingResult with protocol number and receipt
        """
        numero_normalizado = self._normalize_processo(numero_processo)

        with self.crypto.mtls_tempfiles(pfx_encrypted, pfx_password_encrypted) as (
            cert_path, key_path,
        ):
            client = self._create_client(wsdl_url, cert_path, key_path)

            # Build document list per tipoDocumento from WSDL schema
            docs_mni = []
            for i, doc in enumerate(documentos):
                tnu_code = TNU_CODES.get(doc.get("tipo_documento", "anexo"), "41")

                docs_mni.append({
                    "idDocumento": str(i + 1),
                    "tipoDocumento": tnu_code,
                    "descricao": doc.get("nome", f"Documento {i + 1}"),
                    "nivelSigilo": sigilo,
                    "mimetype": "application/pdf",
                    "dataHora": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
                    "conteudo": doc["conteudo"],  # bytes — zeep handles base64Binary
                })

            # Build dadosBasicos from stored JSON or fallback to minimal
            if dados_basicos_json:
                dados_basicos = build_dados_basicos(dados_basicos_json, numero_normalizado)
            else:
                dados_basicos = {
                    "classeProcessual": classe_processual,
                    "codigoLocalidade": "0001",
                    "competencia": 0,
                    "nivelSigilo": sigilo,
                    "numero": numero_normalizado,
                }

            try:
                resposta = client.service.entregarManifestacaoProcessual(
                    idManifestante=id_manifestante,
                    senhaManifestante="",
                    numeroProcesso=numero_normalizado,
                    dadosBasicos=dados_basicos,
                    documento=docs_mni,
                    dataEnvio=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
                )

                sucesso = getattr(resposta, "sucesso", False)
                mensagem = str(getattr(resposta, "mensagem", ""))
                protocolo = str(getattr(resposta, "protocolo", "")) if sucesso else None
                recibo = None

                if sucesso and hasattr(resposta, "recibo") and resposta.recibo:
                    try:
                        recibo = base64.b64encode(resposta.recibo).decode("ascii")
                    except Exception:
                        recibo = str(resposta.recibo)

                logger.info(
                    "entregarManifestacaoProcessual completed",
                    extra={
                        "url": wsdl_url,
                        "sucesso": sucesso,
                        "protocolo": protocolo,
                        "processo": numero_normalizado,
                    },
                )

                return MniFilingResult(
                    sucesso=sucesso,
                    numero_protocolo=protocolo,
                    recibo_base64=recibo,
                    mensagem=mensagem,
                )

            except Exception as e:
                logger.error(
                    "entregarManifestacaoProcessual failed",
                    extra={"url": wsdl_url, "error": str(e)},
                )
                return MniFilingResult(
                    sucesso=False,
                    mensagem=f"Erro SOAP: {type(e).__name__}: {e}",
                )

    def _create_client(self, wsdl_url: str, cert_path: str, key_path: str) -> ZeepClient:
        """Create a zeep SOAP client with mTLS session."""
        session = requests.Session()
        session.cert = (cert_path, key_path)
        session.verify = True
        session.timeout = settings.mni_request_timeout

        transport = Transport(
            session=session,
            timeout=settings.mni_request_timeout,
            cache=SqliteCache(
                path=settings.mni_wsdl_cache_path or "/tmp/zeep_cache.db",
                timeout=3600,
            ),
        )

        return ZeepClient(wsdl_url, transport=transport)

    def _normalize_processo(self, numero: str) -> str:
        """Strip formatting from process number to get 20 pure digits."""
        clean = numero.replace(".", "").replace("-", "").replace(" ", "")
        if len(clean) != 20 or not clean.isdigit():
            raise ValueError(
                f"numeroProcesso deve ter 20 dígitos numéricos, recebido: '{numero}' → '{clean}'"
            )
        return clean

    def _serialize_zeep(self, obj) -> dict:
        """Convert zeep response to plain dict."""
        from zeep.helpers import serialize_object
        try:
            return serialize_object(obj, dict)
        except Exception:
            return {"raw": str(obj)}

    @staticmethod
    def parse_consulta_response(raw: dict) -> dict:
        """Parse raw zeep consultarProcesso response into structured fields.

        Extracts cabecalho, polos, assuntos, orgaoJulgador, movimentos, documentos
        from the serialized zeep dict. Returns a dict matching ProcessoConsultaResponse schema.
        """
        POLO_LABELS = {
            "AT": "Ativo", "PA": "Passivo", "TC": "Terceiro",
            "FL": "Fiscal da Lei", "AD": "Amicus Curiae", "VI": "Vítima",
            "TJ": "Testemunha do Juízo",
        }

        sucesso = raw.get("sucesso", False)
        mensagem = raw.get("mensagem", "")
        processo = raw.get("processo", {}) or {}

        if not sucesso or not processo:
            return {
                "sucesso": sucesso,
                "mensagem": mensagem,
                "raw": raw,
            }

        # --- dadosBasicos / cabecalho ---
        dados = processo.get("dadosBasicos") or {}
        cabecalho = {
            "numero": dados.get("numero"),
            "classe_processual": dados.get("classeProcessual"),
            "codigo_localidade": dados.get("codigoLocalidade"),
            "competencia": dados.get("competencia"),
            "nivel_sigilo": dados.get("nivelSigilo", 0),
            "data_ajuizamento": dados.get("dataAjuizamento"),
            "valor_causa": dados.get("valorCausa"),
        }

        # --- polos ---
        polos_raw = dados.get("polo") or []
        if isinstance(polos_raw, dict):
            polos_raw = [polos_raw]
        polos = []
        for polo_item in polos_raw:
            polo_tipo = polo_item.get("polo", "")
            partes_raw = polo_item.get("parte") or []
            if isinstance(partes_raw, dict):
                partes_raw = [partes_raw]
            partes = []
            for parte in partes_raw:
                pessoa = parte.get("pessoa") or {}
                advogados_raw = parte.get("advogado") or []
                if isinstance(advogados_raw, dict):
                    advogados_raw = [advogados_raw]
                advogados = []
                for adv in advogados_raw:
                    advogados.append({
                        "nome": adv.get("nome", ""),
                        "inscricao": adv.get("inscricao"),
                        "cpf": adv.get("numeroDocumentoPrincipal"),
                        "tipo_representante": adv.get("tipoRepresentante"),
                    })
                partes.append({
                    "nome": pessoa.get("nome", ""),
                    "documento": pessoa.get("numeroDocumentoPrincipal"),
                    "tipo_pessoa": pessoa.get("tipoPessoa"),
                    "sexo": pessoa.get("sexo"),
                    "advogados": advogados,
                })
            polos.append({
                "polo": polo_tipo,
                "polo_label": POLO_LABELS.get(polo_tipo, polo_tipo),
                "partes": partes,
            })

        # --- assuntos ---
        assuntos_raw = dados.get("assunto") or []
        if isinstance(assuntos_raw, dict):
            assuntos_raw = [assuntos_raw]
        assuntos = []
        for a in assuntos_raw:
            assuntos.append({
                "codigo_nacional": a.get("codigoNacional"),
                "codigo_local": a.get("codigoLocalidade") or a.get("assuntoLocal", {}).get("codigoPaiNacional") if isinstance(a.get("assuntoLocal"), dict) else None,
                "descricao": a.get("descricao") or (a.get("assuntoLocal", {}).get("descricao") if isinstance(a.get("assuntoLocal"), dict) else None),
                "principal": a.get("principal", False),
            })

        # --- orgaoJulgador ---
        oj = dados.get("orgaoJulgador") or {}
        orgao_julgador = None
        if oj:
            orgao_julgador = {
                "codigo_orgao": str(oj.get("codigoOrgao", "")),
                "nome_orgao": oj.get("nomeOrgao", ""),
                "codigo_municipio_ibge": oj.get("codigoMunicipioIBGE"),
                "instancia": oj.get("instancia"),
            }

        # --- movimentos ---
        movimentos_raw = processo.get("movimento") or []
        if isinstance(movimentos_raw, dict):
            movimentos_raw = [movimentos_raw]
        movimentos = []
        for m in movimentos_raw:
            complementos = []
            compl_raw = m.get("complemento") or []
            if isinstance(compl_raw, dict):
                compl_raw = [compl_raw]
            for c in compl_raw:
                desc = c.get("descricao") or c.get("valor") or str(c)
                complementos.append(desc)

            mov_nac = m.get("movimentoNacional") or {}
            mov_local = m.get("movimentoLocal") or {}
            codigo = mov_nac.get("codigoNacional") if mov_nac else None
            descricao = mov_nac.get("descricao") or mov_local.get("descricao") or ""

            movimentos.append({
                "data_hora": m.get("dataHora"),
                "codigo_nacional": codigo,
                "descricao": descricao,
                "complementos": complementos,
            })

        # --- documentos (metadata only) ---
        docs_raw = processo.get("documento") or []
        if isinstance(docs_raw, dict):
            docs_raw = [docs_raw]
        documentos = []
        for d in docs_raw:
            documentos.append({
                "id_documento": d.get("idDocumento"),
                "tipo_documento": d.get("tipoDocumento"),
                "descricao": d.get("descricao"),
                "mimetype": d.get("mimetype"),
                "data_hora": d.get("dataHora"),
                "nivel_sigilo": d.get("nivelSigilo"),
            })

        return {
            "sucesso": sucesso,
            "mensagem": mensagem,
            "cabecalho": cabecalho,
            "polos": polos,
            "assuntos": assuntos,
            "orgao_julgador": orgao_julgador,
            "movimentos": movimentos,
            "documentos": documentos,
            "raw": raw,
        }

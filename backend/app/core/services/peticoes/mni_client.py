"""MNI 2.2.2 SOAP client for electronic filing with Brazilian courts.

Uses zeep for SOAP/WSDL communication and mTLS via A1 ICP-Brasil certificates.
Key MNI 2.2.2 rules:
  - numeroProcesso: 20 pure digits (no dots/dashes)
  - Initial petition: "00000000000000000000" (20 zeros)
  - Documents: base64Binary (changed from hexBinary in v2.2.2)
  - orgaoJulgador: required (code, name, instance)
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
            classe_processual: Classe processual code (default 60 = Petição)
            sigilo: Secrecy level (0-5)

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

            # Build dadosBasicos (tipoCabecalhoProcesso) — required by MNI 2.2.2
            dados_basicos = {
                "classeProcessual": classe_processual,
                "codigoLocalidade": "0001",  # Default
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

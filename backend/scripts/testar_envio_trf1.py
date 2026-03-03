"""
Testa entregarManifestacaoProcessual no TRF1.

Processo: 1000654-37.2026.4.01.3704
PDF: docs/chamamento ALAN CÁSSIO JORGE DE MELO.pdf
Certificado: Amanda (CPF 07071649316, OAB 50784 CE)

Usa WSDL local + override de service address (TRF1 retorna 403 no download WSDL).
Reutiliza a mesma lógica do mni_client.py do backend.

Uso:
    cd backend
    poetry run python3 scripts/testar_envio_trf1.py
"""

import base64
import glob as _glob
import hashlib
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
from cryptography import x509

try:
    from zeep import Client as ZeepClient, Settings as ZeepSettings
    from zeep.transports import Transport
    from zeep.cache import SqliteCache
    from zeep.helpers import serialize_object
except ImportError:
    print("ERRO: zeep não instalado. Execute: poetry install")
    sys.exit(1)


# ─── Config ──────────────────────────────────────────────────────────────────

PROCESSO = "1000654-37.2026.4.01.3704"
PROCESSO_20 = PROCESSO.replace(".", "").replace("-", "")  # 10006543720264013704

# TRF1 PJe 1ª instância — WSDL retorna 403, usaremos WSDL local
WSDL_TRF1_1G = "https://pje1g.trf1.jus.br/pje/intercomunicacao?wsdl"
SERVICE_URL_TRF1_1G = "https://pje1g.trf1.jus.br/pje/intercomunicacao"

# Local WSDL/XSD path (docs/intercomunicacao-2.2.2/)
PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
LOCAL_WSDL_DIR = PROJECT_ROOT / "docs" / "intercomunicacao-2.2.2"

# Certificado Amanda
PFX_PATH = str(PROJECT_ROOT / "docs" / "Amanda Alves de Sousa_07071649316.pfx")
PFX_SENHA = "22051998"
AMANDA_CPF = "07071649316"

# PDF a enviar
_pdf_candidates = _glob.glob(str(PROJECT_ROOT / "docs" / "chamamento*ALAN*.pdf"))
PDF_PATH = _pdf_candidates[0] if _pdf_candidates else ""

TIMEOUT = 60


# ─── Helpers ─────────────────────────────────────────────────────────────────

def extrair_pfx(pfx_path: str, senha: str) -> tuple[str, str, str]:
    """Extrai cert e key PEM do PFX."""
    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, senha.encode() if senha else b"")
    cert_pem = pkcs.cert.certificate.public_bytes(Encoding.PEM)
    key_pem = pkcs.key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    try:
        cn = pkcs.cert.certificate.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        titular = cn[0].value if cn else "Desconhecido"
    except Exception:
        titular = "Desconhecido"
    not_after = pkcs.cert.certificate.not_valid_after_utc
    print(f"  Certificado válido até: {not_after}")

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem); os.close(cert_fd)
    os.write(key_fd, key_pem); os.close(key_fd)
    os.chmod(key_path, 0o600)
    return cert_path, key_path, titular


def limpar_tempfiles(*paths: str):
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, "wb") as f:
                    f.write(b"\x00" * os.path.getsize(p))
                os.unlink(p)
        except Exception:
            pass


def criar_client_local_wsdl(service_url: str, cert_path: str, key_path: str) -> ZeepClient:
    """Cria zeep client usando WSDL LOCAL e override do service address.
    Mesma lógica do MniSoapClient._create_client_from_local_wsdl do backend.
    """
    session = requests.Session()
    session.cert = (cert_path, key_path)
    session.verify = True
    session.timeout = TIMEOUT

    transport = Transport(
        session=session,
        timeout=TIMEOUT,
        cache=SqliteCache(path="/tmp/trf1_envio_cache.db", timeout=3600),
    )

    # strict=False ignora <xsd:any> obrigatório em tipoDocumento
    zeep_settings = ZeepSettings(strict=False, xml_huge_tree=True)

    # Tentar remoto primeiro
    try:
        client = ZeepClient(WSDL_TRF1_1G, transport=transport, settings=zeep_settings)
        print(f"  WSDL remoto carregado OK")
        return client
    except Exception as e:
        print(f"  WSDL remoto falhou ({e.__class__.__name__}), usando WSDL local...")

    # Fallback: WSDL local com paths corrigidos
    local_wsdl = LOCAL_WSDL_DIR / "servico-intercomunicacao-2.2.2.wsdl"
    if not local_wsdl.exists():
        raise FileNotFoundError(f"WSDL local não encontrado: {local_wsdl}")

    wsdl_text = local_wsdl.read_text(encoding="utf-8")
    wsdl_text = wsdl_text.replace('../xsd/', './')  # XSD estão no mesmo dir

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".wsdl", dir=str(LOCAL_WSDL_DIR),
        delete=False, encoding="utf-8",
    ) as tmp:
        tmp.write(wsdl_text)
        tmp_path = tmp.name

    try:
        client = ZeepClient(f"file://{tmp_path}", transport=transport, settings=zeep_settings)
        # Override service address para o endpoint real do TRF1
        client.service._binding_options["address"] = service_url
        print(f"  WSDL local carregado, service address → {service_url}")
        ops = [op for op in client.service._operations]
        print(f"  Operações: {', '.join(ops)}")
        return client
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─── Step 1: Consultar processo ──────────────────────────────────────────────

def testar_consulta(client: ZeepClient) -> bool:
    print(f"\n{'='*60}")
    print("STEP 1: consultarProcesso (leitura)")
    print(f"{'='*60}")
    print(f"Processo: {PROCESSO} → {PROCESSO_20}")

    t0 = time.monotonic()
    try:
        resp = client.service.consultarProcesso(
            idConsultante=AMANDA_CPF,
            senhaConsultante="",
            numeroProcesso=PROCESSO_20,
            movimentos=False,
            incluirCabecalho=True,
            incluirDocumentos=False,
        )
        latencia = int((time.monotonic() - t0) * 1000)
        data = serialize_object(resp, dict)
        sucesso = data.get("sucesso", False)
        mensagem = data.get("mensagem", "")

        print(f"  Sucesso: {sucesso}")
        print(f"  Mensagem: {mensagem}")
        print(f"  Latência: {latencia}ms")

        if sucesso:
            processo = data.get("processo", {})
            if processo:
                cab = processo.get("dadosBasicos", {})
                if cab:
                    print(f"  Classe processual: {cab.get('classeProcessual')}")
                    oj = cab.get("orgaoJulgador", {})
                    if oj:
                        print(f"  Órgão julgador: {oj.get('nomeOrgao')} (cód: {oj.get('codigoOrgao')})")
                    polos = cab.get("polo", [])
                    if not isinstance(polos, list):
                        polos = [polos]
                    for polo in polos:
                        tipo = polo.get("polo", "?")
                        partes = polo.get("parte", [])
                        if not isinstance(partes, list):
                            partes = [partes]
                        nomes = [
                            (p.get("pessoa", {}) if isinstance(p, dict) else {}).get("nome", "?")
                            for p in partes
                        ]
                        print(f"  Polo {tipo}: {', '.join(nomes)}")

        with open("trf1_consulta_resultado.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return sucesso

    except Exception as e:
        latencia = int((time.monotonic() - t0) * 1000)
        print(f"  ERRO: {e} ({latencia}ms)")
        return False


# ─── Step 2: Enviar manifestação (processo existente → só numeroProcesso) ────

def enviar_manifestacao(client: ZeepClient) -> dict:
    print(f"\n{'='*60}")
    print("STEP 2: entregarManifestacaoProcessual")
    print(f"  MODO: Processo EXISTENTE → <choice> = numeroProcesso (sem dadosBasicos)")
    print(f"{'='*60}")

    pdf_path = os.path.abspath(PDF_PATH)
    if not os.path.exists(pdf_path):
        print(f"  ERRO: PDF não encontrado: {pdf_path}")
        return {"sucesso": False, "mensagem": "PDF não encontrado"}

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_size_kb = len(pdf_bytes) / 1024
    print(f"  PDF: {os.path.basename(pdf_path)} ({pdf_size_kb:.1f} KB)")
    print(f"  SHA256: {hashlib.sha256(pdf_bytes).hexdigest()}")

    data_envio = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    print(f"  dataEnvio: {data_envio}")
    print(f"  Processo: {PROCESSO_20}")

    # tipoDocumento "60" = Petição (TNU/CNJ Resolução 46)
    documento = {
        "idDocumento": "1",
        "tipoDocumento": "60",
        "descricao": "Chamamento ao processo - Alan Cássio Jorge de Melo",
        "nivelSigilo": 0,
        "mimetype": "application/pdf",
        "dataHora": data_envio,
        "conteudo": pdf_bytes,
    }

    print(f"\n  Enviando SOAP (SÓ numeroProcesso, sem dadosBasicos)...")
    t0 = time.monotonic()

    try:
        # <choice> do XSD: para processo existente, APENAS numeroProcesso
        resp = client.service.entregarManifestacaoProcessual(
            idManifestante=AMANDA_CPF,
            senhaManifestante="",
            numeroProcesso=PROCESSO_20,
            documento=[documento],
            dataEnvio=data_envio,
        )
        latencia = int((time.monotonic() - t0) * 1000)
        data = serialize_object(resp, dict)

        sucesso = data.get("sucesso", False)
        mensagem = data.get("mensagem", "")
        protocolo = data.get("protocoloRecebimento", "")

        print(f"\n  ┌─────────────────────────────────────────────────┐")
        print(f"  │ RESULTADO DO ENVIO                              │")
        print(f"  ├─────────────────────────────────────────────────┤")
        print(f"  │ Sucesso:   {sucesso}")
        print(f"  │ Mensagem:  {mensagem}")
        print(f"  │ Protocolo: {protocolo}")
        print(f"  │ Latência:  {latencia}ms")
        print(f"  └─────────────────────────────────────────────────┘")

        recibo = data.get("recibo")
        if recibo:
            recibo_path = "trf1_recibo.pdf"
            with open(recibo_path, "wb") as f:
                f.write(recibo if isinstance(recibo, bytes) else base64.b64decode(recibo))
            print(f"  Recibo salvo: {recibo_path}")

        parametros = data.get("parametro", [])
        if parametros:
            if not isinstance(parametros, list):
                parametros = [parametros]
            print(f"\n  Parâmetros retornados:")
            for p in parametros:
                print(f"    - {p}")

        data_save = dict(data)
        if data_save.get("recibo") and isinstance(data_save["recibo"], bytes):
            data_save["recibo"] = f"<{len(data_save['recibo'])} bytes>"
        with open("trf1_envio_resultado.json", "w", encoding="utf-8") as f:
            json.dump(data_save, f, indent=2, ensure_ascii=False, default=str)

        return data

    except Exception as e:
        latencia = int((time.monotonic() - t0) * 1000)
        print(f"\n  ERRO SOAP: {type(e).__name__}: {e}")
        print(f"  Latência: {latencia}ms")
        if hasattr(e, "detail"):
            print(f"  Detail: {e.detail}")
        return {"sucesso": False, "mensagem": f"ERRO: {e}"}


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("TESTE ENVIO MNI - TRF1 (com WSDL local fallback)")
    print(f"Processo: {PROCESSO}")
    print("=" * 60)

    pfx_path = os.path.abspath(PFX_PATH)
    pdf_path = os.path.abspath(PDF_PATH) if PDF_PATH else ""

    print(f"\nVerificando arquivos:")
    print(f"  PFX: {'OK' if os.path.exists(pfx_path) else 'NAO ENCONTRADO'}")
    print(f"  PDF: {'OK' if pdf_path and os.path.exists(pdf_path) else 'NAO ENCONTRADO'}")
    print(f"  WSDL local: {'OK' if (LOCAL_WSDL_DIR / 'servico-intercomunicacao-2.2.2.wsdl').exists() else 'NAO ENCONTRADO'}")

    if not os.path.exists(pfx_path) or not pdf_path or not os.path.exists(pdf_path):
        print("ERRO: Arquivos necessários não encontrados!")
        sys.exit(1)

    print(f"\nExtraindo certificado...")
    cert_path, key_path, titular = extrair_pfx(pfx_path, PFX_SENHA)
    print(f"  Titular: {titular}")

    try:
        print(f"\nCriando client SOAP (WSDL local → {SERVICE_URL_TRF1_1G})...")
        client = criar_client_local_wsdl(SERVICE_URL_TRF1_1G, cert_path, key_path)

        consulta_ok = testar_consulta(client)

        if not consulta_ok:
            print("\n  Consulta falhou, tentando envio mesmo assim...")

        resultado = enviar_manifestacao(client)

        print(f"\n{'='*60}")
        print("RESUMO FINAL")
        print(f"{'='*60}")
        print(f"Processo: {PROCESSO}")
        print(f"Consulta: {'OK' if consulta_ok else 'FALHOU'}")
        print(f"Envio sucesso: {resultado.get('sucesso', False)}")
        print(f"Mensagem: {resultado.get('mensagem', '')}")
        if resultado.get("protocoloRecebimento"):
            print(f"PROTOCOLO: {resultado['protocoloRecebimento']}")
        print(f"{'='*60}")

    finally:
        limpar_tempfiles(cert_path, key_path)
        print("\nArquivos temporários removidos.")


if __name__ == "__main__":
    main()

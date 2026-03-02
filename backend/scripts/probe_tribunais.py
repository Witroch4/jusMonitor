"""
Probe script — verifica endpoints MNI 2.2.2 dos TRFs 1-6.

SEGURANÇA:
  - Fase 1: GET no WSDL (sem certificado, só teste de conectividade HTTP)
  - Fase 2: consultarProcesso (mTLS, operação de LEITURA — nunca protocola nada)
  - Nenhuma petição é criada. Nenhum dado é enviado a advogados/partes/processos reais.
  - O número de processo 00000000000000000000 é inválido e retornará "não encontrado".

Uso:
    poetry run python scripts/probe_tribunais.py --pfx /caminho/cert.pfx --senha "SENHA"

Interpretação dos resultados:
    WSDL OK + consultarProcesso OK (ou "não encontrado") → endpoint funcionando, mTLS aceito
    WSDL OK + SSL Error                                  → endpoint existe, mas cert não aceito
    WSDL timeout/connection refused                      → endpoint indisponível ou URL errada
"""

import argparse
import sys
import time
import tempfile
import os
import ssl
import traceback
from dataclasses import dataclass, field
from typing import Optional

import requests
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
from cryptography import x509

try:
    from zeep import Client as ZeepClient
    from zeep.transports import Transport
    from zeep.cache import SqliteCache
except ImportError:
    print("ERRO: zeep não instalado. Execute: poetry install")
    sys.exit(1)


# ─── Endpoints a testar ────────────────────────────────────────────────────────

ENDPOINTS = [
    # TRF1 — 1ª Região (DF, MG, GO, BA, MA, PI, TO, PA, AM, AC, RO, RR, AP)
    {"id": "TRF1-1G",   "nome": "TRF1 1º Grau (Brasília)",  "wsdl": "https://pje1g.trf1.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF1-2G",   "nome": "TRF1 2º Grau (Brasília)",  "wsdl": "https://pje2g.trf1.jus.br/pje/intercomunicacao?wsdl"},

    # TRF2 — 2ª Região (RJ, ES)
    {"id": "TRF2-1G",   "nome": "TRF2 1º Grau (RJ)",        "wsdl": "https://pje1g.trf2.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF2-2G",   "nome": "TRF2 2º Grau (RJ)",        "wsdl": "https://pje2g.trf2.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF2-ALT",  "nome": "TRF2 alternativo",          "wsdl": "https://pje.trf2.jus.br/pje/intercomunicacao?wsdl"},

    # TRF3 — 3ª Região (SP, MS)
    {"id": "TRF3-1G",   "nome": "TRF3 1º Grau (SP)",        "wsdl": "https://pje1g.trf3.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF3-2G",   "nome": "TRF3 2º Grau (SP)",        "wsdl": "https://pje2g.trf3.jus.br/pje/intercomunicacao?wsdl"},

    # TRF4 — 4ª Região (RS, SC, PR) — EPROC
    {"id": "TRF4-EPROC","nome": "TRF4 EPROC (Sul)",         "wsdl": "https://eproc.trf4.jus.br/eproc2trf4/intercomunicacao?wsdl"},
    {"id": "TRF4-1G",   "nome": "TRF4 1º Grau PJe",         "wsdl": "https://pje1g.trf4.jus.br/pje/intercomunicacao?wsdl"},

    # TRF5 — 5ª Região (CE, AL, SE, PB, PE, RN)
    {"id": "TRF5-REG",  "nome": "TRF5 Regional",             "wsdl": "https://pje.trf5.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF5-JFCE", "nome": "TRF5 JFCE (Ceará)",        "wsdl": "https://pje.jfce.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF5-JFAL", "nome": "TRF5 JFAL (Alagoas)",      "wsdl": "https://pje.jfal.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF5-JFSE", "nome": "TRF5 JFSE (Sergipe)",      "wsdl": "https://pje.jfse.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF5-JFPE", "nome": "TRF5 JFPE (Pernambuco)",   "wsdl": "https://pje.jfpe.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF5-JFPB", "nome": "TRF5 JFPB (Paraíba)",      "wsdl": "https://pje.jfpb.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF5-JFRN", "nome": "TRF5 JFRN (R. G. Norte)",  "wsdl": "https://pje.jfrn.jus.br/pje/intercomunicacao?wsdl"},

    # TRF6 — 6ª Região (MG — criado em 2021, desmembrado do TRF1)
    {"id": "TRF6",      "nome": "TRF6 (Minas Gerais)",       "wsdl": "https://pje.trf6.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF6-1G",   "nome": "TRF6 1º Grau (MG)",        "wsdl": "https://pje1g.trf6.jus.br/pje/intercomunicacao?wsdl"},
    {"id": "TRF6-JFMG", "nome": "TRF6 JFMG (Minas)",        "wsdl": "https://pje.jfmg.jus.br/pje/intercomunicacao?wsdl"},
]


# ─── Helpers de certificado ────────────────────────────────────────────────────

def extrair_pfx(pfx_path: str, senha: str) -> tuple[str, str, str]:
    """
    Extrai cert PEM e key PEM do PFX.
    Retorna (cert_pem_path, key_pem_path, titular_nome).
    Os arquivos temporários são de responsabilidade do chamador (apagar após uso).
    """
    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()

    senha_bytes = senha.encode() if senha else b""
    pkcs = load_pkcs12(pfx_bytes, senha_bytes)

    cert_pem = pkcs.cert.certificate.public_bytes(Encoding.PEM)
    key_pem = pkcs.key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

    # Extrai nome do titular
    try:
        cn = pkcs.cert.certificate.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        titular = cn[0].value if cn else "Desconhecido"
    except Exception:
        titular = "Desconhecido"

    # Escreve em tempfiles seguros
    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")

    os.write(cert_fd, cert_pem)
    os.write(key_fd, key_pem)
    os.close(cert_fd)
    os.close(key_fd)
    os.chmod(key_path, 0o600)

    return cert_path, key_path, titular


def limpar_tempfiles(*paths: str) -> None:
    """Sobrescreve e remove arquivos temporários de chave privada."""
    for p in paths:
        try:
            if os.path.exists(p):
                size = os.path.getsize(p)
                with open(p, "wb") as f:
                    f.write(b"\x00" * size)
                os.unlink(p)
        except Exception:
            pass


# ─── Fases do probe ───────────────────────────────────────────────────────────

@dataclass
class ProbeResult:
    id: str
    nome: str
    wsdl: str
    fase1_status: str = "—"        # código HTTP ou erro
    fase1_ok: bool = False
    fase2_status: str = "—"        # resultado SOAP ou erro
    fase2_ok: bool = False
    fase2_detalhe: str = ""        # mensagem do tribunal ou traceback resumido
    latencia_ms: Optional[int] = None


def fase1_wsdl_probe(endpoint: dict, timeout: int = 10) -> ProbeResult:
    """GET no WSDL sem certificado — verifica existência do endpoint."""
    result = ProbeResult(
        id=endpoint["id"],
        nome=endpoint["nome"],
        wsdl=endpoint["wsdl"],
    )

    t0 = time.monotonic()
    try:
        r = requests.get(endpoint["wsdl"], timeout=timeout, verify=True)
        result.latencia_ms = int((time.monotonic() - t0) * 1000)
        result.fase1_status = str(r.status_code)
        # 200 = WSDL ok; 401/403 = existe mas requer auth; 302 = redirect login
        result.fase1_ok = r.status_code in (200, 401, 403, 302)
        if not result.fase1_ok:
            result.fase1_status = f"HTTP {r.status_code}"
    except requests.exceptions.SSLError as e:
        result.fase1_status = f"SSL: {str(e)[:60]}"
    except requests.exceptions.ConnectionError:
        result.fase1_status = "CONNECTION_ERROR"
    except requests.exceptions.Timeout:
        result.fase1_status = "TIMEOUT"
    except Exception as e:
        result.fase1_status = f"ERR: {type(e).__name__}"

    return result


def fase2_soap_probe(result: ProbeResult, cert_path: str, key_path: str, cpf: str, timeout: int = 20) -> None:
    """
    consultarProcesso com número inválido (00000000000000000000).
    Operação de LEITURA — nunca protocola, nunca cria processo.
    Sucesso = tribunal respondeu (qualquer resposta SOAP, incluindo "não encontrado").
    """
    if not result.fase1_ok:
        result.fase2_status = "PULADO (fase1 falhou)"
        return

    t0 = time.monotonic()
    try:
        session = requests.Session()
        session.cert = (cert_path, key_path)
        session.verify = True
        session.timeout = timeout

        transport = Transport(
            session=session,
            timeout=timeout,
            cache=SqliteCache(path="/tmp/probe_wsdl_cache.db", timeout=3600),
        )
        client = ZeepClient(result.wsdl, transport=transport)

        # Número de processo inválido — o tribunal vai retornar "não encontrado"
        # Isso é SEGURO: consultarProcesso é leitura, sem efeitos colaterais.
        resposta = client.service.consultarProcesso(
            idConsultante=cpf,
            senhaConsultante="",
            numeroProcesso="00000000000000000000",
            movimentos=False,
            incluirCabecalho=False,
            incluirDocumentos=False,
        )

        result.latencia_ms = int((time.monotonic() - t0) * 1000)
        sucesso = getattr(resposta, "sucesso", False)
        mensagem = str(getattr(resposta, "mensagem", ""))

        result.fase2_ok = True  # chegou ao tribunal e recebeu resposta SOAP
        result.fase2_status = "SOAP OK"
        result.fase2_detalhe = f"sucesso={sucesso} | msg={mensagem[:100]}"

    except Exception as e:
        result.latencia_ms = int((time.monotonic() - t0) * 1000)
        msg = str(e)

        # Classifica o tipo de falha
        if "SSL" in msg or "certificate" in msg.lower() or "handshake" in msg.lower():
            result.fase2_status = "SSL_ERROR"
            result.fase2_detalhe = msg[:120]
        elif "Timeout" in msg or "timed out" in msg.lower():
            result.fase2_status = "TIMEOUT"
            result.fase2_detalhe = msg[:80]
        elif "Connection" in msg or "refused" in msg.lower():
            result.fase2_status = "CONNECTION_ERROR"
            result.fase2_detalhe = msg[:80]
        elif "Fault" in msg or "SOAP" in msg or "ValidationError" in msg:
            # Tribunal respondeu com SOAP Fault — pipeline funciona!
            result.fase2_ok = True
            result.fase2_status = "SOAP_FAULT (tribunal OK)"
            result.fase2_detalhe = msg[:150]
        else:
            result.fase2_status = f"ERR: {type(e).__name__}"
            result.fase2_detalhe = msg[:120]


# ─── Relatório ────────────────────────────────────────────────────────────────

def imprimir_relatorio(resultados: list[ProbeResult], cpf: str, titular: str) -> None:
    print("\n" + "=" * 90)
    print(f"  PROBE ENDPOINTS MNI 2.2.2 — TRF 1-6")
    print(f"  Certificado: {titular} | CPF usado: {cpf}")
    print(f"  Fase 1: GET WSDL (sem cert)  |  Fase 2: consultarProcesso com mTLS (leitura)")
    print("=" * 90)

    header = f"{'ID':<14} {'WSDL (Fase1)':<10} {'SOAP (Fase2)':<26} {'ms':>6}  {'Endpoint'}"
    print(header)
    print("-" * 90)

    for r in resultados:
        f1 = ("✓ " + r.fase1_status) if r.fase1_ok else ("✗ " + r.fase1_status)
        f2 = ("✓ " + r.fase2_status) if r.fase2_ok else ("✗ " + r.fase2_status)
        lat = str(r.latencia_ms) if r.latencia_ms is not None else "—"
        print(f"{r.id:<14} {f1:<18} {f2:<32} {lat:>6}ms  {r.wsdl}")
        if r.fase2_detalhe:
            print(f"{'':14}   └── {r.fase2_detalhe}")

    print("=" * 90)

    ok = [r for r in resultados if r.fase2_ok]
    wsdl_ok = [r for r in resultados if r.fase1_ok]
    print(f"\nRESUMO: {len(wsdl_ok)}/{len(resultados)} endpoints WSDL acessíveis | "
          f"{len(ok)}/{len(resultados)} com SOAP respondendo (mTLS aceito)\n")

    print("LEGENDA:")
    print("  ✓ SOAP OK / SOAP_FAULT     → Tribunal respondeu. Pipeline funcionando. Cert aceito.")
    print("  ✗ SSL_ERROR                → Endpoint existe mas rejeitou o certificado.")
    print("  ✗ TIMEOUT                  → Endpoint lento ou firewall bloqueando.")
    print("  ✗ CONNECTION_ERROR         → URL errada ou servidor fora do ar.")
    print("  ✗ PULADO                   → WSDL inacessível, fase 2 não executada.\n")

    print("ENDPOINTS FUNCIONANDO (adicionar ao registry):")
    for r in ok:
        print(f'  {{"id": "{r.id}", "wsdl": "{r.wsdl}"}},')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe de endpoints MNI 2.2.2 — TRF 1-6. Operação de leitura apenas, sem protocolação."
    )
    parser.add_argument("--pfx", required=True, help="Caminho para o arquivo .pfx / .p12 do certificado A1")
    parser.add_argument("--senha", required=True, help="Senha do arquivo PFX")
    parser.add_argument("--cpf", default="", help="CPF do certificado (digits apenas). Se vazio, extrai do cert.")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout por requisição em segundos (default: 15)")
    parser.add_argument(
        "--ids", nargs="*",
        help="IDs dos endpoints a testar (ex: TRF1-1G TRF5-JFCE). Padrão: todos."
    )
    args = parser.parse_args()

    # Extrai cert
    print(f"\nCarregando certificado: {args.pfx}")
    try:
        cert_path, key_path, titular = extrair_pfx(args.pfx, args.senha)
    except Exception as e:
        print(f"ERRO ao carregar PFX: {e}")
        sys.exit(1)

    print(f"Titular: {titular}")

    # CPF: usa o passado ou extrai do CN
    cpf = args.cpf.replace(".", "").replace("-", "") if args.cpf else ""
    if not cpf:
        # Tenta extrair CPF do CN (formato padrão ICP-Brasil: "Nome:CPF")
        if ":" in titular:
            cpf_candidate = titular.split(":")[-1].strip()
            if cpf_candidate.isdigit() and len(cpf_candidate) == 11:
                cpf = cpf_candidate
    if not cpf:
        print("AVISO: CPF não encontrado no cert e não passado via --cpf. Usando '00000000000' (pode falhar no SOAP).")
        cpf = "00000000000"

    # Filtra endpoints se --ids passado
    endpoints = ENDPOINTS
    if args.ids:
        endpoints = [e for e in ENDPOINTS if e["id"] in args.ids]
        if not endpoints:
            print(f"Nenhum endpoint encontrado para IDs: {args.ids}")
            sys.exit(1)

    print(f"\nTestando {len(endpoints)} endpoint(s)...\n")

    resultados: list[ProbeResult] = []
    try:
        for ep in endpoints:
            print(f"  [{ep['id']}] {ep['nome']}")
            print(f"    Fase 1: GET {ep['wsdl'][:60]}...")
            r = fase1_wsdl_probe(ep, timeout=args.timeout)
            print(f"    → {r.fase1_status}")

            if r.fase1_ok:
                print(f"    Fase 2: consultarProcesso (mTLS, leitura)...")
                fase2_soap_probe(r, cert_path, key_path, cpf, timeout=args.timeout)
                print(f"    → {r.fase2_status} | {r.fase2_detalhe[:80]}")
            else:
                r.fase2_status = "PULADO"

            resultados.append(r)
            print()

    finally:
        limpar_tempfiles(cert_path, key_path)
        print("Arquivos temporários de chave removidos com segurança.\n")

    imprimir_relatorio(resultados, cpf, titular)


if __name__ == "__main__":
    main()

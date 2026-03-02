"""
Consulta processos reais via MNI 2.2.2 — operação de LEITURA pura.

SEGURANÇA:
  - consultarProcesso é read-only — não cria, não modifica, não protocola nada
  - Usa mTLS com certificado A1 da Amanda
  - Resultados salvos em JSON local para análise

Uso:
    poetry run python scripts/consultar_processos_reais.py \
        --pfx /caminho/cert.pfx --senha "SENHA" \
        [--output resultados.json]

Dados extraídos: cabeçalho, polos (partes), órgão julgador, assuntos, movimentos.
"""

import argparse
import json
import sys
import time
import tempfile
import os
from datetime import datetime

import requests
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
from cryptography import x509

try:
    from zeep import Client as ZeepClient
    from zeep.transports import Transport
    from zeep.cache import SqliteCache
    from zeep.helpers import serialize_object
except ImportError:
    print("ERRO: zeep não instalado. Execute: poetry install")
    sys.exit(1)


# ─── Processos reais do CSV (mapeados para endpoints confirmados) ──────────────

PROCESSOS = [
    # TRF5-JFCE (confirmado: SOAP OK)
    {"numero": "0004233-37.2025.4.05.8100", "nome": "ENZO MAXUEL DUARTE", "wsdl": "https://pje.jfce.jus.br/pje/intercomunicacao?wsdl", "tribunal": "TRF5-JFCE"},
    {"numero": "0013862-35.2025.4.05.8100", "nome": "JENNIFFER ALVES MACHADO", "wsdl": "https://pje.jfce.jus.br/pje/intercomunicacao?wsdl", "tribunal": "TRF5-JFCE"},
    {"numero": "0017908-67.2025.4.05.8100", "nome": "ANTONIO CARLOS DE SOUSA HOLANDA", "wsdl": "https://pje.jfce.jus.br/pje/intercomunicacao?wsdl", "tribunal": "TRF5-JFCE"},

    # TRF5-JFPB (confirmado: SOAP OK)
    {"numero": "0001440-85.2026.4.05.8102", "nome": "JOSE JOAQUIM DOS SANTOS", "wsdl": "https://pje.jfpb.jus.br/pje/intercomunicacao?wsdl", "tribunal": "TRF5-JFPB"},

    # TRF5-JFAL (confirmado: SOAP OK)
    {"numero": "0016468-42.2025.4.05.8001", "nome": "ALADSON SILVA DOS SANTOS", "wsdl": "https://pje.jfal.jus.br/pje/intercomunicacao?wsdl", "tribunal": "TRF5-JFAL"},

    # TRF6-1G (confirmado: SOAP OK)
    {"numero": "6000791-84.2026.4.06.3803", "nome": "STELLA CARVALHO FERNANDES", "wsdl": "https://pje1g.trf6.jus.br/pje/intercomunicacao?wsdl", "tribunal": "TRF6-1G"},
    {"numero": "6008485-08.2025.4.06.3814", "nome": "RENATA CANDIDA MENDONCA RAMOS SILVEIRA", "wsdl": "https://pje1g.trf6.jus.br/pje/intercomunicacao?wsdl", "tribunal": "TRF6-1G"},
]


# ─── Helpers ───────────────────────────────────────────────────────────────────

def normalize_processo(numero: str) -> str:
    """Remove pontos, traços → 20 dígitos."""
    clean = numero.replace(".", "").replace("-", "").replace(" ", "")
    if len(clean) != 20 or not clean.isdigit():
        raise ValueError(f"Número inválido: '{numero}' → '{clean}' ({len(clean)} dígitos)")
    return clean


def extrair_pfx(pfx_path: str, senha: str) -> tuple[str, str, str]:
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
    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem)
    os.write(key_fd, key_pem)
    os.close(cert_fd)
    os.close(key_fd)
    os.chmod(key_path, 0o600)
    return cert_path, key_path, titular


def limpar_tempfiles(*paths: str):
    for p in paths:
        try:
            if os.path.exists(p):
                size = os.path.getsize(p)
                with open(p, "wb") as f:
                    f.write(b"\x00" * size)
                os.unlink(p)
        except Exception:
            pass


def consultar_processo(wsdl_url: str, cert_path: str, key_path: str, cpf: str, numero: str, timeout: int = 30) -> dict:
    """Chama consultarProcesso SOAP (LEITURA PURA)."""
    session = requests.Session()
    session.cert = (cert_path, key_path)
    session.verify = True
    session.timeout = timeout

    transport = Transport(
        session=session,
        timeout=timeout,
        cache=SqliteCache(path="/tmp/consulta_wsdl_cache.db", timeout=3600),
    )
    client = ZeepClient(wsdl_url, transport=transport)

    numero_normalizado = normalize_processo(numero)

    resposta = client.service.consultarProcesso(
        idConsultante=cpf,
        senhaConsultante="",
        numeroProcesso=numero_normalizado,
        movimentos=True,
        incluirCabecalho=True,
        incluirDocumentos=False,
    )

    return serialize_object(resposta, dict)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Consulta processos reais via MNI 2.2.2 (leitura pura)")
    parser.add_argument("--pfx", required=True, help="Caminho para .pfx")
    parser.add_argument("--senha", required=True, help="Senha do PFX")
    parser.add_argument("--cpf", default="", help="CPF (digits). Se vazio, extrai do cert.")
    parser.add_argument("--output", default="consulta_resultados.json", help="Arquivo JSON de saída")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout por consulta (s)")
    parser.add_argument("--indices", nargs="*", type=int, help="Índices dos processos a testar (0-based). Padrão: todos.")
    args = parser.parse_args()

    print(f"\nCarregando certificado: {args.pfx}")
    cert_path, key_path, titular = extrair_pfx(args.pfx, args.senha)
    print(f"Titular: {titular}")

    cpf = args.cpf.replace(".", "").replace("-", "") if args.cpf else ""
    if not cpf and ":" in titular:
        cpf_candidate = titular.split(":")[-1].strip()
        if cpf_candidate.isdigit() and len(cpf_candidate) == 11:
            cpf = cpf_candidate
    if not cpf:
        cpf = "00000000000"
    print(f"CPF: {cpf}\n")

    processos = PROCESSOS
    if args.indices:
        processos = [PROCESSOS[i] for i in args.indices if 0 <= i < len(PROCESSOS)]

    resultados = []
    try:
        for i, proc in enumerate(processos):
            print(f"[{i+1}/{len(processos)}] {proc['nome']}")
            print(f"  Processo: {proc['numero']}")
            print(f"  Tribunal: {proc['tribunal']} ({proc['wsdl'][:50]}...)")

            t0 = time.monotonic()
            try:
                data = consultar_processo(
                    proc["wsdl"], cert_path, key_path, cpf,
                    proc["numero"], timeout=args.timeout,
                )
                latencia = int((time.monotonic() - t0) * 1000)

                sucesso = data.get("sucesso", False)
                mensagem = data.get("mensagem", "")
                processo = data.get("processo")

                resultado = {
                    "numero": proc["numero"],
                    "nome_cliente": proc["nome"],
                    "tribunal": proc["tribunal"],
                    "sucesso": sucesso,
                    "mensagem": mensagem,
                    "latencia_ms": latencia,
                    "dados_processo": processo,
                }

                if sucesso and processo:
                    print(f"  ✓ SUCESSO ({latencia}ms)")
                    # Extrair info útil
                    if isinstance(processo, dict):
                        cab = processo.get("processo") or processo
                        print(f"    Classe: {cab.get('classeProcessual', '?')}")
                        polos = cab.get("polo", [])
                        if polos:
                            for polo in polos:
                                tipo = polo.get("polo", "?")
                                partes = polo.get("parte", [])
                                nomes = [p.get("pessoa", {}).get("nome", "?") for p in partes if isinstance(p, dict)]
                                print(f"    Polo {tipo}: {', '.join(nomes)}")
                        oj = cab.get("orgaoJulgador")
                        if oj:
                            print(f"    Órgão: {oj.get('nomeOrgao', '?')} (IBGE: {oj.get('codigoMunicipioIBGE', '?')})")
                else:
                    print(f"  ✗ {mensagem[:100]} ({latencia}ms)")

                resultados.append(resultado)

            except Exception as e:
                latencia = int((time.monotonic() - t0) * 1000)
                msg = str(e)
                print(f"  ✗ ERRO: {msg[:100]} ({latencia}ms)")
                resultados.append({
                    "numero": proc["numero"],
                    "nome_cliente": proc["nome"],
                    "tribunal": proc["tribunal"],
                    "sucesso": False,
                    "mensagem": f"ERRO: {msg}",
                    "latencia_ms": latencia,
                })

            print()

    finally:
        limpar_tempfiles(cert_path, key_path)
        print("Arquivos temporários removidos.\n")

    # Salvar resultados
    # Converter datetime e bytes para string no JSON
    def json_serializer(obj):
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return f"<bytes {len(obj)}>"
        return str(obj)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False, default=json_serializer)
    print(f"Resultados salvos em: {args.output}")

    # Resumo
    ok = [r for r in resultados if r["sucesso"]]
    print(f"\nRESUMO: {len(ok)}/{len(resultados)} processos consultados com sucesso")
    for r in ok:
        print(f"  ✓ {r['numero']} ({r['nome_cliente']}) — {r['tribunal']}")
    for r in resultados:
        if not r["sucesso"]:
            print(f"  ✗ {r['numero']} ({r['nome_cliente']}) — {r['mensagem'][:80]}")


if __name__ == "__main__":
    main()

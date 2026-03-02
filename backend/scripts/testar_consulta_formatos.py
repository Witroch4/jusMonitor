"""
Testa consultarProcesso com diferentes formatos de idConsultante.

O MNI diz que mTLS substitui id/senha, mas na prática cada tribunal
implementa diferente. Este script testa todos os formatos possíveis
para descobrir qual funciona.

SEGURANÇA: consultarProcesso é LEITURA PURA — não modifica nada.

Uso:
    poetry run python scripts/testar_consulta_formatos.py \
        --pfx /caminho/cert.pfx --senha "SENHA"
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


# Processo real confirmado no TRF5-JFCE (Amanda é advogada neste processo)
PROCESSO_TESTE = {
    "numero": "0004233-37.2025.4.05.8100",
    "nome": "ENZO MAXUEL DUARTE",
    "wsdl": "https://pje.jfce.jus.br/pje/intercomunicacao?wsdl",
    "tribunal": "TRF5-JFCE",
}

# Amanda - dados do certificado
AMANDA_CPF = "07071649316"
AMANDA_OAB = "50784"
AMANDA_OAB_UF = "CE"


def normalize_processo(numero: str) -> str:
    clean = numero.replace(".", "").replace("-", "").replace(" ", "")
    if len(clean) != 20 or not clean.isdigit():
        raise ValueError(f"Número inválido: '{numero}' → '{clean}'")
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


def consultar(wsdl_url: str, cert_path: str, key_path: str,
              id_consultante: str, senha: str, numero: str,
              movimentos: bool = True, incluir_cabecalho: bool = True,
              timeout: int = 30) -> dict:
    """Chama consultarProcesso com parâmetros específicos."""
    session = requests.Session()
    session.cert = (cert_path, key_path)
    session.verify = True
    session.timeout = timeout

    transport = Transport(
        session=session,
        timeout=timeout,
        cache=SqliteCache(path="/tmp/consulta_fmt_cache.db", timeout=3600),
    )
    client = ZeepClient(wsdl_url, transport=transport)

    numero_norm = normalize_processo(numero)

    resposta = client.service.consultarProcesso(
        idConsultante=id_consultante,
        senhaConsultante=senha,
        numeroProcesso=numero_norm,
        movimentos=movimentos,
        incluirCabecalho=incluir_cabecalho,
        incluirDocumentos=False,
    )

    return serialize_object(resposta, dict)


def main():
    parser = argparse.ArgumentParser(description="Testa consultarProcesso com múltiplos formatos de ID")
    parser.add_argument("--pfx", required=True, help="Caminho para .pfx")
    parser.add_argument("--senha", required=True, help="Senha do PFX")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout (s)")
    args = parser.parse_args()

    print(f"\nCarregando certificado: {args.pfx}")
    cert_path, key_path, titular = extrair_pfx(args.pfx, args.senha)
    print(f"Titular: {titular}")
    print(f"Processo: {PROCESSO_TESTE['numero']} ({PROCESSO_TESTE['nome']})")
    print(f"Tribunal: {PROCESSO_TESTE['tribunal']}")
    print()

    # Formatos de idConsultante para testar
    formatos = [
        ("CPF puro", AMANDA_CPF, ""),
        ("CPF com senha vazia", AMANDA_CPF, ""),
        ("CPF com senha=cpf", AMANDA_CPF, AMANDA_CPF),
        ("OAB UF+numero", f"{AMANDA_OAB_UF}{AMANDA_OAB}", ""),
        ("OAB formato CE50784", f"CE{AMANDA_OAB}", ""),
        ("OAB numero puro", AMANDA_OAB, ""),
        ("String vazia", "", ""),
        ("Zeros 11 digitos", "00000000000", ""),
        ("CPF formatado", "070.716.493-16", ""),
    ]

    resultados = []

    try:
        for i, (desc, id_val, senha_val) in enumerate(formatos):
            print(f"[{i+1}/{len(formatos)}] Testando: {desc}")
            print(f"  idConsultante = '{id_val}'")
            print(f"  senhaConsultante = '{senha_val}'")

            t0 = time.monotonic()
            try:
                data = consultar(
                    PROCESSO_TESTE["wsdl"], cert_path, key_path,
                    id_val, senha_val, PROCESSO_TESTE["numero"],
                    timeout=args.timeout,
                )
                latencia = int((time.monotonic() - t0) * 1000)

                sucesso = data.get("sucesso", False)
                mensagem = data.get("mensagem", "")
                processo = data.get("processo")

                resultado = {
                    "formato": desc,
                    "idConsultante": id_val,
                    "sucesso": sucesso,
                    "mensagem": mensagem,
                    "latencia_ms": latencia,
                    "tem_processo": processo is not None,
                }

                if sucesso and processo:
                    print(f"  ✓ SUCESSO! ({latencia}ms)")
                    if isinstance(processo, dict):
                        cab = processo.get("dadosBasicos") or processo.get("processo") or processo
                        if isinstance(cab, dict):
                            print(f"    Classe: {cab.get('classeProcessual', '?')}")
                            polos = cab.get("polo", [])
                            if polos:
                                for polo in (polos if isinstance(polos, list) else [polos]):
                                    tipo = polo.get("polo", "?")
                                    partes = polo.get("parte", [])
                                    if not isinstance(partes, list):
                                        partes = [partes]
                                    nomes = []
                                    for p in partes:
                                        if isinstance(p, dict):
                                            pessoa = p.get("pessoa", {})
                                            if isinstance(pessoa, dict):
                                                nomes.append(pessoa.get("nome", "?"))
                                    print(f"    Polo {tipo}: {', '.join(nomes)}")
                            oj = cab.get("orgaoJulgador")
                            if oj and isinstance(oj, dict):
                                print(f"    Órgão: {oj.get('nomeOrgao', '?')}")
                    resultado["dados_resumo"] = str(processo)[:200]
                else:
                    print(f"  ✗ {mensagem[:100]} ({latencia}ms)")

                resultados.append(resultado)

            except Exception as e:
                latencia = int((time.monotonic() - t0) * 1000)
                msg = str(e)
                print(f"  ✗ ERRO: {msg[:120]} ({latencia}ms)")
                resultados.append({
                    "formato": desc,
                    "idConsultante": id_val,
                    "sucesso": False,
                    "mensagem": f"ERRO: {msg[:200]}",
                    "latencia_ms": latencia,
                })

            print()
            # Pausa entre chamadas para não sobrecarregar
            time.sleep(1)

    finally:
        limpar_tempfiles(cert_path, key_path)
        print("Arquivos temporários removidos.\n")

    # Salvar resultados
    output = "consulta_formatos_resultado.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
    print(f"Resultados salvos em: {output}")

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    ok = [r for r in resultados if r["sucesso"]]
    fail = [r for r in resultados if not r["sucesso"]]

    if ok:
        print(f"\n✓ {len(ok)} formato(s) FUNCIONOU:")
        for r in ok:
            print(f"  → {r['formato']} (idConsultante='{r['idConsultante']}') — {r['latencia_ms']}ms")
    else:
        print("\n✗ Nenhum formato funcionou")

    print(f"\n✗ {len(fail)} formato(s) FALHOU:")
    for r in fail:
        print(f"  → {r['formato']}: {r['mensagem'][:80]}")

    print()


if __name__ == "__main__":
    main()

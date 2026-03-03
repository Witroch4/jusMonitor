"""Login completo no PJe TRF1 via simulacao PJeOffice.

Descobertas:
- certChain = ASN.1 PKIPath DER (SEQUENCE OF Certificate, end-entity first) → base64
- assinatura = MD5withRSA raw signature de mensagem.encode('utf-8') → base64
- uuid = UUIDv4 novo a cada chamada
- HTTP 204 = sucesso no pjeoffice-rest
- Submeter form com pjeoffice-code = uuid
"""

import asyncio
import base64
import json
import os
import re
import sys
import tempfile
import time
import uuid as uuid_mod

import requests
import urllib3

urllib3.disable_warnings()

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12


# ─── Helpers ─────────────────────────────────────────────────────────────────

def build_pkipath_der(cert_ders: list) -> bytes:
    """ASN.1 SEQUENCE OF Certificate (PKIPath)."""
    content = b"".join(cert_ders)
    n = len(content)
    if n < 0x80:
        lb = bytes([n])
    elif n < 0x100:
        lb = bytes([0x81, n])
    elif n < 0x10000:
        lb = bytes([0x82, n >> 8, n & 0xff])
    else:
        lb = bytes([0x83, (n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff])
    return bytes([0x30]) + lb + content


def load_pfx(pfx_path: str, password: str):
    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, password.encode())
    return pkcs.key, pkcs.cert.certificate, [c.certificate for c in (pkcs.additional_certs or [])]


def get_certchain_b64(cert_obj, additional_certs) -> str:
    """PKIPath base64 (end-entity first)."""
    cert_ders = [cert_obj.public_bytes(Encoding.DER)]
    for c in additional_certs:
        cert_ders.append(c.public_bytes(Encoding.DER))
    return base64.b64encode(build_pkipath_der(cert_ders)).decode("ascii")


def sign_md5_rsa(private_key, mensagem: str) -> str:
    """MD5withRSA PKCS1v15 de mensagem.encode('utf-8') → base64."""
    sig = private_key.sign(mensagem.encode("utf-8"), padding.PKCS1v15(), hashes.MD5())
    return base64.b64encode(sig).decode("ascii")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    PFX_PATH = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    PFX_PASSWORD = "22051998"
    LOGIN_URL = "https://pje1g.trf1.jus.br/pje/login.seam"
    PROCESSO = "1000654-37.2026.4.01.3704"
    BASE_URL = "https://pje1g.trf1.jus.br/pje"
    SSO_ENDPOINT = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"

    print("=" * 60)
    print("  PJe TRF1 Login via PJeOffice Simulation")
    print("=" * 60)

    # Load PFX
    print("\n[1] Carregando certificado...")
    private_key, cert_obj, additional_certs = load_pfx(PFX_PATH, PFX_PASSWORD)
    subject = cert_obj.subject.rfc4514_string()
    print(f"  Subject: {subject}")
    print(f"  Validade: {cert_obj.not_valid_after_utc}")

    certchain_b64 = get_certchain_b64(cert_obj, additional_certs)
    print(f"  certChain PKIPath: {len(certchain_b64)} chars b64")

    # Prepare PEM for mTLS
    cert_pem = cert_obj.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain_pem = b"".join(c.public_bytes(Encoding.PEM) for c in additional_certs)

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem + chain_pem); os.close(cert_fd)
    os.write(key_fd, key_pem); os.close(key_fd)

    session = requests.Session()
    session.cert = (cert_path, key_path)

    try:
        # Step 1: GET login page
        print("\n[2] Obtendo página de login...")
        resp = session.get(LOGIN_URL, allow_redirects=True, timeout=30)
        print(f"  Status: {resp.status_code}, URL: {resp.url}")

        if resp.status_code != 200:
            print(f"  ERRO ao obter login page!")
            return False

        html = resp.text
        match = re.search(r"autenticar\('([^']+)',\s*'([^']+)'\)", html)
        if not match:
            print("  ERRO: challenge não encontrado na página!")
            return False

        codigo_seguranca = match.group(1)
        mensagem = match.group(2)
        print(f"  mensagem (nonce): {mensagem}")
        print(f"  codigoSeguranca: {codigo_seguranca[:50]}...")
        print(f"  Cookies SSO: {list(session.cookies.keys())}")

        # Extract form action
        form_match = re.search(r'id="loginForm"[^>]*action="([^"]+)"', html)
        form_action = form_match.group(1).replace("&amp;", "&") if form_match else ""
        print(f"  Form action: {form_action[:120]}...")

        # Step 2: Sign
        print("\n[3] Assinando mensagem com MD5withRSA...")
        token_uuid = str(uuid_mod.uuid4())
        assinatura_b64 = sign_md5_rsa(private_key, mensagem)
        print(f"  UUID: {token_uuid}")
        print(f"  Assinatura: {assinatura_b64[:60]}...")

        # Step 3: POST to pjeoffice-rest
        print("\n[4] Enviando para /pjeoffice-rest...")
        payload = {
            "certChain": certchain_b64,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": assinatura_b64,
        }

        t0 = time.monotonic()
        rest_resp = session.post(
            SSO_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Origin": "https://sso.cloud.pje.jus.br",
                "Referer": resp.url,
            },
            timeout=30,
        )
        t1 = time.monotonic()
        print(f"  Status: {rest_resp.status_code} ({t1-t0:.2f}s)")
        print(f"  Body: '{rest_resp.text[:200]}'")

        if rest_resp.status_code != 204:
            print(f"  FALHA no pjeoffice-rest! Esperado 204, got {rest_resp.status_code}")
            if rest_resp.status_code == 500 and "ConstraintViolation" in rest_resp.text:
                print("  ⚠️  UUID duplicado - tente novamente (gerando novo UUID já seria suficiente)")
            return False

        print("  ✅ pjeoffice-rest: OK (204)")

        # Step 4: Submit form
        print("\n[5] Submetendo formulário de login...")
        login_url = form_action if form_action.startswith("http") else f"https://sso.cloud.pje.jus.br{form_action}"
        print(f"  POST → {login_url[:120]}")

        t0 = time.monotonic()
        login_resp = session.post(
            login_url,
            data={
                "username": "",
                "password": "",
                "pjeoffice-code": token_uuid,
                "phrase": "",
                "login-pje-office": "CERTIFICADO DIGITAL",
            },
            allow_redirects=True,
            timeout=30,
        )
        t1 = time.monotonic()
        print(f"  Status: {login_resp.status_code} ({t1-t0:.2f}s)")
        print(f"  URL final: {login_resp.url}")
        print(f"  Cookies: {list(session.cookies.keys())}")

        body = login_resp.text
        # Keywords específicas do painel (NÃO da página de login)
        painel_keywords = ["localizar processo", "meu painel", "avisos do sistema",
                           "menu principal", "expedientes", "nova tarefa", "fila de tarefas",
                           "amanda alves", "07071649316"]
        found = [kw for kw in painel_keywords if kw in body.lower()]
        print(f"  Keywords do painel: {found}")

        if found:
            print("\n  ✅ ✅ ✅ LOGIN COM SUCESSO! ✅ ✅ ✅")
            logged_in = True
        else:
            print("  ❌ Login não confirmado no painel")
            print(f"  Body (2000): {body[:2000]}")
            logged_in = False

        if not logged_in:
            return False

        # Step 5: Navegar para o processo
        print(f"\n[6] Procurando processo {PROCESSO}...")
        proc_resp = session.get(
            f"{BASE_URL}/Processo/ConsultaProcesso/listView.seam",
            timeout=30,
        )
        print(f"  Status: {proc_resp.status_code}, URL: {proc_resp.url}")

        # Check if we have session on PJe
        pje_body = proc_resp.text
        if "login" in proc_resp.url.lower() or "sso" in proc_resp.url.lower():
            print("  ⚠️  Redirecionado para login - sessão não transferida para PJe")
            # Try to follow the redirect chain manually
            print(f"  URL: {proc_resp.url}")
            print(f"  PJe cookies: {list(session.cookies.keys())}")
        else:
            print(f"  PJe URL: {proc_resp.url}")
            pje_keywords = ["processo", "localizar", "menu", PROCESSO]
            found_pje = [kw for kw in pje_keywords if kw in pje_body.lower()]
            print(f"  Keywords PJe: {found_pje}")

        return logged_in

    finally:
        os.unlink(cert_path)
        os.unlink(key_path)


if __name__ == "__main__":
    success = main()
    print(f"\n{'✅ SUCESSO' if success else '❌ FALHOU'}")
    sys.exit(0 if success else 1)

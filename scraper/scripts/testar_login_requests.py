"""Test with requests library (direct HTTP, not browser fetch) + mTLS."""

import asyncio
import base64
import json
import os
import re
import tempfile
import time
import uuid as uuid_mod

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12


def main():
    with open("/app/docs/Amanda Alves de Sousa_07071649316.pfx", "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, b"22051998")

    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]

    # Save PEM files for mTLS
    cert_pem = cert_obj.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain_pem = b""
    for c in additional_certs:
        chain_pem += c.public_bytes(Encoding.PEM)

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem + chain_pem); os.close(cert_fd)
    os.write(key_fd, key_pem); os.close(key_fd)

    # certChain as array
    chain_array = [base64.b64encode(cert_obj.public_bytes(Encoding.DER)).decode()]
    for c in additional_certs:
        chain_array.append(base64.b64encode(c.public_bytes(Encoding.DER)).decode())

    print(f"certChain entries: {len(chain_array)}")
    print(f"Cert PEM path: {cert_path}")
    print(f"Key PEM path: {key_path}")

    # Step 1: Get login page via requests with mTLS
    print("\n=== Step 1: Get login page (with mTLS) ===")
    session = requests.Session()

    # Set client certificate for mTLS
    session.cert = (cert_path, key_path)
    session.verify = False  # Ignore SSL verification for testing

    resp = session.get(
        "https://pje1g.trf1.jus.br/pje/login.seam",
        allow_redirects=True,
        timeout=30,
    )
    print(f"  Status: {resp.status_code}")
    print(f"  URL: {resp.url}")
    print(f"  Cookies: {dict(session.cookies)}")

    # Extract codigoSeguranca and mensagem from HTML
    html = resp.text
    match = re.search(r"autenticar\('([^']+)',\s*'([^']+)'\)", html)
    if not match:
        print("  ERROR: Could not find autenticar() in HTML!")
        print(f"  HTML (2000 chars): {html[:2000]}")
        return

    codigo_seguranca = match.group(1)
    mensagem = match.group(2)
    print(f"  codigoSeguranca: {codigo_seguranca[:60]}...")
    print(f"  mensagem: {mensagem}")

    # Extract form action
    form_match = re.search(r'id="loginForm"[^>]*action="([^"]+)"', html)
    form_action = form_match.group(1).replace("&amp;", "&") if form_match else ""
    print(f"  Form action: {form_action[:150]}")

    # Parse session params
    sc_match = re.search(r"session_code=([^&]+)", form_action)
    exec_match = re.search(r"execution=([^&]+)", form_action)
    tab_match = re.search(r"tab_id=([^&]+)", form_action)
    session_code = sc_match.group(1) if sc_match else ""
    execution = exec_match.group(1) if exec_match else ""
    tab_id = tab_match.group(1) if tab_match else ""
    print(f"  session_code: {session_code}")
    print(f"  execution: {execution}")
    print(f"  tab_id: {tab_id}")

    # Step 2: Sign mensagem
    print("\n=== Step 2: Signing mensagem ===")
    token_uuid = str(uuid_mod.uuid4())
    mensagem_bytes = mensagem.encode("utf-8")

    for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1()), ("SHA256", hashes.SHA256())]:
        sig = private_key.sign(mensagem_bytes, padding.PKCS1v15(), algo)
        sig_b64 = base64.b64encode(sig).decode()

        payload = {
            "certChain": chain_array,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_b64,
        }

        # Step 3: POST to pjeoffice-rest using same session (cookies + mTLS)
        print(f"\n=== Step 3: POST pjeoffice-rest ({algo_name}) with mTLS + session cookies ===")
        try:
            resp = session.post(
                "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://sso.cloud.pje.jus.br",
                },
                timeout=30,
            )
            print(f"  Status: {resp.status_code}")
            print(f"  Body: {resp.text[:500]}")

            if resp.status_code == 200 and "error" not in resp.text.lower():
                print("  *** SUCCESS ***")
                break
        except Exception as e:
            print(f"  Error: {e}")

    # Step 4: Submit login form
    print(f"\n=== Step 4: Submit login form with pjeoffice-code={token_uuid} ===")
    try:
        login_url = form_action if form_action.startswith("http") else f"https://sso.cloud.pje.jus.br{form_action}"
        resp = session.post(
            login_url,
            data={
                "pjeoffice-code": token_uuid,
                "phrase": "",
                "login-pje-office": "CERTIFICADO DIGITAL",
            },
            allow_redirects=True,
            timeout=30,
        )
        print(f"  Status: {resp.status_code}")
        print(f"  URL: {resp.url}")
        print(f"  Cookies: {dict(session.cookies)}")

        # Check if logged in
        body = resp.text
        keywords = ["painel", "advogado", "meus processos", "amanda", "localizar"]
        found = [kw for kw in keywords if kw in body.lower()]
        print(f"  Keywords found: {found}")
        if found:
            print("  *** LOGIN SUCCESS ***")
        else:
            print(f"  Body (2000 chars): {body[:2000]}")
    except Exception as e:
        print(f"  Error: {e}")

    # Cleanup
    os.unlink(cert_path)
    os.unlink(key_path)
    print("\nDone!")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()

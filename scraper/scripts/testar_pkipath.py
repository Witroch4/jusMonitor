"""Test PKIPath-encoded certChain.

PKIPath = ASN.1 SEQUENCE OF Certificate (DER).
This is what getCertificateChain64() returns in signer4j.
"""

import asyncio
import base64
import json
import os
import re
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


def build_pkipath_der(cert_ders: list) -> bytes:
    """Build DER-encoded ASN.1 PKIPath (SEQUENCE OF Certificate)."""
    content = b"".join(cert_ders)
    length = len(content)

    if length < 0x80:
        len_bytes = bytes([length])
    elif length < 0x100:
        len_bytes = bytes([0x81, length])
    elif length < 0x10000:
        len_bytes = bytes([0x82, length >> 8, length & 0xff])
    else:
        len_bytes = bytes([0x83, (length >> 16) & 0xff, (length >> 8) & 0xff, length & 0xff])

    return bytes([0x30]) + len_bytes + content


def main():
    with open("/app/docs/Amanda Alves de Sousa_07071649316.pfx", "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, b"22051998")

    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]

    # PEM para mTLS
    cert_pem = cert_obj.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain_pem = b""
    for c in additional_certs:
        chain_pem += c.public_bytes(Encoding.PEM)

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem + chain_pem); os.close(cert_fd)
    os.write(key_fd, key_pem); os.close(key_fd)

    # DER de cada certificado
    cert_ders = [cert_obj.public_bytes(Encoding.DER)]
    for c in additional_certs:
        cert_ders.append(c.public_bytes(Encoding.DER))

    # PKIPath com todas as ordens possíveis
    # Ordem normal: end-entity first
    pkipath_normal = build_pkipath_der(cert_ders)
    pkipath_normal_b64 = base64.b64encode(pkipath_normal).decode()

    # Ordem reversa: root first
    pkipath_reverse = build_pkipath_der(list(reversed(cert_ders)))
    pkipath_reverse_b64 = base64.b64encode(pkipath_reverse).decode()

    # Só o certificado principal (sem cadeia)
    pkipath_main = build_pkipath_der(cert_ders[:1])
    pkipath_main_b64 = base64.b64encode(pkipath_main).decode()

    print(f"PKIPath normal ({len(cert_ders)} certs): {len(pkipath_normal)} bytes → b64: {pkipath_normal_b64[:60]}...")
    print(f"PKIPath reverse ({len(cert_ders)} certs): {len(pkipath_reverse)} bytes")
    print(f"PKIPath main (1 cert): {len(pkipath_main)} bytes")

    # GET login page
    print("\n=== GET login page ===")
    session = requests.Session()
    session.cert = (cert_path, key_path)

    resp = session.get("https://pje1g.trf1.jus.br/pje/login.seam", allow_redirects=True, timeout=30)
    print(f"Status: {resp.status_code}, URL: {resp.url}")

    html = resp.text
    match = re.search(r"autenticar\('([^']+)',\s*'([^']+)'\)", html)
    if not match:
        print("ERROR: No challenge found!")
        return

    codigo_seguranca = match.group(1)
    mensagem = match.group(2)
    print(f"mensagem: {mensagem}")

    # Form action
    form_match = re.search(r'id="loginForm"[^>]*action="([^"]+)"', html)
    form_action = form_match.group(1).replace("&amp;", "&") if form_match else ""
    print(f"form_action: {form_action[:150]}")

    token_uuid = str(uuid_mod.uuid4())
    mensagem_bytes = mensagem.encode("utf-8")
    endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"

    print(f"\n=== Testing PKIPath certChain formats + all signature algorithms ===\n")

    combos = []
    for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1()), ("SHA256", hashes.SHA256())]:
        sig = private_key.sign(mensagem_bytes, padding.PKCS1v15(), algo)
        sig_b64 = base64.b64encode(sig).decode()
        for chain_name, chain_val in [
            ("pkipath_normal", pkipath_normal_b64),
            ("pkipath_reverse", pkipath_reverse_b64),
            ("pkipath_main", pkipath_main_b64),
        ]:
            combos.append((f"{algo_name}+{chain_name}", chain_val, sig_b64))

    success_combo = None
    for name, chain_val, sig_val in combos:
        payload = {
            "certChain": chain_val,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_val,
        }
        try:
            r = session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json", "Origin": "https://sso.cloud.pje.jus.br"},
                timeout=30,
            )
            body = r.text[:300]
            is_success = r.status_code == 200 and "error" not in body.lower()
            tag = " *** SUCCESS ***" if is_success else ""
            print(f"  {name}: {r.status_code} → {body}{tag}")
            if is_success:
                success_combo = name
                break
        except Exception as e:
            print(f"  {name}: ERROR {e}")

    # Also try with algoritmoAssinatura field
    print("\n=== Testing with algoritmoAssinatura field ===\n")
    algos_field = [
        ("MD5withRSA", hashes.MD5()),
        ("SHA1withRSA", hashes.SHA1()),
        ("SHA256withRSA", hashes.SHA256()),
    ]
    for algo_str, algo in algos_field:
        sig = private_key.sign(mensagem_bytes, padding.PKCS1v15(), algo)
        sig_b64 = base64.b64encode(sig).decode()
        payload = {
            "certChain": pkipath_normal_b64,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_b64,
            "algoritmoAssinatura": algo_str,
        }
        try:
            r = session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json", "Origin": "https://sso.cloud.pje.jus.br"},
                timeout=30,
            )
            body = r.text[:300]
            is_success = r.status_code == 200 and "error" not in body.lower()
            tag = " *** SUCCESS ***" if is_success else ""
            print(f"  {algo_str}: {r.status_code} → {body}{tag}")
            if is_success:
                success_combo = algo_str
                break
        except Exception as e:
            print(f"  {algo_str}: ERROR {e}")

    # Now also try an alternative: what if mensagem is NOT signed but the codigoSeguranca is?
    print("\n=== Testing sign codigoSeguranca (decoded bytes) with PKIPath ===\n")
    try:
        cs_decoded = base64.b64decode(codigo_seguranca)
        print(f"codigoSeguranca decoded: {len(cs_decoded)} bytes")
        for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1()), ("SHA256", hashes.SHA256())]:
            sig = private_key.sign(cs_decoded, padding.PKCS1v15(), algo)
            sig_b64 = base64.b64encode(sig).decode()
            payload = {
                "certChain": pkipath_normal_b64,
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": sig_b64,
            }
            r = session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            body = r.text[:300]
            is_success = r.status_code == 200 and "error" not in body.lower()
            tag = " *** SUCCESS ***" if is_success else ""
            print(f"  Sign decoded CS {algo_name}: {r.status_code} → {body}{tag}")
            if is_success:
                success_combo = f"sign_cs_{algo_name}"
                break
    except Exception as e:
        print(f"  ERROR: {e}")

    if success_combo:
        print(f"\n=== SUCCESS! Combo: {success_combo} ===")
        print(f"Submitting login form with pjeoffice-code={token_uuid}...")
        login_url = form_action if form_action.startswith("http") else f"https://sso.cloud.pje.jus.br{form_action}"
        r = session.post(
            login_url,
            data={"pjeoffice-code": token_uuid, "phrase": "", "login-pje-office": "CERTIFICADO DIGITAL"},
            allow_redirects=True, timeout=30,
        )
        print(f"Login result: {r.status_code}, URL: {r.url}")
        body = r.text
        real_keywords = ["painel", "localizar processo", "avisos", "amanda alves"]
        found = [kw for kw in real_keywords if kw in body.lower()]
        print(f"Real login keywords: {found}")
        if found:
            print("*** REAL LOGIN SUCCESS! ***")
        else:
            print(f"Body (2000): {body[:2000]}")
    else:
        print("\nNo success. Trying direct form submit to check 400 error message...")
        login_url = form_action if form_action.startswith("http") else f"https://sso.cloud.pje.jus.br{form_action}"
        r = session.post(
            login_url,
            data={"pjeoffice-code": "12345678-bad0-0000-0000-000000000000", "phrase": ""},
            allow_redirects=True, timeout=30,
        )
        print(f"Direct submit: {r.status_code}, URL: {r.url}")
        print(f"Body (1000): {r.text[:1000]}")

    # Cleanup
    os.unlink(cert_path)
    os.unlink(key_path)
    print("\nDone!")


if __name__ == "__main__":
    main()

"""Descobrir campos de SignatureData - Round 2.

certChain foi aceito no round 1. Vamos descobrir os demais.
"""

import asyncio
import json
import os
import tempfile

async def main():
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    from playwright.async_api import async_playwright

    with open("/app/docs/Amanda Alves de Sousa_07071649316.pfx", "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, b"22051998")
    cert_pem = pkcs.cert.certificate.public_bytes(Encoding.PEM)
    key_pem = pkcs.key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain = b""
    if pkcs.additional_certs:
        for c in pkcs.additional_certs:
            chain += c.certificate.public_bytes(Encoding.PEM)

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem + chain); os.close(cert_fd)
    os.write(key_fd, key_pem); os.close(key_fd)

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process"],
    )

    client_certs = [
        {"origin": "https://sso.cloud.pje.jus.br", "certPath": cert_path, "keyPath": key_path},
    ]

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        locale="pt-BR", timezone_id="America/Sao_Paulo",
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        client_certificates=client_certs,
    )

    page = await context.new_page()
    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(2)

    endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"

    async def test_fields(payload):
        js_payload = json.dumps(payload)
        result = await page.evaluate(f"""async () => {{
            const resp = await fetch('{endpoint}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({js_payload}),
            }});
            return await resp.text();
        }}""")
        return result

    # We know certChain is valid. Let's try individual fields with certChain as base
    print("=== Finding second field (with certChain) ===")
    candidates = [
        "signature", "signedData", "signedContent", "sign",
        "hash", "digest", "token", "uuid", "code",
        "plain", "content", "data", "message", "mensagem",
        "assinatura", "signatureData", "signatureValue",
        "pkcs7", "cms", "detachedSignature", "signatureBytes",
        "signedHash", "signedDigest", "signedMessage",
        "challenge", "response", "nonce",
        "applet", "result", "status", "tipo",
    ]

    for field in candidates:
        payload = {"certChain": "test", field: "test"}
        result = await test_fields(payload)
        if "Unrecognized" in result:
            # Not valid - extract which field was rejected
            if field in result:
                print(f"  {field}: REJECTED")
            else:
                print(f"  {field}: ACCEPTED (error on different field: {result[:100]})")
        else:
            print(f"  {field}: ACCEPTED! Response: {result[:200]}")

    # Now let's try the full PJeOffice approach
    # Looking for: what fields does PJeOffice actually post?
    # From the Java source (PJeOffice is open source by CNJ)
    # The task is "sso.autenticador" and sends to "/pjeoffice-rest"
    # PJeOffice signs the "mensagem" with the cert and posts:
    # - certChain: the certificate chain
    # - the signature of the mensagem
    # - the token UUID

    # Let me try more specific Java-style names
    print("\n=== More Java-style names ===")
    java_candidates = [
        "signedData", "signedContent", "signatureValue", "signatureBase64",
        "signedMessage", "signedHash", "cmsSignature", "pkcs7Data",
        "assinado", "conteudoAssinado", "signedResult",
        "signedMensagem", "signed", "sig", "s", "p7s",
        "base64Signature", "signatureB64", "signedBase64",
    ]

    for field in java_candidates:
        payload = {"certChain": "test", field: "test"}
        result = await test_fields(payload)
        if field not in result and "Unrecognized" in result:
            print(f"  {field}: ACCEPTED!")
        elif "Unrecognized" not in result:
            print(f"  {field}: POSSIBLY ACCEPTED - Response: {result[:200]}")
        else:
            pass  # rejected

    # Try finding a third field - token/uuid/code with certChain + whatever we found
    print("\n=== Looking for token-like fields ===")
    token_candidates = [
        "token", "uuid", "code", "sessionToken", "authToken",
        "requestToken", "tokenId", "id", "sessionId",
        "nonce", "challenge",
    ]

    for field in token_candidates:
        payload = {"certChain": "test", field: "test"}
        result = await test_fields(payload)
        if field not in result and "Unrecognized" in result:
            print(f"  {field}: ACCEPTED (certChain)")
        elif "Unrecognized" not in result:
            print(f"  {field}: POSSIBLY ACCEPTED - Response: {result[:200]}")

    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path); os.unlink(key_path)


if __name__ == "__main__":
    asyncio.run(main())

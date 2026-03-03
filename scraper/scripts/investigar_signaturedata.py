"""Descobrir os campos exatos de SignatureData via brute force com mensagens de erro."""

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
        {"origin": "https://pje1g.trf1.jus.br", "certPath": cert_path, "keyPath": key_path},
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

    # Test 1: Empty object
    print("=== Test 1: Empty object ===")
    r1 = await page.evaluate("""async () => {
        const resp = await fetch('""" + endpoint + """', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({}),
        });
        return {status: resp.status, body: await resp.text()};
    }""")
    print(f"Status: {r1['status']} Body: {r1['body'][:500]}")

    # Test 2: Known Java field name patterns from PJeOffice
    tests = [
        {"certificate": "test", "signature": "test", "token": "test"},
        {"certificateChain": "test", "signedData": "test", "token": "test"},
        {"cert": "test", "sign": "test", "uuid": "test"},
        {"certificado": "test", "assinatura": "test", "token": "test"},
        {"chain": "test", "hash": "test", "token": "test"},
    ]

    for i, payload in enumerate(tests, 2):
        print(f"\n=== Test {i}: {list(payload.keys())} ===")
        js_payload = json.dumps(payload)
        result = await page.evaluate(f"""async () => {{
            const resp = await fetch('{endpoint}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: '{js_payload}',
            }});
            return {{status: resp.status, body: await resp.text()}};
        }}""")
        print(f"Status: {result['status']} Body: {result['body'][:500]}")

    # Test with more specific PJeOffice fields based on the Java class name
    # br.jus.pje.pjeoffice.models.SignatureData
    more_tests = [
        {"certificate": "MIItest", "signature": "test", "token": "test", "algorithm": "SHA256withRSA"},
        {"certChain": "test", "signature": "test", "token": "test"},
        {"certificateChain": ["test"], "signature": "test", "token": "test"},
        {"x509Certificate": "test", "pkcs7Signature": "test", "token": "test"},
        # Based on typical Java signing patterns
        {"certificate": "test", "signature": "test", "token": "test", "content": "test"},
        {"certificate": "test", "signedContent": "test", "token": "test"},
        {"certificate": "test", "signature": "test", "plain": "test"},
    ]

    for i, payload in enumerate(more_tests, len(tests) + 2):
        print(f"\n=== Test {i}: {list(payload.keys())} ===")
        js_payload = json.dumps(payload)
        result = await page.evaluate(f"""async () => {{
            const resp = await fetch('{endpoint}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: '{js_payload}',
            }});
            return {{status: resp.status, body: await resp.text()}};
        }}""")
        print(f"Status: {result['status']} Body: {result['body'][:500]}")

    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path); os.unlink(key_path)


if __name__ == "__main__":
    asyncio.run(main())

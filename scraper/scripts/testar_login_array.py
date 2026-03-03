"""Test MD5withRSA + certChain as array (the working format)."""

import asyncio
import base64
import json
import os
import tempfile
import time
import uuid as uuid_mod

async def main():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    from playwright.async_api import async_playwright

    with open("/app/docs/Amanda Alves de Sousa_07071649316.pfx", "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, b"22051998")

    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]

    cert_pem = cert_obj.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain_pem = b""
    for c in additional_certs:
        chain_pem += c.public_bytes(Encoding.PEM)

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem + chain_pem); os.close(cert_fd)
    os.write(key_fd, key_pem); os.close(key_fd)

    # certChain as array of DER base64
    chain_array = [base64.b64encode(cert_obj.public_bytes(Encoding.DER)).decode("ascii")]
    for c in additional_certs:
        chain_array.append(base64.b64encode(c.public_bytes(Encoding.DER)).decode("ascii"))
    print(f"certChain array: {len(chain_array)} entries")

    # Also prepare: just main cert as array
    chain_main_only = [chain_array[0]]

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process"],
    )

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        locale="pt-BR", timezone_id="America/Sao_Paulo",
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        client_certificates=[
            {"origin": "https://sso.cloud.pje.jus.br", "certPath": cert_path, "keyPath": key_path},
            {"origin": "https://pje1g.trf1.jus.br", "certPath": cert_path, "keyPath": key_path},
        ],
    )

    page = await context.new_page()
    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(2)

    # Extract challenge
    onclick_data = await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (!btn) return null;
        const onclick = btn.getAttribute('onclick') || '';
        const match = onclick.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
        if (match) return {codigoSeguranca: match[1], mensagem: match[2]};
        return null;
    }""")

    if not onclick_data:
        print("ERROR: Could not extract challenge")
        return

    mensagem = onclick_data["mensagem"]
    codigo_seg = onclick_data["codigoSeguranca"]
    print(f"mensagem: {mensagem}")
    print(f"codigoSeguranca: {codigo_seg[:60]}...")

    token_uuid = str(uuid_mod.uuid4())
    mensagem_bytes = mensagem.encode("utf-8")
    cs_bytes = codigo_seg.encode("utf-8")

    endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"

    async def test(name, payload):
        pj = json.dumps(payload)
        r = await page.evaluate("""async (pj) => {
            try {
                const resp = await fetch('""" + endpoint + """', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: pj, credentials: 'include',
                });
                return {status: resp.status, body: await resp.text()};
            } catch (e) { return {error: e.message}; }
        }""", pj)
        s = r.get("status", "ERR")
        b = r.get("body", r.get("error", ""))[:300]
        success = s == 200 and "error" not in b.lower()
        tag = " ***SUCCESS***" if success else ""
        print(f"  {name}: {s} → {b}{tag}")
        return success

    print("\n=== Testing MD5/SHA1/SHA256 with array certChain ===\n")

    # Sign mensagem with different algos
    for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1()), ("SHA256", hashes.SHA256())]:
        sig = private_key.sign(mensagem_bytes, padding.PKCS1v15(), algo)
        sig_b64 = base64.b64encode(sig).decode("ascii")

        # Full chain array
        ok = await test(f"Sign mensagem {algo_name} + full chain array", {
            "certChain": chain_array,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_b64,
        })
        if ok:
            break

        # Main cert only array
        ok = await test(f"Sign mensagem {algo_name} + main cert array", {
            "certChain": chain_main_only,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_b64,
        })
        if ok:
            break

    print("\n=== Testing with codigoSeguranca as signed content ===\n")

    for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1()), ("SHA256", hashes.SHA256())]:
        sig = private_key.sign(cs_bytes, padding.PKCS1v15(), algo)
        sig_b64 = base64.b64encode(sig).decode("ascii")

        ok = await test(f"Sign codigoSeg {algo_name} + full chain", {
            "certChain": chain_array,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_b64,
        })
        if ok:
            break

    # Also try: sign codigoSeguranca decoded from base64 (it's a challenge)
    print("\n=== Testing with decoded codigoSeguranca (raw bytes) ===\n")
    try:
        cs_decoded = base64.b64decode(codigo_seg)
        print(f"  codigoSeguranca decoded: {len(cs_decoded)} bytes")

        for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1()), ("SHA256", hashes.SHA256())]:
            sig = private_key.sign(cs_decoded, padding.PKCS1v15(), algo)
            sig_b64 = base64.b64encode(sig).decode("ascii")

            ok = await test(f"Sign decoded CS {algo_name} + full chain", {
                "certChain": chain_array,
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": sig_b64,
            })
            if ok:
                break
    except Exception as e:
        print(f"  Failed to decode codigoSeguranca: {e}")

    # Try combining: codigoSeguranca + mensagem
    print("\n=== Testing combined content signatures ===\n")
    combined1 = codigo_seg + mensagem
    combined2 = mensagem + codigo_seg

    for what, data in [("CS+msg", combined1.encode()), ("msg+CS", combined2.encode())]:
        sig = private_key.sign(data, padding.PKCS1v15(), hashes.MD5())
        sig_b64 = base64.b64encode(sig).decode("ascii")
        await test(f"Sign {what} MD5 + full chain", {
            "certChain": chain_array,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_b64,
        })

    # Try: the token UUID is what's signed?
    print("\n=== Testing UUID as signed content ===\n")
    uuid_bytes = token_uuid.encode("utf-8")
    sig = private_key.sign(uuid_bytes, padding.PKCS1v15(), hashes.MD5())
    sig_b64 = base64.b64encode(sig).decode("ascii")
    await test("Sign UUID MD5 + full chain", {
        "certChain": chain_array,
        "uuid": token_uuid,
        "mensagem": mensagem,
        "assinatura": sig_b64,
    })

    # Try: mensagem should be the signed result, not the content
    # What if PJeOffice puts the signed content in "assinatura" and "mensagem" is just passed through?
    print("\n=== Testing: assinatura contains the TEXT, not signature ===\n")
    # Nah, that doesn't make sense. Let me try CMS format with array chain
    from cryptography.hazmat.primitives.serialization import pkcs7 as pkcs7_mod

    # CMS detached of mensagem
    builder = pkcs7_mod.PKCS7SignatureBuilder().set_data(mensagem_bytes)
    builder = builder.add_signer(cert_obj, private_key, hashes.SHA256())
    for ca in additional_certs:
        builder = builder.add_certificate(ca)
    cms_der = builder.sign(Encoding.DER, [pkcs7_mod.PKCS7Options.DetachedSignature])
    cms_b64 = base64.b64encode(cms_der).decode("ascii")

    await test("CMS SHA256 detached mensagem + full chain array", {
        "certChain": chain_array,
        "uuid": token_uuid,
        "mensagem": mensagem,
        "assinatura": cms_b64,
    })

    # Try NoAttributes
    cms_der2 = builder.sign(Encoding.DER, [pkcs7_mod.PKCS7Options.DetachedSignature, pkcs7_mod.PKCS7Options.NoAttributes])
    cms_b64_2 = base64.b64encode(cms_der2).decode("ascii")
    await test("CMS SHA256 NoAttrs detached + full chain array", {
        "certChain": chain_array,
        "uuid": token_uuid,
        "mensagem": mensagem,
        "assinatura": cms_b64_2,
    })

    # Cleanup
    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path); os.unlink(key_path)
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

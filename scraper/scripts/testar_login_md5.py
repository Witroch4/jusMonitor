"""Teste login PJe com assinatura MD5withRSA (como PJeOffice faz)."""

import asyncio
import base64
import json
import os
import tempfile
import time
import uuid as uuid_mod

async def main():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, utils
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    from playwright.async_api import async_playwright

    # ── Load PFX ──
    print("=== Loading PFX ===")
    with open("/app/docs/Amanda Alves de Sousa_07071649316.pfx", "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, b"22051998")

    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]
    print(f"  Subject: {cert_obj.subject.rfc4514_string()}")
    print(f"  Chain: {len(additional_certs)} additional certs")

    # PEM files for Playwright mTLS
    cert_pem = cert_obj.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain_pem = b""
    for c in additional_certs:
        chain_pem += c.public_bytes(Encoding.PEM)

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem + chain_pem)
    os.close(cert_fd)
    os.write(key_fd, key_pem)
    os.close(key_fd)

    # Prepare certChain formats
    # Format A: concatenated DER → base64
    all_der = cert_obj.public_bytes(Encoding.DER)
    for c in additional_certs:
        all_der += c.public_bytes(Encoding.DER)
    certchain_concat_b64 = base64.b64encode(all_der).decode("ascii")

    # Format B: each cert DER → b64, then join with newline
    cert_b64_list = [base64.b64encode(cert_obj.public_bytes(Encoding.DER)).decode("ascii")]
    for c in additional_certs:
        cert_b64_list.append(base64.b64encode(c.public_bytes(Encoding.DER)).decode("ascii"))
    certchain_newline_b64 = "\n".join(cert_b64_list)

    # Format C: just the main cert DER → b64
    certchain_main_b64 = base64.b64encode(cert_obj.public_bytes(Encoding.DER)).decode("ascii")

    # Format D: PEM without headers
    pem_no_header = cert_pem.decode("ascii")
    pem_no_header = pem_no_header.replace("-----BEGIN CERTIFICATE-----\n", "")
    pem_no_header = pem_no_header.replace("\n-----END CERTIFICATE-----\n", "")
    pem_no_header = pem_no_header.replace("\n", "")

    print(f"  certChain format A (concat DER b64): {len(certchain_concat_b64)} chars")
    print(f"  certChain format B (newline-sep b64): {len(certchain_newline_b64)} chars")
    print(f"  certChain format C (main cert b64): {len(certchain_main_b64)} chars")
    print(f"  certChain format D (PEM no headers): {len(pem_no_header)} chars")

    # ── Launch browser ──
    print("\n=== Launching Playwright ===")
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process"],
    )

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        locale="pt-BR", timezone_id="America/Sao_Paulo",
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        client_certificates=[
            {"origin": "https://sso.cloud.pje.jus.br", "certPath": cert_path, "keyPath": key_path},
            {"origin": "https://pje1g.trf1.jus.br", "certPath": cert_path, "keyPath": key_path},
        ],
    )

    try:
        from playwright_stealth import Stealth
        await Stealth().apply_stealth_async(context)
    except ImportError:
        pass

    page = await context.new_page()

    # Navigate to login
    print("\n=== Navigating to PJe login ===")
    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
    print(f"  URL: {page.url}")
    await asyncio.sleep(2)

    # Extract challenge
    print("\n=== Extracting challenge ===")
    onclick_data = await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (!btn) return null;
        const onclick = btn.getAttribute('onclick') || '';
        const match = onclick.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
        if (match) return {codigoSeguranca: match[1], mensagem: match[2]};
        return {raw: onclick};
    }""")

    if not onclick_data or "raw" in onclick_data:
        print(f"  ERROR: {onclick_data}")
        return

    codigo_seguranca = onclick_data["codigoSeguranca"]
    mensagem = onclick_data["mensagem"]
    print(f"  codigoSeguranca: {codigo_seguranca[:60]}...")
    print(f"  mensagem: {mensagem}")

    # Generate token
    token_uuid = str(uuid_mod.uuid4())
    print(f"  token UUID: {token_uuid}")

    # Sign with MD5withRSA (what PJeOffice uses)
    print("\n=== Signing with MD5withRSA ===")
    mensagem_bytes = mensagem.encode("utf-8")

    # MD5withRSA signature
    sig_md5 = private_key.sign(mensagem_bytes, padding.PKCS1v15(), hashes.MD5())
    sig_md5_b64 = base64.b64encode(sig_md5).decode("ascii")
    print(f"  MD5withRSA sig: {len(sig_md5)} bytes → b64: {sig_md5_b64[:60]}...")

    # Also prepare SHA1withRSA and SHA256withRSA as fallbacks
    sig_sha1 = private_key.sign(mensagem_bytes, padding.PKCS1v15(), hashes.SHA1())
    sig_sha1_b64 = base64.b64encode(sig_sha1).decode("ascii")

    sig_sha256 = private_key.sign(mensagem_bytes, padding.PKCS1v15(), hashes.SHA256())
    sig_sha256_b64 = base64.b64encode(sig_sha256).decode("ascii")

    endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"

    # Try all combinations
    print("\n=== Testing all combinations ===")

    combos = [
        # (name, certChain_value, assinatura_value)
        ("MD5 + concat_DER_b64", certchain_concat_b64, sig_md5_b64),
        ("MD5 + main_cert_b64", certchain_main_b64, sig_md5_b64),
        ("MD5 + PEM_no_header", pem_no_header, sig_md5_b64),
        ("SHA1 + concat_DER_b64", certchain_concat_b64, sig_sha1_b64),
        ("SHA1 + main_cert_b64", certchain_main_b64, sig_sha1_b64),
        ("SHA1 + PEM_no_header", pem_no_header, sig_sha1_b64),
        ("SHA256 + concat_DER_b64", certchain_concat_b64, sig_sha256_b64),
        ("SHA256 + main_cert_b64", certchain_main_b64, sig_sha256_b64),
        ("SHA256 + PEM_no_header", pem_no_header, sig_sha256_b64),
    ]

    best_result = None

    for name, chain_val, sig_val in combos:
        payload = {
            "certChain": chain_val,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_val,
        }
        payload_json = json.dumps(payload)

        result = await page.evaluate("""async (payloadStr) => {
            try {
                const resp = await fetch('""" + endpoint + """', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: payloadStr,
                    credentials: 'include',
                });
                const text = await resp.text();
                return {status: resp.status, body: text.substring(0, 500)};
            } catch (e) {
                return {error: e.message};
            }
        }""", payload_json)

        status = result.get("status", "ERR")
        body = result.get("body", result.get("error", ""))[:200]
        marker = "***" if status == 200 and "error" not in body.lower() else ""
        print(f"  {name}: {status} → {body} {marker}")

        if status == 200 and ("error" not in body.lower() or body.strip() in ("", "{}", "null", "true")):
            best_result = (name, token_uuid)
            break

    # If we found a working combination, submit the form
    if best_result:
        print(f"\n=== SUCCESS with {best_result[0]}! Submitting form... ===")
        await page.evaluate(f"""() => {{
            document.getElementById('pjeoffice-code').value = '{best_result[1]}';
            document.getElementById('loginForm').submit();
        }}""")

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception:
            pass
        await asyncio.sleep(3)

        print(f"  URL: {page.url}")
        body = await page.inner_text("body")
        print(f"  Body: {body[:2000]}")

        os.makedirs("/tmp/pje_test", exist_ok=True)
        await page.screenshot(path=f"/tmp/pje_test/login_success_{int(time.time())}.png", full_page=True)
    else:
        print("\n  No working combination found yet. Let me check error details...")

        # Let's try with additional debug on the 500 error
        print("\n=== Debug: checking what the server expects ===")

        # Try signing the codigoSeguranca instead of mensagem
        print("\n  Trying to sign codigoSeguranca instead of mensagem...")
        cs_bytes = codigo_seguranca.encode("utf-8")

        for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1()), ("SHA256", hashes.SHA256())]:
            sig = private_key.sign(cs_bytes, padding.PKCS1v15(), algo)
            sig_b64 = base64.b64encode(sig).decode("ascii")

            payload = {
                "certChain": certchain_main_b64,
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": sig_b64,
            }
            result = await page.evaluate("""async (payloadStr) => {
                try {
                    const resp = await fetch('""" + endpoint + """', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: payloadStr,
                        credentials: 'include',
                    });
                    const text = await resp.text();
                    return {status: resp.status, body: text.substring(0, 500)};
                } catch (e) {
                    return {error: e.message};
                }
            }""", json.dumps(payload))

            status = result.get("status", "ERR")
            body = result.get("body", "")[:200]
            print(f"    Sign codigoSeguranca with {algo_name} + main cert: {status} → {body}")

        # Try signing codigoSeguranca with certChain as concat DER
        for algo_name, algo in [("MD5", hashes.MD5()), ("SHA1", hashes.SHA1())]:
            sig = private_key.sign(cs_bytes, padding.PKCS1v15(), algo)
            sig_b64 = base64.b64encode(sig).decode("ascii")

            payload = {
                "certChain": certchain_concat_b64,
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": sig_b64,
            }
            result = await page.evaluate("""async (payloadStr) => {
                try {
                    const resp = await fetch('""" + endpoint + """', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: payloadStr,
                        credentials: 'include',
                    });
                    const text = await resp.text();
                    return {status: resp.status, body: text.substring(0, 500)};
                } catch (e) {
                    return {error: e.message};
                }
            }""", json.dumps(payload))

            status = result.get("status", "ERR")
            body = result.get("body", "")[:200]
            print(f"    Sign codigoSeguranca with {algo_name} + concat DER: {status} → {body}")

    # Cleanup
    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path)
    os.unlink(key_path)
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

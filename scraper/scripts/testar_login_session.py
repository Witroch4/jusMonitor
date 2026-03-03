"""Test with session context - include session_code, execution, cookies."""

import asyncio
import base64
import json
import os
import tempfile
import time
import uuid as uuid_mod
import re

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

    chain_array = [base64.b64encode(cert_obj.public_bytes(Encoding.DER)).decode("ascii")]
    for c in additional_certs:
        chain_array.append(base64.b64encode(c.public_bytes(Encoding.DER)).decode("ascii"))

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

    # Get form action URL (contains session_code, execution, client_id, tab_id)
    session_info = await page.evaluate("""() => {
        const form = document.getElementById('loginForm');
        const btn = document.getElementById('kc-pje-office');
        const onclick = btn ? (btn.getAttribute('onclick') || '') : '';
        const match = onclick.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);

        return {
            formAction: form ? form.action : '',
            cookies: document.cookie,
            url: window.location.href,
            codigoSeguranca: match ? match[1] : '',
            mensagem: match ? match[2] : '',
        };
    }""")

    print(f"Form action: {session_info['formAction'][:200]}")
    print(f"Cookies: {session_info['cookies'][:200]}")
    print(f"URL: {session_info['url'][:200]}")
    print(f"Mensagem: {session_info['mensagem']}")
    print(f"CodigoSeguranca: {session_info['codigoSeguranca'][:60]}...")

    # Parse session params from form action
    form_action = session_info["formAction"]
    session_code_match = re.search(r"session_code=([^&]+)", form_action)
    execution_match = re.search(r"execution=([^&]+)", form_action)
    tab_id_match = re.search(r"tab_id=([^&]+)", form_action)
    client_id_match = re.search(r"client_id=([^&]+)", form_action)

    session_code = session_code_match.group(1) if session_code_match else ""
    execution = execution_match.group(1) if execution_match else ""
    tab_id = tab_id_match.group(1) if tab_id_match else ""
    client_id = client_id_match.group(1) if client_id_match else ""

    print(f"\nSession params:")
    print(f"  session_code: {session_code}")
    print(f"  execution: {execution}")
    print(f"  tab_id: {tab_id}")
    print(f"  client_id: {client_id}")

    mensagem = session_info["mensagem"]
    token_uuid = str(uuid_mod.uuid4())
    mensagem_bytes = mensagem.encode("utf-8")

    # Sign with MD5withRSA
    sig_md5 = private_key.sign(mensagem_bytes, padding.PKCS1v15(), hashes.MD5())
    sig_md5_b64 = base64.b64encode(sig_md5).decode("ascii")

    sig_sha256 = private_key.sign(mensagem_bytes, padding.PKCS1v15(), hashes.SHA256())
    sig_sha256_b64 = base64.b64encode(sig_sha256).decode("ascii")

    base_endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"

    # Test 1: Include session params in URL
    print("\n=== Test 1: pjeoffice-rest with session params in URL ===")
    urls_to_try = [
        f"{base_endpoint}?session_code={session_code}&execution={execution}&client_id={client_id}&tab_id={tab_id}",
        f"{base_endpoint}?session_code={session_code}&tab_id={tab_id}",
        f"{base_endpoint}?execution={execution}",
    ]

    for url in urls_to_try:
        payload = {
            "certChain": chain_array,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_md5_b64,
        }
        result = await page.evaluate("""async ([url, payload]) => {
            try {
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload),
                    credentials: 'include',
                });
                return {status: resp.status, body: await resp.text()};
            } catch (e) { return {error: e.message}; }
        }""", [url, payload])
        s = result.get("status", "ERR")
        b = result.get("body", result.get("error", ""))[:300]
        print(f"  {url[:80]}...: {s} → {b}")

    # Test 2: Include session_code in payload body
    print("\n=== Test 2: session params in payload body ===")
    extra_field_combos = [
        {"sessionCode": session_code},
        {"session_code": session_code},
        {"tabId": tab_id},
        {"execution": execution},
        {"sessionCode": session_code, "tabId": tab_id},
    ]

    for extra in extra_field_combos:
        payload = {
            "certChain": chain_array,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_md5_b64,
            **extra,
        }
        result = await page.evaluate("""async (payload) => {
            try {
                const resp = await fetch('""" + base_endpoint + """', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload),
                    credentials: 'include',
                });
                return {status: resp.status, body: await resp.text()};
            } catch (e) { return {error: e.message}; }
        }""", payload)
        s = result.get("status", "ERR")
        b = result.get("body", result.get("error", ""))[:300]
        extra_keys = list(extra.keys())
        if "Unrecognized" in b:
            # field was rejected
            print(f"  extra={extra_keys}: REJECTED field ({b[:100]})")
        else:
            print(f"  extra={extra_keys}: {s} → {b}")

    # Test 3: Try httpx (outside browser) with cookies
    print("\n=== Test 3: Direct httpx POST with session cookies ===")
    cookies_str = session_info["cookies"]
    cookie_dict = {}
    for part in cookies_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookie_dict[k.strip()] = v.strip()
    print(f"  Cookies: {list(cookie_dict.keys())}")

    import httpx

    for algo_name, sig_b64 in [("MD5", sig_md5_b64), ("SHA256", sig_sha256_b64)]:
        payload = {
            "certChain": chain_array,
            "uuid": token_uuid,
            "mensagem": mensagem,
            "assinatura": sig_b64,
        }

        for url in [
            base_endpoint,
            f"{base_endpoint}?session_code={session_code}&execution={execution}&client_id={client_id}&tab_id={tab_id}",
        ]:
            try:
                async with httpx.AsyncClient(
                    timeout=30.0,
                    verify=False,
                    cookies=cookie_dict,
                ) as client:
                    resp = await client.post(
                        url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Origin": "https://sso.cloud.pje.jus.br",
                            "Referer": session_info["url"],
                        },
                    )
                    print(f"  httpx {algo_name} → {url[:60]}...: {resp.status_code} → {resp.text[:300]}")
            except Exception as e:
                print(f"  httpx {algo_name} failed: {e}")

    # Test 4: Try submitting the form directly with pjeoffice-code set
    # (without calling pjeoffice-rest first, just to see what error we get)
    print("\n=== Test 4: Submit form directly with pjeoffice-code ===")
    direct_uuid = str(uuid_mod.uuid4())
    await page.evaluate(f"""() => {{
        document.getElementById('pjeoffice-code').value = '{direct_uuid}';
    }}""")

    # Listen for response
    response_data = {}
    async def capture_response(resp):
        if "authenticate" in resp.url:
            response_data["url"] = resp.url
            response_data["status"] = resp.status
            try:
                response_data["body"] = await resp.text()
            except:
                pass

    page.on("response", capture_response)

    try:
        async with page.expect_navigation(timeout=15000):
            await page.evaluate("""() => { document.getElementById('loginForm').submit(); }""")
    except Exception as e:
        print(f"  Navigation: {e}")

    await asyncio.sleep(3)
    print(f"  Response: {response_data}")
    print(f"  Current URL: {page.url}")
    body = await page.inner_text("body")
    print(f"  Body: {body[:1000]}")

    os.makedirs("/tmp/pje_test", exist_ok=True)
    await page.screenshot(path=f"/tmp/pje_test/session_test_{int(time.time())}.png", full_page=True)

    # Cleanup
    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path); os.unlink(key_path)
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

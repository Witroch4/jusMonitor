"""Investigar o fluxo completo de login por certificado do PJe SSO.

Objetivo: entender exatamente o que o PJeOffice faz para replicar via Python.
"""

import asyncio
import json
import os
import tempfile
import time

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

    # Navigate to login
    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
    print("URL:", page.url)
    await asyncio.sleep(2)

    # 1. Get the full HTML of the cert button area
    print("\n=== FULL HTML OF CERT BUTTON AREA ===")
    html_around_btn = await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (!btn) return 'NOT FOUND';
        // Get parent's parent HTML to see context
        let el = btn;
        for (let i = 0; i < 3; i++) {
            if (el.parentElement) el = el.parentElement;
        }
        return el.outerHTML;
    }""")
    print(html_around_btn[:3000])

    # 2. Get ALL event listeners on the button
    print("\n=== EVENT LISTENERS ON CERT BUTTON ===")
    listeners = await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (!btn) return 'NOT FOUND';
        // Check onclick attribute
        const result = {
            onclick_attr: btn.getAttribute('onclick') || 'NONE',
            onclick_prop: btn.onclick ? btn.onclick.toString() : 'NONE',
        };
        return result;
    }""")
    print(json.dumps(listeners, indent=2))

    # 3. Intercept button click to see what JS it executes
    print("\n=== INTERCEPTING BUTTON CLICK ===")
    # Override autenticar() to capture its arguments
    await page.evaluate("""() => {
        window.__captured_autenticar_args = null;
        window.__original_autenticar = window.autenticar;
        window.autenticar = function() {
            window.__captured_autenticar_args = Array.from(arguments);
            console.log('INTERCEPTED autenticar:', JSON.stringify(Array.from(arguments)));
        };

        // Also override PJeOffice.executar
        window.__captured_pjeoffice_args = null;
        if (window.PJeOffice) {
            window.__original_pjeoffice_executar = window.PJeOffice.executar;
            window.PJeOffice.executar = function(req, s, e, i) {
                window.__captured_pjeoffice_args = req;
                console.log('INTERCEPTED PJeOffice.executar:', JSON.stringify(req));
            };
        }

        // Also override PJeOffice.verificarDisponibilidade
        if (window.PJeOffice) {
            window.__original_verificar = window.PJeOffice.verificarDisponibilidade;
            window.PJeOffice.verificarDisponibilidade = function(onDisponivel, onIndisponivel) {
                console.log('INTERCEPTED verificarDisponibilidade');
                // Pretend PJeOffice is available
                onDisponivel();
            };
        }
    }""")

    # Click the button
    btn = page.locator("#kc-pje-office")
    await btn.click()
    await asyncio.sleep(3)

    # Check captured args
    autenticar_args = await page.evaluate("() => window.__captured_autenticar_args")
    pjeoffice_args = await page.evaluate("() => window.__captured_pjeoffice_args")

    print(f"\nautenticar() args: {json.dumps(autenticar_args, indent=2)}")
    print(f"\nPJeOffice.executar() args: {json.dumps(pjeoffice_args, indent=2)}")

    # 4. Get console messages
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

    # Click again to trigger console logging
    await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (btn) btn.click();
    }""")
    await asyncio.sleep(2)

    print(f"\nConsole messages: {console_msgs}")

    # 5. Check the SSO pjeoffice-rest endpoint
    print("\n=== CHECKING PJEOFFICE-REST ENDPOINT ===")
    rest_check = await page.evaluate("""async () => {
        try {
            const resp = await fetch('https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest', {
                method: 'OPTIONS',
            });
            return {status: resp.status, headers: Object.fromEntries(resp.headers.entries())};
        } catch (e) {
            return {error: e.message};
        }
    }""")
    print(f"OPTIONS /pjeoffice-rest: {json.dumps(rest_check, indent=2)}")

    # 6. Try POST to pjeoffice-rest with dummy data to see response
    print("\n=== TESTING PJEOFFICE-REST ENDPOINT ===")
    rest_test = await page.evaluate("""async () => {
        try {
            const resp = await fetch('https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({test: true}),
            });
            const text = await resp.text();
            return {status: resp.status, body: text.substring(0, 1000)};
        } catch (e) {
            return {error: e.message};
        }
    }""")
    print(f"POST /pjeoffice-rest: {json.dumps(rest_test, indent=2)}")

    # 7. Try GET to pjeoffice-rest
    rest_get = await page.evaluate("""async () => {
        try {
            const resp = await fetch('https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest', {
                method: 'GET',
            });
            const text = await resp.text();
            return {status: resp.status, body: text.substring(0, 1000)};
        } catch (e) {
            return {error: e.message};
        }
    }""")
    print(f"GET /pjeoffice-rest: {json.dumps(rest_get, indent=2)}")

    # 8. Check for X.509 authenticator on Keycloak
    print("\n=== CHECKING X.509 AUTH ENDPOINT ===")
    # Try the realm's certificate-auth URL pattern
    x509_urls = [
        "https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?response_type=code&client_id=pje-trf1-1g&redirect_uri=https://pje1g.trf1.jus.br/pje/login.seam&scope=openid&kc_idp_hint=x509",
        "https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/certs",
    ]
    for url in x509_urls:
        try:
            resp = await page.evaluate(f"""async () => {{
                try {{
                    const resp = await fetch('{url}');
                    const text = await resp.text();
                    return {{status: resp.status, url: '{url}', body: text.substring(0, 500)}};
                }} catch (e) {{
                    return {{error: e.message, url: '{url}'}};
                }}
            }}""")
            print(f"  {resp.get('url', '')[:80]}: status={resp.get('status', 'err')} body={resp.get('body', resp.get('error', ''))[:200]}")
        except Exception as e:
            print(f"  Failed: {e}")

    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path); os.unlink(key_path)


if __name__ == "__main__":
    asyncio.run(main())

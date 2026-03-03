"""Investigar mecanismo de login por certificado do PJe SSO."""

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
    os.write(cert_fd, cert_pem + chain)
    os.close(cert_fd)
    os.write(key_fd, key_pem)
    os.close(key_fd)

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
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        client_certificates=client_certs,
    )

    page = await context.new_page()

    # Navigate to login
    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
    print("URL:", page.url)
    await asyncio.sleep(2)

    # Investigate the certificate button
    btn_info = await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (!btn) return {error: 'not found'};
        return {
            tagName: btn.tagName,
            type: btn.type || '',
            value: btn.value || '',
            id: btn.id,
            className: btn.className || '',
            formId: btn.form ? btn.form.id : '',
            formAction: btn.form ? btn.form.action : '',
            formMethod: btn.form ? btn.form.method : '',
        };
    }""")
    print("\nBotao CERTIFICADO DIGITAL:")
    print(json.dumps(btn_info, indent=2))

    # Get all forms
    forms = await page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('form').forEach(f => {
            const inputs = [];
            f.querySelectorAll('input, select, button').forEach(el => {
                inputs.push({
                    tag: el.tagName,
                    name: el.name || '',
                    type: el.type || '',
                    id: el.id || '',
                    value: (el.value || '').substring(0, 100),
                });
            });
            result.push({
                id: f.id || '',
                action: (f.action || '').substring(0, 200),
                method: f.method || '',
                inputs: inputs,
            });
        });
        return result;
    }""")
    print("\nForms:")
    for f in forms:
        print(f"  Form id={f['id']} action={f['action'][:150]} method={f['method']}")
        for inp in f["inputs"]:
            print(f"    {inp['tag']} name={inp['name']} type={inp['type']} id={inp['id']} value={inp['value'][:80]}")

    # Get inline scripts that reference pjeoffice or certificado
    js_content = await page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('script').forEach(s => {
            if (s.src) {
                result.push({type: 'external', src: s.src.substring(0, 200)});
            } else {
                const text = s.textContent || '';
                if (text.length > 5) {
                    result.push({type: 'inline', content: text.substring(0, 1000)});
                }
            }
        });
        return result;
    }""")
    print("\nScripts:")
    for s in js_content:
        if s["type"] == "external":
            print(f"  [ext] {s['src']}")
        else:
            print(f"  [inline] {s['content'][:300]}")

    # Try to fetch the pjeOffice.js content to understand the flow
    print("\n\nFetching pjeOffice.js...")
    try:
        pje_office_js = await page.evaluate("""async () => {
            const resp = await fetch('/auth/resources/ryzvo/login/pje-v2/js/pjeOffice.js');
            const text = await resp.text();
            return text.substring(0, 5000);
        }""")
        print("pjeOffice.js content (5000 chars):")
        print(pje_office_js)
    except Exception as e:
        print(f"Failed to fetch pjeOffice.js: {e}")

    # Also check script.js
    print("\n\nFetching script.js...")
    try:
        script_js = await page.evaluate("""async () => {
            const resp = await fetch('/auth/resources/ryzvo/login/pje-v2/js/script.js');
            const text = await resp.text();
            return text.substring(0, 5000);
        }""")
        print("script.js content (5000 chars):")
        print(script_js)
    except Exception as e:
        print(f"Failed to fetch script.js: {e}")

    # Check for hidden forms or special auth endpoints
    print("\n\nChecking for cert-auth URL pattern...")
    all_links = await page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('a[href]').forEach(a => {
            links.push({text: (a.textContent || '').trim().substring(0, 50), href: a.href.substring(0, 250)});
        });
        return links;
    }""")
    print("All links:")
    for l in all_links:
        print(f"  {l['text']} -> {l['href'][:200]}")

    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path)
    os.unlink(key_path)


if __name__ == "__main__":
    asyncio.run(main())

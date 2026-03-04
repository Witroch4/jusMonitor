"""Debug A4J response when clicking PETICIONAR."""
import asyncio
import json
import sys
import base64
import uuid as uuid_mod
import re

sys.path.insert(0, "/app")


async def login(page):
    from app.scrapers.pje_peticionamento import (
        _extract_pem_from_pfx, _sign_md5_rsa, _get_certchain_b64,
    )
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    import pyotp

    pfx_path = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    pfx_password = "22051998"
    totp_secret = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"

    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()
    cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)
    pkcs = load_pkcs12(pfx_bytes, pfx_password.encode())
    certchain_b64 = _get_certchain_b64(
        pkcs.cert.certificate,
        [c.certificate for c in (pkcs.additional_certs or [])]
    )

    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60_000)
    await asyncio.sleep(2)

    od = await page.evaluate("""() => {
        for (const el of document.querySelectorAll('[onclick]')) {
            const m = el.getAttribute('onclick')?.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
            if (m) return {mensagem: m[2]};
        }
        return null;
    }""")
    if not od: return False

    token_uuid = str(uuid_mod.uuid4())
    payload = json.dumps({
        "certChain": certchain_b64, "uuid": token_uuid,
        "mensagem": od["mensagem"],
        "assinatura": _sign_md5_rsa(pkcs.key, od["mensagem"]),
    })

    r = await page.evaluate("""async ([url, p]) => {
        try { const r = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:p,credentials:'include'}); return {status:r.status}; }
        catch(e) { return {error:e.message}; }
    }""", ["https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest", payload])
    if r.get("status") not in (200, 204): return False

    await page.evaluate("""([uuid]) => {
        const c = document.getElementById('pjeoffice-code'); if(c) c.value=uuid;
        const f = document.getElementById('loginForm'); if(!f)return;
        const b = document.createElement('input'); b.type='hidden'; b.name='login-pje-office'; b.value='CERTIFICADO DIGITAL';
        f.appendChild(b); f.submit();
    }""", [token_uuid])

    try: await page.wait_for_url(re.compile(r"(pje1g\.trf|otp|login-actions)"), timeout=30_000)
    except: pass
    await asyncio.sleep(2)

    otp = page.locator("input[name='otp'], input[id='otp']")
    if await otp.count() > 0:
        code = pyotp.TOTP(totp_secret).now()
        await otp.first.fill(code); await asyncio.sleep(0.3)
        await page.locator("input[id='kc-login']").evaluate("el => el.click()")
        try: await page.wait_for_url(re.compile(r"pje1g\.trf"), timeout=30_000)
        except: pass
        await asyncio.sleep(3)

    return "pje1g.trf1" in page.url


async def main():
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    from app.scrapers.pje_peticionamento import _extract_pem_from_pfx

    pfx_path = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    pfx_password = "22051998"
    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()
    cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)
    tag = "[A4J-DEBUG]"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            client_certificates=[
                {"origin": o, "certPath": cert_path, "keyPath": key_path}
                for o in ["https://sso.cloud.pje.jus.br", "https://pje1g.trf1.jus.br"]
            ],
        )
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        if not await login(page):
            print(f"{tag} Login failed"); await browser.close(); return
        print(f"{tag} Logged in!")

        # Go to Petição Avulsa
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Check if A4J is available
        a4j_check = await page.evaluate("""() => {
            return {
                A4J_exists: typeof A4J !== 'undefined',
                A4J_AJAX_exists: typeof A4J !== 'undefined' && typeof A4J.AJAX !== 'undefined',
                A4J_Submit_exists: typeof A4J !== 'undefined' && typeof A4J.AJAX !== 'undefined' && typeof A4J.AJAX.Submit !== 'undefined',
            };
        }""")
        print(f"{tag} A4J check: {a4j_check}")

        # Fill process number
        await page.evaluate("""() => {
            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) { el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); }
            };
            set('fPP:numeroProcesso:numeroSequencial', '1000654');
            set('fPP:numeroProcesso:numeroDigitoVerificador', '37');
            set('fPP:numeroProcesso:Ano', '2026');
            set('fPP:numeroProcesso:ramoJustica', '4');
            set('fPP:numeroProcesso:respectivoTribunal', '01');
            set('fPP:numeroProcesso:NumeroOrgaoJustica', '3704');
        }""")
        await asyncio.sleep(1)

        # Click Pesquisar
        await page.evaluate("() => document.getElementById('fPP:searchProcessosPeticao')?.click()")
        await asyncio.sleep(8)
        print(f"{tag} Search done")

        # Intercept the A4J response to see what comes back
        a4j_body = await page.evaluate("""() => {
            return new Promise((resolve) => {
                // Override XMLHttpRequest to capture next response
                const origSend = XMLHttpRequest.prototype.send;
                const origOpen = XMLHttpRequest.prototype.open;
                let capturedUrl = '';

                XMLHttpRequest.prototype.open = function(method, url, ...args) {
                    capturedUrl = url;
                    return origOpen.apply(this, [method, url, ...args]);
                };

                XMLHttpRequest.prototype.send = function(...args) {
                    const xhr = this;
                    const origOnReady = xhr.onreadystatechange;
                    xhr.onreadystatechange = function() {
                        if (xhr.readyState === 4) {
                            resolve({
                                status: xhr.status,
                                url: capturedUrl,
                                responseText: xhr.responseText?.substring(0, 5000) || '',
                                headers: xhr.getAllResponseHeaders()
                            });
                            // Restore
                            XMLHttpRequest.prototype.send = origSend;
                            XMLHttpRequest.prototype.open = origOpen;
                        }
                        if (origOnReady) origOnReady.apply(this, arguments);
                    };
                    return origSend.apply(this, args);
                };

                // Now click idPet
                const link = document.querySelector('a[id*="idPet"]');
                if (link) link.click();
                else resolve({error: 'no idPet link'});

                // Timeout after 15s
                setTimeout(() => resolve({error: 'timeout'}), 15000);
            });
        }""")

        print(f"\n{tag} A4J Response captured:")
        if isinstance(a4j_body, dict):
            print(f"   Status: {a4j_body.get('status')}")
            print(f"   URL: {a4j_body.get('url', '')[:100]}")
            resp_text = a4j_body.get('responseText', '')
            print(f"   Response ({len(resp_text)} chars):")
            # Print first 3000 chars
            for i in range(0, min(len(resp_text), 3000), 200):
                print(f"   {resp_text[i:i+200]}")

        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/a4j_debug_01.png", full_page=True)

        # Check if the page was updated by A4J
        body = await page.inner_text("body")
        has_tipo = "Tipo" in body
        has_upload = "arquivo" in body.lower() or "upload" in body.lower()
        has_editor = "editor" in body.lower() or "ckeditor" in body.lower()
        print(f"\n{tag} Page has 'Tipo': {has_tipo}")
        print(f"{tag} Page has 'arquivo/upload': {has_upload}")
        print(f"{tag} Page has 'editor/ckeditor': {has_editor}")
        print(f"{tag} Body (1500): {body[:1500]}")

        await browser.close()
        print(f"\n{tag} DONE")


asyncio.run(main())

"""Login no PJe, buscar processo na petição avulsa, e clicar para peticionar."""
import asyncio
import json
import sys
import base64
import uuid as uuid_mod
import re

sys.path.insert(0, "/app")


async def login(page, tag):
    """Full SSO + TOTP login."""
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

    onclick_data = await page.evaluate("""() => {
        for (const el of document.querySelectorAll('[onclick]')) {
            const m = el.getAttribute('onclick')?.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
            if (m) return {mensagem: m[2]};
        }
        return null;
    }""")
    if not onclick_data:
        print(f"{tag} ERROR: No challenge"); return False

    token_uuid = str(uuid_mod.uuid4())
    payload = json.dumps({
        "certChain": certchain_b64, "uuid": token_uuid,
        "mensagem": onclick_data["mensagem"],
        "assinatura": _sign_md5_rsa(pkcs.key, onclick_data["mensagem"]),
    })

    r = await page.evaluate("""async ([url, p]) => {
        try { const r = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:p,credentials:'include'}); return {status:r.status}; }
        catch(e) { return {error:e.message}; }
    }""", ["https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest", payload])
    if r.get("status") not in (200, 204):
        print(f"{tag} ERROR: SSO {r}"); return False

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
        code = __import__("pyotp").TOTP(totp_secret).now()
        await otp.first.fill(code)
        await asyncio.sleep(0.3)
        sub = page.locator("input[name='login'], input[id='kc-login'], button[type='submit']")
        if await sub.count() > 0: await sub.first.click()
        else: await otp.first.press("Enter")
        try: await page.wait_for_url(re.compile(r"pje1g\.trf"), timeout=20_000)
        except: pass
        await asyncio.sleep(2)

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

    tag = "[PET2]"

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

        if not await login(page, tag):
            await browser.close(); return
        print(f"{tag} Logged in!")

        # === Go to Petição Avulsa ===
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Fill process number: 1000654-37.2026.4.01.3704
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
        await page.evaluate("""() => {
            document.getElementById('fPP:searchProcessosPeticao')?.click();
        }""")
        await asyncio.sleep(8)
        print(f"{tag} Search done, URL: {page.url}")

        # Verify process found
        count = await page.evaluate("""() => {
            const text = document.body.innerText;
            const m = text.match(/(\\d+) resultados encontrados/);
            return m ? parseInt(m[1]) : 0;
        }""")
        print(f"{tag} Results found: {count}")

        if count == 0:
            print(f"{tag} ERROR: Process not found!")
            await browser.close(); return

        await page.screenshot(path="/tmp/pet2_01_found.png", full_page=True)

        # === Click the petition link (idPet) ===
        print(f"\n{tag} Clicking petition link...")
        # The link uses A4J.AJAX.Submit - we need to trigger it via JS
        clicked = await page.evaluate("""() => {
            // Find the petition link in the table
            const links = document.querySelectorAll('a[id*="idPet"]');
            if (links.length > 0) {
                links[0].click();
                return 'clicked: ' + links[0].id;
            }
            // Fallback: try clAP
            const clap = document.querySelectorAll('a[id*="clAP"]');
            if (clap.length > 0) {
                clap[0].click();
                return 'clicked clAP: ' + clap[0].id;
            }
            return 'no link found';
        }""")
        print(f"{tag} Click result: {clicked}")
        await asyncio.sleep(8)
        await page.screenshot(path="/tmp/pet2_02_after_click.png", full_page=True)
        print(f"{tag} URL after click: {page.url}")

        body = await page.inner_text("body")
        print(f"{tag} Body (1500): {body[:1500]}")

        # Check for tipo peticao, upload, etc
        elements = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('input, select, textarea, button, a').forEach(el => {
                const id = el.id || '';
                const name = el.name || '';
                const text = el.textContent?.trim().substring(0, 60) || '';
                if (el.offsetParent !== null && (id || text)) {
                    result.push({
                        tag: el.tagName,
                        id: id.substring(0, 60),
                        type: el.type || '',
                        text: text,
                        href: el.href?.substring(0, 80) || ''
                    });
                }
            });
            return result;
        }""")
        print(f"\n{tag} Visible elements ({len(elements)}):")
        for el in elements:
            print(f"   {el['tag']} id={el['id'][:50]} type={el['type']} text={el['text'][:40]}")

        # Look for file upload elements
        file_inputs = await page.evaluate("""() => {
            const inputs = document.querySelectorAll('input[type="file"]');
            return Array.from(inputs).map(i => ({id: i.id, name: i.name, accept: i.accept}));
        }""")
        print(f"\n{tag} File upload inputs: {json.dumps(file_inputs)}")

        # Look for selects (tipo peticão, etc)
        selects = await page.evaluate("""() => {
            const sels = document.querySelectorAll('select');
            return Array.from(sels).filter(s => s.offsetParent !== null).map(s => {
                const opts = Array.from(s.options).map(o => ({value: o.value, text: o.textContent.trim().substring(0, 60)}));
                return {id: s.id, name: s.name, options: opts.slice(0, 20)};
            });
        }""")
        print(f"\n{tag} Visible selects:")
        for sel in selects:
            print(f"   SELECT id={sel['id'][:50]}")
            for opt in sel['options'][:10]:
                print(f"      [{opt['value'][:20]}] {opt['text']}")

        # Look for iframes (PJe sometimes uses iframes for document editing)
        iframes = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('iframe')).map(f => ({
                id: f.id, name: f.name, src: f.src?.substring(0, 100) || '',
                width: f.width, height: f.height
            }));
        }""")
        print(f"\n{tag} Iframes: {json.dumps(iframes)}")

        await browser.close()
        print(f"\n{tag} DONE")


asyncio.run(main())

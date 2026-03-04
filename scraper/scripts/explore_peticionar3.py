"""Login, buscar processo, clicar PETICIONAR e explorar formulário."""
import asyncio
import json
import sys
import base64
import uuid as uuid_mod
import re

sys.path.insert(0, "/app")


async def login(page, tag):
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
        code = __import__("pyotp").TOTP(totp_secret).now()
        await otp.first.fill(code); await asyncio.sleep(0.3)
        sub = page.locator("input[name='login'], input[id='kc-login'], button[type='submit']")
        if await sub.count() > 0:
            await sub.first.evaluate("el => el.click()")
        else:
            await otp.first.press("Enter")
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
    tag = "[PET3]"

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
            print(f"{tag} Login failed"); await browser.close(); return
        print(f"{tag} Logged in!")

        # === Go to Petição Avulsa and search ===
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

        # Click Pesquisar via A4J (capture its onclick)
        await page.evaluate("""() => {
            document.getElementById('fPP:searchProcessosPeticao')?.click();
        }""")
        await asyncio.sleep(8)

        count_text = await page.inner_text("body")
        print(f"{tag} Found process: {'resultados encontrados' in count_text}")

        # === Get full onclick of the PETICIONAR button ===
        onclick_info = await page.evaluate("""() => {
            const links = document.querySelectorAll('a[id*="idPet"], a[id*="clAP"]');
            return Array.from(links).map(l => ({
                id: l.id,
                onclick: l.getAttribute('onclick') || '',
                href: l.href || '',
                innerHTML: l.innerHTML.substring(0, 200),
                className: l.className
            }));
        }""")
        print(f"\n{tag} Action links:")
        for link in onclick_info:
            print(f"   id={link['id']}")
            print(f"   onclick={link['onclick'][:300]}")
            print(f"   innerHTML={link['innerHTML'][:100]}")
            print()

        # === Try clicking idPet and listening for navigation/A4J response ===
        print(f"{tag} Clicking idPet and waiting for A4J response...")

        # Monitor network to see what A4J sends back
        responses_collected = []
        def on_response(response):
            if "peticao" in response.url.lower() or "seam" in response.url.lower():
                responses_collected.append({
                    "url": response.url[:150],
                    "status": response.status,
                    "headers": dict(response.headers) if hasattr(response, 'headers') else {}
                })

        page.on("response", on_response)

        # Click the PETICIONAR button
        await page.evaluate("""() => {
            const link = document.querySelector('a[id*="idPet"]');
            if (link) link.click();
        }""")

        # Wait longer for A4J response and potential page change
        await asyncio.sleep(10)
        await page.screenshot(path="/tmp/pet3_01_after_pet_click.png", full_page=True)
        print(f"{tag} URL: {page.url}")
        print(f"{tag} Network responses: {json.dumps(responses_collected[:5], indent=2)}")

        body = await page.inner_text("body")
        print(f"{tag} Body (2000): {body[:2000]}")

        # Check if page content changed (new form elements?)
        new_elements = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('select, textarea, input[type="file"], iframe').forEach(el => {
                result.push({
                    tag: el.tagName, id: el.id, name: el.name || '',
                    type: el.type || '', visible: el.offsetParent !== null,
                    src: el.src?.substring(0, 100) || ''
                });
            });
            return result;
        }""")
        print(f"\n{tag} Selects/textareas/files/iframes:")
        for el in new_elements:
            vis = "V" if el.get("visible") else "H"
            print(f"   [{vis}] {el['tag']} id={el['id'][:50]} type={el['type']} src={el.get('src','')[:50]}")

        # === Try the other approach: clAP link ===
        print(f"\n{'='*60}")
        print(f"{tag} Trying clAP link instead...")
        # First go back to petição avulsa
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Fill and search again
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
        await page.evaluate("() => document.getElementById('fPP:searchProcessosPeticao')?.click()")
        await asyncio.sleep(8)

        # Click clAP
        await page.evaluate("""() => {
            const link = document.querySelector('a[id*="clAP"]');
            if (link) link.click();
        }""")
        await asyncio.sleep(10)
        await page.screenshot(path="/tmp/pet3_02_after_clap.png", full_page=True)
        print(f"{tag} URL after clAP: {page.url}")

        body = await page.inner_text("body")
        print(f"{tag} Body after clAP (2000): {body[:2000]}")

        # Check for navigation to a new page
        new_elements2 = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('select, textarea, input[type="file"], iframe, input[type="text"]').forEach(el => {
                if (el.offsetParent !== null) {
                    result.push({
                        tag: el.tagName, id: el.id?.substring(0, 60) || '', name: el.name || '',
                        type: el.type || ''
                    });
                }
            });
            return result;
        }""")
        print(f"\n{tag} Visible form elements after clAP:")
        for el in new_elements2:
            print(f"   {el['tag']} id={el['id'][:50]} type={el['type']}")

        await browser.close()
        print(f"\n{tag} DONE")


asyncio.run(main())

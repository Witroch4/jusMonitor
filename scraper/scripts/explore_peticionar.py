"""Login no PJe e explorar o fluxo completo de petição avulsa."""
import asyncio
import json
import sys
import base64
import uuid as uuid_mod
import re

sys.path.insert(0, "/app")


async def login(page, tag):
    """Do the full SSO + TOTP login, return True on success."""
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
    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]
    certchain_b64 = _get_certchain_b64(cert_obj, additional_certs)

    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60_000)
    await asyncio.sleep(2)

    onclick_data = await page.evaluate("""() => {
        const allElems = document.querySelectorAll('[onclick]');
        for (const el of allElems) {
            const oc = el.getAttribute('onclick') || '';
            const m = oc.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
            if (m) return {mensagem: m[2]};
        }
        return null;
    }""")
    if not onclick_data:
        print(f"{tag} ERROR: No challenge"); return False

    token_uuid = str(uuid_mod.uuid4())
    sso_payload = json.dumps({
        "certChain": certchain_b64, "uuid": token_uuid,
        "mensagem": onclick_data["mensagem"],
        "assinatura": _sign_md5_rsa(private_key, onclick_data["mensagem"]),
    })

    r = await page.evaluate("""async ([url, p]) => {
        try { const r = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:p,credentials:'include'}); return {status:r.status}; }
        catch(e) { return {error:e.message}; }
    }""", ["https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest", sso_payload])
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
        code = pyotp.TOTP(totp_secret).now()
        await otp.first.fill(code)
        await asyncio.sleep(0.3)
        sub = page.locator("input[name='login'], input[id='kc-login'], button[type='submit']")
        if await sub.count() > 0: await sub.first.click()
        else: await otp.first.press("Enter")
        try: await page.wait_for_url(re.compile(r"pje1g\.trf"), timeout=20_000)
        except: pass
        await asyncio.sleep(2)
        print(f"{tag} TOTP OK")

    print(f"{tag} Logged in: {page.url}")
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

    tag = "[PETICIONAR]"

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
            await browser.close()
            return

        # === Step 1: Go to Petição Avulsa ===
        print(f"\n{'='*60}")
        print(f"{tag} Step 1: Navigate to Petição Avulsa")
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/pet_01_form.png", full_page=True)

        # === Step 2: Fill process number 1000654-37.2026.4.01.3704 ===
        print(f"{tag} Step 2: Filling process number...")
        # NNNNNNN-DD.AAAA.J.TT.OOOO
        # 1000654-37.2026.4.01.3704
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
        await page.screenshot(path="/tmp/pet_02_filled.png", full_page=True)

        # === Step 3: Click Pesquisar ===
        print(f"{tag} Step 3: Clicking Pesquisar...")
        # Use JS click because JSF buttons use onclick handlers
        await page.evaluate("""() => {
            const btn = document.getElementById('fPP:searchProcessosPeticao');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(8)
        await page.screenshot(path="/tmp/pet_03_search_result.png", full_page=True)
        print(f"{tag} URL after search: {page.url}")

        # Check what happened
        body = await page.inner_text("body")
        print(f"{tag} Body text (1000): {body[:1000]}")

        # Look for process results or errors
        results = await page.evaluate("""() => {
            const rows = document.querySelectorAll('table tbody tr, .rf-dt-r, .rich-table-row');
            const data = [];
            for (const row of rows) {
                const cells = row.querySelectorAll('td');
                const text = Array.from(cells).map(c => c.textContent.trim().substring(0, 50)).join(' | ');
                if (text) data.push(text);
            }
            return data;
        }""")
        print(f"{tag} Table rows: {json.dumps(results[:10], indent=2)}")

        # Check for any error messages
        errors = await page.evaluate("""() => {
            const msgs = document.querySelectorAll('.rich-messages, .ui-message, .alert, .error, .msg-error, .mensagem');
            return Array.from(msgs).map(m => m.textContent.trim().substring(0, 200));
        }""")
        print(f"{tag} Messages: {json.dumps(errors)}")

        # Get all visible form elements now (may have changed after search)
        elements = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('input, select, textarea, button').forEach(el => {
                if (el.offsetParent !== null || el.type === 'button') {
                    result.push({
                        tag: el.tagName,
                        id: el.id || '',
                        name: el.name || '',
                        type: el.type || '',
                        value: el.value?.substring(0, 50) || '',
                        text: el.textContent?.trim().substring(0, 50) || ''
                    });
                }
            });
            return result;
        }""")
        print(f"\n{tag} Current form elements ({len(elements)}):")
        for el in elements:
            print(f"   {el['tag']} id={el['id'][:50]} type={el['type']} val={el['value'][:30]} text={el['text'][:30]}")

        # Check if a process was found and there are next steps
        # Try clicking on any process row
        process_link = await page.evaluate("""() => {
            const links = document.querySelectorAll('a[onclick*="processo"], a[id*="processo"], a[id*="Processo"]');
            return Array.from(links).map(l => ({id: l.id, text: l.textContent.trim().substring(0, 80), onclick: (l.getAttribute('onclick') || '').substring(0, 100)}));
        }""")
        print(f"\n{tag} Process links: {json.dumps(process_link[:5], indent=2)}")

        # === Step 4: Also try via the Consulta detail URL that worked ===
        print(f"\n{'='*60}")
        print(f"{tag} Step 4: Consulta detail page")
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/ConsultaProcesso/Detalhe/listView.seam?ca=10006543720264013704", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        await page.screenshot(path="/tmp/pet_04_consulta_detail.png", full_page=True)
        print(f"{tag} URL: {page.url}")
        body = await page.inner_text("body")
        print(f"{tag} Body (1500): {body[:1500]}")

        # Look for "peticionar" button in process detail
        pet_buttons = await page.evaluate("""() => {
            const all = document.querySelectorAll('a, button, input[type="button"]');
            return Array.from(all)
                .filter(el => {
                    const text = (el.textContent || '').toLowerCase();
                    const id = (el.id || '').toLowerCase();
                    return text.includes('peticion') || text.includes('juntar') ||
                           text.includes('protocolo') || text.includes('documento') ||
                           id.includes('peticion') || id.includes('juntar');
                })
                .map(el => ({
                    tag: el.tagName, id: el.id, text: el.textContent.trim().substring(0, 80),
                    href: el.href || '', onclick: (el.getAttribute('onclick') || '').substring(0, 100)
                }));
        }""")
        print(f"\n{tag} Petition/document buttons: {json.dumps(pet_buttons, indent=2)}")

        # Get all action buttons/links on the process detail page
        actions = await page.evaluate("""() => {
            const btns = document.querySelectorAll('a[onclick], button[onclick], input[type="button"]');
            return Array.from(btns)
                .filter(el => el.offsetParent !== null)
                .map(el => ({
                    tag: el.tagName, id: el.id?.substring(0, 50) || '',
                    text: el.textContent?.trim().substring(0, 50) || '',
                    onclick: (el.getAttribute('onclick') || '').substring(0, 80)
                }));
        }""")
        print(f"\n{tag} Action buttons: {json.dumps(actions[:20], indent=2)}")

        await browser.close()
        print(f"\n{tag} DONE")


asyncio.run(main())

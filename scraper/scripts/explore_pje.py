"""Login no PJe e explorar navegação via URLs diretas."""
import asyncio
import json
import sys
import base64
import uuid as uuid_mod
import re

sys.path.insert(0, "/app")


async def main():
    from app.scrapers.pje_peticionamento import (
        _extract_pem_from_pfx, _sign_md5_rsa, _get_certchain_b64,
    )
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    import pyotp

    pfx_path = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    pfx_password = "22051998"
    totp_secret = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"
    tag = "[EXPLORE]"

    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()

    cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)
    pkcs = load_pkcs12(pfx_bytes, pfx_password.encode())
    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]
    certchain_b64 = _get_certchain_b64(cert_obj, additional_certs)

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

        # === LOGIN (compact) ===
        await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60_000)
        await asyncio.sleep(2)

        onclick_data = await page.evaluate("""() => {
            const allElems = document.querySelectorAll('[onclick]');
            for (const el of allElems) {
                const oc = el.getAttribute('onclick') || '';
                const m = oc.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
                if (m) return {codigoSeguranca: m[1], mensagem: m[2]};
            }
            return null;
        }""")
        if not onclick_data:
            print(f"{tag} ERROR: No challenge"); await browser.close(); return

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
            print(f"{tag} ERROR: SSO {r}"); await browser.close(); return
        print(f"{tag} SSO OK")

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
            print(f"{tag} TOTP OK: {code}")

        print(f"{tag} Logged in: {page.url}")

        # === EXPLORE 1: Petição Avulsa (PETICIONAR menu) ===
        print(f"\n{'='*60}")
        print(f"{tag} EXPLORE 1: Petição Avulsa")
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/explore_peticao_avulsa.png", full_page=True)
        print(f"{tag} URL: {page.url}")

        # Dump all inputs/selects/buttons
        elements = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('input, select, textarea, button').forEach(el => {
                result.push({
                    tag: el.tagName,
                    id: el.id || '',
                    name: el.name || '',
                    type: el.type || '',
                    placeholder: el.placeholder || '',
                    value: el.value || '',
                    text: el.textContent?.trim().substring(0, 50) || '',
                    visible: el.offsetParent !== null
                });
            });
            return result;
        }""")
        visible_elements = [e for e in elements if e.get("visible")]
        print(f"{tag} Visible form elements ({len(visible_elements)}):")
        for el in visible_elements:
            print(f"   {el['tag']} id={el['id'][:40]} name={el['name'][:30]} type={el['type']} val={el['value'][:30]} text={el['text'][:30]}")

        body = await page.inner_text("body")
        print(f"{tag} Body text: {body[:800]}")

        # === EXPLORE 2: Search process in sidebar ===
        print(f"\n{'='*60}")
        print(f"{tag} EXPLORE 2: Painel search")
        await page.goto("https://pje1g.trf1.jus.br/pje/Painel/painel_usuario/advogado.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Get search-related elements
        search_elements = await page.evaluate("""() => {
            const els = document.querySelectorAll('input[placeholder*="Pesquise"], input[placeholder*="processo"], button[ng-click*="pesq"]');
            return Array.from(els).map(e => ({tag: e.tagName, id: e.id, placeholder: e.placeholder, onclick: e.getAttribute('ng-click') || e.getAttribute('onclick') || ''}));
        }""")
        print(f"{tag} Search elements: {json.dumps(search_elements, indent=2)}")

        # Try to fill and submit search via JS
        await page.evaluate("""(numero) => {
            const input = document.querySelector('input[placeholder*="Pesquise"]');
            if (input) {
                input.value = numero;
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""", "1000654-37.2026.4.01.3704")
        await asyncio.sleep(1)

        # Find and click the search button via JS
        clicked = await page.evaluate("""() => {
            // Try the lupa icon button
            const btns = document.querySelectorAll('.input-group-addon, button');
            for (const btn of btns) {
                if (btn.querySelector('i.fa-search') || btn.querySelector('.glyphicon-search') ||
                    btn.getAttribute('ng-click')?.includes('pesq')) {
                    btn.click();
                    return 'clicked: ' + (btn.id || btn.className || btn.tagName);
                }
            }
            // Angular: try triggering the search function
            const scope = angular?.element(document.querySelector('input[placeholder*="Pesquise"]'))?.scope?.();
            if (scope?.pesquisar) { scope.pesquisar(); return 'called scope.pesquisar()'; }
            return 'no button found';
        }""")
        print(f"{tag} Search click: {clicked}")
        await asyncio.sleep(5)
        await page.screenshot(path="/tmp/explore_search_result.png", full_page=True)
        print(f"{tag} After search URL: {page.url}")
        body = await page.inner_text("body")
        print(f"{tag} After search text: {body[:800]}")

        # === EXPLORE 3: Consulta Processos form ===
        print(f"\n{'='*60}")
        print(f"{tag} EXPLORE 3: Consulta Processos form")
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/ConsultaProcesso/listView.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Get all inputs
        inputs = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('input, select').forEach(el => {
                if (el.type === 'hidden') return;
                result.push({
                    tag: el.tagName,
                    id: el.id,
                    name: el.name || '',
                    type: el.type,
                    maxLength: el.maxLength,
                    placeholder: el.placeholder || '',
                    value: el.value || ''
                });
            });
            return result;
        }""")
        print(f"{tag} Form inputs:")
        for inp in inputs:
            print(f"   {inp['tag']} id={inp['id'][:50]} name={inp['name'][:30]} type={inp['type']} maxLen={inp.get('maxLength','')} val={inp['value']}")

        # Try to fill "Número do processo" field
        # PJe splits it: NNNNNNN-DD.AAAA.J.TT.OOOO
        fill_result = await page.evaluate("""() => {
            // Look for inputs related to processo number
            const inputs = document.querySelectorAll('input');
            const processInputs = [];
            for (const inp of inputs) {
                if (inp.id && (inp.id.includes('umeroOrgaoJustica') || inp.id.includes('umeroProcesso') ||
                    inp.id.includes('igito') || inp.id.includes('Ano') || inp.id.includes('ustica') ||
                    inp.id.includes('ribunal') || inp.id.includes('rigem'))) {
                    processInputs.push({id: inp.id, maxLength: inp.maxLength});
                }
            }
            return processInputs;
        }""")
        print(f"{tag} Process number inputs: {json.dumps(fill_result, indent=2)}")

        # === EXPLORE 4: Direct process detail URLs ===
        print(f"\n{'='*60}")
        print(f"{tag} EXPLORE 4: Direct process URLs")

        # Try different URL patterns
        urls_to_try = [
            "https://pje1g.trf1.jus.br/pje/ConsultaPublica/DetalheProcessoConsultaPublica/listView.seam?ca=10006543720264013704",
            "https://pje1g.trf1.jus.br/pje/Processo/ConsultaProcesso/Detalhe/listProcessoCompletoAdvogado.seam?processo.id=10006543720264013704",
            "https://pje1g.trf1.jus.br/pje/Processo/ConsultaProcesso/Detalhe/listView.seam?ca=10006543720264013704",
        ]
        for url in urls_to_try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            body_short = (await page.inner_text("body"))[:200]
            print(f"{tag} {url[-60:]}")
            print(f"   → {page.url[:80]}")
            print(f"   → {body_short[:150]}")

        # === EXPLORE 5: Petição Avulsa - fill process number ===
        print(f"\n{'='*60}")
        print(f"{tag} EXPLORE 5: Fill Petição Avulsa form")
        await page.goto("https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Get ALL inputs including hidden
        all_inputs = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('input, select, textarea').forEach(el => {
                result.push({
                    tag: el.tagName,
                    id: el.id,
                    name: el.name || '',
                    type: el.type,
                    maxLength: el.maxLength,
                    value: el.value || '',
                    visible: el.offsetParent !== null
                });
            });
            return result;
        }""")
        print(f"{tag} All form elements:")
        for inp in all_inputs:
            vis = "V" if inp.get("visible") else "H"
            print(f"   [{vis}] {inp['tag']} id={inp['id'][:60]} type={inp['type']} maxLen={inp.get('maxLength','')} val={inp['value'][:20]}")

        # Get labels too for context
        labels = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('label')).map(l => ({
                for: l.getAttribute('for') || '',
                text: l.textContent.trim().substring(0, 50)
            }));
        }""")
        print(f"{tag} Labels:")
        for lbl in labels:
            print(f"   {lbl['for']}: {lbl['text']}")

        await browser.close()
        print(f"\n{tag} DONE")


asyncio.run(main())

"""Explora o popup de peticionamento do PJe para mapear o fluxo completo."""
import asyncio
import json
import sys
import base64
import uuid as uuid_mod
import re

sys.path.insert(0, "/app")


async def login_and_get_popup_url(page, tag):
    """Login completo e retorna a URL do popup de peticionamento."""
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
    if not od:
        print(f"{tag} ERROR: No challenge"); return None

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
    if r.get("status") not in (200, 204):
        print(f"{tag} ERROR: SSO {r}"); return None

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
        print(f"{tag} TOTP OK: {code}")

    if "pje1g.trf1" not in page.url:
        print(f"{tag} ERROR: Login failed, URL: {page.url}"); return None

    print(f"{tag} Logged in: {page.url}")

    # Vai para petição avulsa
    await page.goto("https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam", wait_until="domcontentloaded")
    await asyncio.sleep(3)

    # Preenche número do processo
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

    # Intercepta URL do popup via XHR
    popup_url = await page.evaluate("""() => {
        return new Promise((resolve) => {
            const origSend = XMLHttpRequest.prototype.send;
            const origOpen = XMLHttpRequest.prototype.open;

            XMLHttpRequest.prototype.send = function(...args) {
                const xhr = this;
                const origOnReady = xhr.onreadystatechange;
                xhr.onreadystatechange = function() {
                    if (xhr.readyState === 4) {
                        const m = xhr.responseText?.match(/var link="([^"]+)"/);
                        if (m) resolve(m[1]);
                        else resolve(null);
                        XMLHttpRequest.prototype.send = origSend;
                        XMLHttpRequest.prototype.open = origOpen;
                    }
                    if (origOnReady) origOnReady.apply(this, arguments);
                };
                return origSend.apply(this, args);
            };

            const link = document.querySelector('a[id*="idPet"]');
            if (link) link.click();
            else resolve(null);
            setTimeout(() => resolve(null), 15000);
        });
    }""")

    print(f"{tag} Popup URL: {popup_url}")
    return popup_url


async def main():
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    from app.scrapers.pje_peticionamento import _extract_pem_from_pfx

    pfx_path = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    pfx_password = "22051998"
    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()
    cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)
    tag = "[POPUP]"

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

        popup_url = await login_and_get_popup_url(page, tag)
        if not popup_url:
            print(f"{tag} ERROR: Could not get popup URL"); await browser.close(); return

        # ============================================================
        # Navega para o popup de peticionamento (mesma aba, não popup)
        # ============================================================
        print(f"\n{'='*60}")
        print(f"{tag} Navigating to popup: {popup_url[:120]}")
        await page.goto(popup_url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(5)
        await page.screenshot(path="/tmp/popup_01_initial.png", full_page=True)
        print(f"{tag} URL: {page.url}")

        body = await page.inner_text("body")
        print(f"{tag} Body (2500):\n{body[:2500]}")

        # ============================================================
        # Mapeamento completo dos elementos do formulário
        # ============================================================
        all_elements = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('input, select, textarea, button, a[onclick]').forEach(el => {
                result.push({
                    tag: el.tagName,
                    id: el.id || '',
                    name: el.name || '',
                    type: el.type || '',
                    value: (el.value || '').substring(0, 60),
                    text: (el.textContent || '').trim().substring(0, 60),
                    placeholder: el.placeholder || '',
                    visible: el.offsetParent !== null,
                    accept: el.accept || '',
                    onclick: (el.getAttribute('onclick') || '').substring(0, 120)
                });
            });
            return result;
        }""")
        print(f"\n{tag} ALL elements ({len(all_elements)}):")
        for el in all_elements:
            vis = "V" if el.get("visible") else "H"
            print(f"  [{vis}] {el['tag']:8} id={el['id'][:60]:60} type={el['type']:10} val={el['value'][:30]:30} text={el['text'][:30]}")

        # ============================================================
        # SELECTs com opções
        # ============================================================
        selects = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('select')).map(s => {
                const opts = Array.from(s.options).map(o => ({v: o.value.substring(0,30), t: o.textContent.trim().substring(0,80)}));
                return {id: s.id, name: s.name, visible: s.offsetParent !== null, options: opts};
            });
        }""")
        print(f"\n{tag} SELECTS:")
        for sel in selects:
            vis = "V" if sel.get("visible") else "H"
            print(f"  [{vis}] SELECT id={sel['id'][:60]}")
            for opt in sel['options'][:15]:
                print(f"     [{opt['v']}] {opt['t']}")

        # ============================================================
        # File inputs e dropzone
        # ============================================================
        file_info = await page.evaluate("""() => {
            const files = Array.from(document.querySelectorAll('input[type="file"]')).map(i => ({
                id: i.id, name: i.name, accept: i.accept, multiple: i.multiple,
                visible: i.offsetParent !== null
            }));
            const dz = Array.from(document.querySelectorAll('.dropzone, [id*="ropzone"], [id*="upload"]')).map(d => ({
                id: d.id, class: d.className.substring(0,40), text: d.textContent.trim().substring(0,100)
            }));
            return {files, dropzones: dz};
        }""")
        print(f"\n{tag} FILE INPUTS: {json.dumps(file_info, indent=2)}")

        # ============================================================
        # Iframes
        # ============================================================
        iframes = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('iframe')).map(f => ({
                id: f.id, name: f.name, src: f.src?.substring(0,120) || '',
                width: f.width, height: f.height, visible: f.offsetParent !== null
            }));
        }""")
        print(f"\n{tag} IFRAMES: {json.dumps(iframes, indent=2)}")

        # ============================================================
        # Labels
        # ============================================================
        labels = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('label')).map(l => ({
                for: l.getAttribute('for') || '',
                text: l.textContent.trim().substring(0, 80)
            }));
        }""")
        print(f"\n{tag} LABELS:")
        for lbl in labels:
            print(f"  [{lbl['for'][:40]}] {lbl['text']}")

        # ============================================================
        # Mensagens / erros
        # ============================================================
        messages = await page.evaluate("""() => {
            const msgs = [];
            document.querySelectorAll('.rf-msgs-sum, .rf-msg, .alert, .ui-message, .mensagem, [class*="error"], [class*="warning"], [class*="msg"]').forEach(m => {
                const text = m.textContent.trim();
                if (text.length > 2 && text.length < 300) msgs.push(text);
            });
            return [...new Set(msgs)];
        }""")
        print(f"\n{tag} MESSAGES: {json.dumps(messages[:10], indent=2)}")

        # ============================================================
        # Salva HTML para análise off-line
        # ============================================================
        html = await page.content()
        with open("/tmp/popup_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n{tag} HTML salvo: /tmp/popup_page.html ({len(html)} chars)")

        # ============================================================
        # Testa fechar o modal PJeOffice se aparecer e re-scannear
        # ============================================================
        await page.evaluate("""() => {
            document.querySelectorAll('.modal.in .close, .modal.show .close, [data-dismiss="modal"]').forEach(b => b.click());
            const openedState = document.getElementById('mpPJeOfficeIndisponivelOpenedState');
            if (openedState) openedState.value = '';
        }""")
        await asyncio.sleep(2)
        await page.screenshot(path="/tmp/popup_02_no_modal.png", full_page=True)

        # ============================================================
        # Verifica se há steps / wizard
        # ============================================================
        wizard = await page.evaluate("""() => {
            const steps = [];
            // Bootstrap wizard/tabs
            document.querySelectorAll('.nav-tabs li, .tab-pane, .wizard-tab, .step, [role="tab"], [role="tabpanel"]').forEach(el => {
                steps.push({
                    tag: el.tagName, id: el.id || '',
                    class: el.className.substring(0,40) || '',
                    text: el.textContent.trim().substring(0, 60),
                    active: el.classList.contains('active') || el.getAttribute('aria-selected') === 'true'
                });
            });
            return steps;
        }""")
        print(f"\n{tag} WIZARD STEPS: {json.dumps(wizard[:15], indent=2)}")

        # ============================================================
        # Verifica botões de ação principais
        # ============================================================
        action_btns = await page.evaluate("""() => {
            const btns = [];
            document.querySelectorAll('button, input[type="button"], input[type="submit"], a.btn').forEach(el => {
                if (el.offsetParent !== null) {
                    btns.push({
                        tag: el.tagName,
                        id: el.id || '',
                        text: (el.textContent || el.value || '').trim().substring(0, 60),
                        onclick: (el.getAttribute('onclick') || '').substring(0, 100)
                    });
                }
            });
            return btns;
        }""")
        print(f"\n{tag} ACTION BUTTONS:")
        for btn in action_btns:
            print(f"  {btn['tag']:8} id={btn['id'][:50]:50} text={btn['text']:30} onclick={btn['onclick'][:60]}")

        await browser.close()
        print(f"\n{tag} DONE")
        print(f"Screenshots: /tmp/popup_01_initial.png, /tmp/popup_02_no_modal.png")
        print(f"HTML: /tmp/popup_page.html")


asyncio.run(main())

"""
Explora o fluxo COMPLETO de peticionamento avulso no PJe TRF1:
  1. PETICIONAR → busca processo → clica PETICIONAR
  2. Abre popup (peticaoPopUp.seam) OU process detail (listProcessoCompletoAdvogado.seam)
  3. "Juntar documentos" → formulário com Tipo, Descrição, Upload PDF
  4. Mapeia todos os "Tipo de documento" disponíveis
"""
import asyncio
import json
import sys
import uuid as uuid_mod
import re

sys.path.insert(0, "/app")

# ── Processo do Jose Iran (existe e funciona) ──
PROCESSO = {
    "sequencial": "1014980",
    "digito": "12",
    "ano": "2025",
    "ramo": "4",
    "tribunal": "01",
    "orgao": "4100",
    "completo": "1014980-12.2025.4.01.4100",
}


async def login(page, tag):
    """Full SSO + TOTP login. Returns True on success."""
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

    await page.goto(
        "https://pje1g.trf1.jus.br/pje/login.seam",
        wait_until="domcontentloaded", timeout=60_000,
    )
    await asyncio.sleep(2)

    od = await page.evaluate("""() => {
        for (const el of document.querySelectorAll('[onclick]')) {
            const m = el.getAttribute('onclick')?.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
            if (m) return {mensagem: m[2]};
        }
        return null;
    }""")
    if not od:
        print(f"{tag} ERROR: No SSO challenge"); return False

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
        print(f"{tag} ERROR: SSO failed {r}"); return False

    await page.evaluate("""([uuid]) => {
        const c = document.getElementById('pjeoffice-code'); if(c) c.value=uuid;
        const f = document.getElementById('loginForm'); if(!f)return;
        const b = document.createElement('input'); b.type='hidden'; b.name='login-pje-office'; b.value='CERTIFICADO DIGITAL';
        f.appendChild(b); f.submit();
    }""", [token_uuid])

    try:
        await page.wait_for_url(re.compile(r"(pje1g\.trf|otp|login-actions)"), timeout=30_000)
    except:
        pass
    await asyncio.sleep(2)

    otp = page.locator("input[name='otp'], input[id='otp']")
    if await otp.count() > 0:
        code = pyotp.TOTP(totp_secret).now()
        await otp.first.fill(code)
        await asyncio.sleep(0.3)
        await page.locator("input[id='kc-login']").evaluate("el => el.click()")
        try:
            await page.wait_for_url(re.compile(r"pje1g\.trf"), timeout=30_000)
        except:
            pass
        await asyncio.sleep(3)
        print(f"{tag} TOTP OK: {code}")

    ok = "pje1g.trf1" in page.url
    print(f"{tag} Login {'OK' if ok else 'FAILED'}: {page.url}")
    return ok


async def main():
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    from app.scrapers.pje_peticionamento import _extract_pem_from_pfx

    pfx_path = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    pfx_password = "22051998"
    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()
    cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)
    tag = "[JUNTAR]"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1400, "height": 900},
            client_certificates=[
                {"origin": o, "certPath": cert_path, "keyPath": key_path}
                for o in ["https://sso.cloud.pje.jus.br", "https://pje1g.trf1.jus.br"]
            ],
        )
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        if not await login(page, tag):
            await browser.close(); return

        # ── PASSO 1: PETICIONAR → busca processo ──
        print(f"\n{'='*60}")
        print(f"{tag} PASSO 1: Buscar processo na Petição Avulsa")
        await page.goto(
            "https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(3)

        proc = PROCESSO
        await page.evaluate("""(p) => {
            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) { el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); }
            };
            set('fPP:numeroProcesso:numeroSequencial', p.sequencial);
            set('fPP:numeroProcesso:numeroDigitoVerificador', p.digito);
            set('fPP:numeroProcesso:Ano', p.ano);
            set('fPP:numeroProcesso:ramoJustica', p.ramo);
            set('fPP:numeroProcesso:respectivoTribunal', p.tribunal);
            set('fPP:numeroProcesso:NumeroOrgaoJustica', p.orgao);
        }""", proc)
        await asyncio.sleep(1)

        await page.evaluate("() => document.getElementById('fPP:searchProcessosPeticao')?.click()")
        await asyncio.sleep(8)

        body = await page.inner_text("body")
        found = "resultados encontrados" in body
        print(f"{tag} Processo encontrado: {found}")
        await page.screenshot(path="/tmp/juntar_01_busca.png", full_page=True)

        if not found:
            print(f"{tag} ABORT: processo não encontrado"); await browser.close(); return

        # ── PASSO 2: Clica PETICIONAR (idPet) e captura popup URL ──
        print(f"\n{'='*60}")
        print(f"{tag} PASSO 2: Capturar URL do popup")
        # Override openPopUp() BEFORE clicking to capture the final URL
        popup_url = await page.evaluate("""() => {
            return new Promise((resolve) => {
                // PJe calls openPopUp('Peticionamento', link) after A4J response
                window.openPopUp = function(title, url) {
                    resolve(url);
                };
                // Also intercept window.open as fallback
                const origWinOpen = window.open;
                window.open = function(url, ...args) {
                    resolve(url);
                    return null;  // Don't actually open
                };
                const link = document.querySelector('a[id*="idPet"]');
                if (link) link.click();
                else resolve(null);
                setTimeout(() => resolve(null), 15000);
            });
        }""")
        print(f"{tag} Popup URL: {(popup_url or 'NONE')[:150]}")

        if not popup_url:
            print(f"{tag} ABORT: sem popup URL"); await browser.close(); return

        # ── PASSO 3: Abre popup (peticaoPopUp.seam) ──
        print(f"\n{'='*60}")
        print(f"{tag} PASSO 3: Abrir popup de peticionamento")
        await page.goto(popup_url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(5)
        await page.screenshot(path="/tmp/juntar_02_popup.png", full_page=True)
        print(f"{tag} Popup URL final: {page.url}")

        body = await page.inner_text("body")
        print(f"{tag} Body (2000):\n{body[:2000]}")

        # ── PASSO 3b: Mapear todos os elementos do popup ──
        all_els = await page.evaluate("""() => {
            const res = [];
            document.querySelectorAll('input, select, textarea, button, a[onclick], a.btn, a[id]').forEach(el => {
                res.push({
                    tag: el.tagName, id: (el.id||'').substring(0,80),
                    name: (el.name||'').substring(0,60), type: el.type||'',
                    value: (el.value||'').substring(0,50),
                    text: (el.textContent||'').trim().substring(0,60),
                    visible: el.offsetParent !== null,
                    accept: el.accept || '',
                    href: (el.href||'').substring(0,100),
                    title: (el.title||el.getAttribute('data-original-title')||'').substring(0,60),
                    onclick: (el.getAttribute('onclick')||'').substring(0,100)
                });
            });
            return res;
        }""")
        print(f"\n{tag} POPUP ELEMENTS ({len(all_els)}):")
        for el in all_els:
            v = "V" if el["visible"] else "H"
            extra = ""
            if el["title"]: extra += f" title='{el['title']}'"
            if el["href"]: extra += f" href={el['href'][:50]}"
            if el["accept"]: extra += f" accept={el['accept']}"
            print(f"  [{v}] {el['tag']:8} id={el['id'][:60]:60} type={el['type']:10} text={el['text'][:35]:35}{extra}")

        # ── PASSO 3c: SELECTs com TODAS as opções ──
        selects = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('select')).map(s => ({
                id: s.id, name: s.name||'', visible: s.offsetParent !== null,
                options: Array.from(s.options).map(o => ({v: o.value, t: o.textContent.trim()}))
            }));
        }""")
        tipo_doc_options = []
        print(f"\n{tag} SELECTS:")
        for sel in selects:
            v = "V" if sel["visible"] else "H"
            print(f"  [{v}] id={sel['id'][:70]} ({len(sel['options'])} options)")
            for opt in sel["options"]:
                print(f"     [{opt['v'][:30]}] {opt['t'][:80]}")
                # Capture tipo de documento options
                if "tipo" in sel["id"].lower() or "tipoDocumento" in sel["id"]:
                    tipo_doc_options.append(opt)

        # ── PASSO 3d: Labels ──
        labels = await page.evaluate("""() =>
            Array.from(document.querySelectorAll('label')).map(l => ({
                for: l.getAttribute('for')||'', text: l.textContent.trim().substring(0,80), visible: l.offsetParent !== null
            }))
        """)
        print(f"\n{tag} LABELS:")
        for lbl in labels:
            v = "V" if lbl["visible"] else "H"
            print(f"  [{v}] for={lbl['for'][:40]:40} → {lbl['text']}")

        # ── PASSO 3e: File inputs & dropzone ──
        files = await page.evaluate("""() => ({
            fileInputs: Array.from(document.querySelectorAll('input[type="file"]')).map(i => ({
                id: i.id, name: i.name, accept: i.accept, multiple: i.multiple, visible: i.offsetParent !== null
            })),
            dropzones: Array.from(document.querySelectorAll('.dropzone, .dz-default, [id*="ropzone"], [class*="dropzone"]')).map(d => ({
                id: d.id, class: d.className.substring(0,60), text: d.textContent.trim().substring(0,100), visible: d.offsetParent !== null
            }))
        })""")
        print(f"\n{tag} FILE/DROPZONE: {json.dumps(files, indent=2)}")

        # ── PASSO 3f: Iframes & CKEditor ──
        iframes = await page.evaluate("""() => ({
            iframes: Array.from(document.querySelectorAll('iframe')).map(f => ({
                id: f.id, src: (f.src||'').substring(0,120), visible: f.offsetParent !== null
            })),
            hasCKEditor: typeof CKEDITOR !== 'undefined',
            hasTinyMCE: typeof tinyMCE !== 'undefined'
        })""")
        print(f"\n{tag} IFRAMES/EDITORS: {json.dumps(iframes, indent=2)}")

        # ── PASSO 3g: Radio buttons (Arquivo PDF / Editor de texto) ──
        radios = await page.evaluate("""() =>
            Array.from(document.querySelectorAll('input[type="radio"]')).map(r => ({
                id: r.id, name: r.name, value: r.value, checked: r.checked,
                label: r.parentElement?.textContent?.trim().substring(0,60) || '',
                visible: r.offsetParent !== null
            }))
        """)
        print(f"\n{tag} RADIOS:")
        for r in radios:
            v = "V" if r["visible"] else "H"
            chk = "✓" if r["checked"] else " "
            print(f"  [{v}][{chk}] id={r['id'][:50]:50} name={r['name'][:30]} val={r['value'][:20]} label={r['label'][:40]}")

        # ── PASSO 3h: Action buttons ──
        btns = await page.evaluate("""() =>
            Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a.btn'))
            .filter(b => b.offsetParent !== null)
            .map(b => ({
                tag: b.tagName, id: (b.id||'').substring(0,60),
                text: (b.textContent||b.value||'').trim().substring(0,60),
                onclick: (b.getAttribute('onclick')||'').substring(0,120)
            }))
        """)
        print(f"\n{tag} ACTION BUTTONS:")
        for b in btns:
            print(f"  {b['tag']:8} id={b['id'][:50]:50} text={b['text'][:40]}")

        # ── PASSO 4: Salvar HTML completo ──
        html = await page.content()
        with open("/tmp/popup_full.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n{tag} HTML salvo: /tmp/popup_full.html ({len(html)} chars)")

        # ── PASSO 5: Fechar modal PJeOffice se existir e re-screenshot ──
        await page.evaluate("""() => {
            document.querySelectorAll('[data-dismiss="modal"], .modal .close, .rich-mpnl-controls .close').forEach(b => b.click());
            const s = document.getElementById('mpPJeOfficeIndisponivelOpenedState');
            if (s) s.value = '';
        }""")
        await asyncio.sleep(2)
        await page.screenshot(path="/tmp/juntar_03_clean.png", full_page=True)

        # ── Se nenhum select visível (pode ser a página do processo) ──
        visible_selects = [s for s in selects if s.get("visible")]
        if not visible_selects:
            print(f"\n{tag} Nenhum select visível — talvez precisa clicar 'Juntar documentos'")
            # Procurar botão/link "Juntar documentos" ou "+"
            juntar_info = await page.evaluate("""() => {
                const all = document.querySelectorAll('a, button, i, span');
                const results = [];
                for (const el of all) {
                    const text = (el.textContent||'').trim().toLowerCase();
                    const title = (el.title||el.getAttribute('data-original-title')||'').toLowerCase();
                    if (text.includes('juntar') || title.includes('juntar') ||
                        title.includes('documento') || text.includes('documento')) {
                        results.push({
                            tag: el.tagName, id: el.id||'',
                            text: el.textContent?.trim().substring(0,60),
                            title: title.substring(0,60),
                            href: (el.href||'').substring(0,100),
                            onclick: (el.getAttribute('onclick')||'').substring(0,100),
                            class: el.className?.substring(0,40) || ''
                        });
                    }
                }
                return results;
            }""")
            print(f"{tag} 'Juntar' elements found: {json.dumps(juntar_info, indent=2)}")

            if juntar_info:
                # Click the first one
                clicked = await page.evaluate("""() => {
                    const all = document.querySelectorAll('a, button');
                    for (const el of all) {
                        const title = (el.title||el.getAttribute('data-original-title')||'').toLowerCase();
                        if (title.includes('juntar')) {
                            el.click();
                            return 'clicked: ' + (el.id || el.title || el.textContent?.trim().substring(0,30));
                        }
                    }
                    return 'not found';
                }""")
                print(f"{tag} Clicked juntar: {clicked}")
                await asyncio.sleep(5)
                await page.screenshot(path="/tmp/juntar_04_form.png", full_page=True)
                print(f"{tag} URL: {page.url}")

                body2 = await page.inner_text("body")
                print(f"{tag} Body após juntar (2000):\n{body2[:2000]}")

                # Re-scan selects
                selects2 = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('select')).map(s => ({
                        id: s.id, visible: s.offsetParent !== null,
                        options: Array.from(s.options).map(o => ({v: o.value, t: o.textContent.trim()}))
                    }))
                """)
                print(f"\n{tag} SELECTS após juntar:")
                for sel in selects2:
                    v = "V" if sel["visible"] else "H"
                    print(f"  [{v}] id={sel['id'][:70]} ({len(sel['options'])} options)")
                    for opt in sel["options"]:
                        print(f"     [{opt['v'][:30]}] {opt['t'][:80]}")

                # Re-scan all visible elements
                els2 = await page.evaluate("""() => {
                    const res = [];
                    document.querySelectorAll('input, select, textarea, button').forEach(el => {
                        if (el.offsetParent !== null || el.type === 'file') {
                            res.push({
                                tag: el.tagName, id: (el.id||'').substring(0,80),
                                type: el.type||'', text: (el.textContent||el.value||'').trim().substring(0,40),
                                accept: el.accept||''
                            });
                        }
                    });
                    return res;
                }""")
                print(f"\n{tag} FORM elements após juntar ({len(els2)}):")
                for el in els2:
                    print(f"   {el['tag']:8} id={el['id'][:60]:60} type={el['type']:10} text={el['text'][:30]}")

                # Radios
                radios2 = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('input[type="radio"]'))
                    .filter(r => r.offsetParent !== null)
                    .map(r => ({id: r.id, name: r.name, value: r.value, checked: r.checked, label: r.parentElement?.textContent?.trim().substring(0,40)||''}))
                """)
                print(f"\n{tag} RADIOS após juntar:")
                for r in radios2:
                    chk = "✓" if r["checked"] else " "
                    print(f"  [{chk}] id={r['id'][:50]} val={r['value']} label={r['label']}")

                # File inputs
                files2 = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('input[type="file"]')).map(i => ({
                        id: i.id, name: i.name, accept: i.accept, visible: i.offsetParent !== null
                    }))
                """)
                print(f"\n{tag} FILE inputs: {json.dumps(files2, indent=2)}")

        # ── SALVAR JSON com tipo_documento options ──
        if tipo_doc_options:
            with open("/tmp/tipo_documento_options.json", "w") as f:
                json.dump(tipo_doc_options, f, indent=2, ensure_ascii=False)
            print(f"\n{tag} Tipo de documento salvo: /tmp/tipo_documento_options.json ({len(tipo_doc_options)} opções)")

        await browser.close()
        print(f"\n{tag} DONE ✓")


asyncio.run(main())

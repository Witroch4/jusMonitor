"""Debug script para validar 2 hipóteses do bug petição avulsa:
  H1: commandLinkAdicionar ABRE file picker (precisa expect_file_chooser)
  H2: POST signing deve ir para SSO (sso.cloud.pje.jus.br), não PJe server

Rodar dentro do container scraper:
  docker compose exec scraper python scripts/debug_peticao_avulsa.py
"""
import asyncio
import base64
import json
import logging
import os
import re
import sys
import time
import uuid as uuid_mod

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
for noisy in ["playwright", "asyncio", "urllib3", "httpx"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)
log = logging.getLogger("debug")

sys.path.insert(0, "/app")

PFX_PATH = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
PFX_PASSWORD = "22051998"
TOTP_SECRET = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"
# PDF real do processo Iran
PDF_PATH_REAL = "/app/shared-docs/chamamento JOSE IRAN DE FIGUEIREDO.pdf"
PROCESSO_NUM = "1014980-12.2025.4.01.4100"
PROCESSO = {
    "sequencial": "1014980", "digito": "12", "ano": "2025",
    "ramo": "4", "tribunal": "01", "orgao": "4100",
}
TAG = "[DEBUG]"


async def login(page, private_key, certchain_b64):
    """Login SSO + TOTP. Retorna True se OK."""
    from app.scrapers.pje_peticionamento import _sign_md5_rsa
    import pyotp

    await page.goto(
        "https://pje1g.trf1.jus.br/pje/login.seam",
        wait_until="domcontentloaded", timeout=60_000,
    )
    await asyncio.sleep(2)

    # Extract challenge
    od = await page.evaluate("""() => {
        for (const el of document.querySelectorAll('[onclick]')) {
            const m = (el.getAttribute('onclick')||'').match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
            if (m) return {mensagem: m[2]};
        }
        return null;
    }""")
    if not od:
        log.error("Challenge SSO não encontrado!")
        return False
    log.info("Challenge: %s", od["mensagem"][:30])

    token_uuid = str(uuid_mod.uuid4())
    payload = json.dumps({
        "certChain": certchain_b64, "uuid": token_uuid,
        "mensagem": od["mensagem"],
        "assinatura": _sign_md5_rsa(private_key, od["mensagem"]),
    })

    r = await page.evaluate("""async ([url, p]) => {
        try {
            const r = await fetch(url, {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:p, credentials:'include'
            });
            return {status:r.status};
        } catch(e) { return {error:e.message}; }
    }""", ["https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest", payload])

    if r.get("status") not in (200, 204):
        log.error("SSO login failed: %s", r)
        return False
    log.info("SSO pjeoffice-rest: HTTP %d", r["status"])

    await page.evaluate("""([uuid]) => {
        const c = document.getElementById('pjeoffice-code');
        if(c) c.value=uuid;
        const f = document.getElementById('loginForm');
        if(!f) return;
        const b = document.createElement('input');
        b.type='hidden'; b.name='login-pje-office'; b.value='CERTIFICADO DIGITAL';
        f.appendChild(b); f.submit();
    }""", [token_uuid])

    try:
        await page.wait_for_url(
            re.compile(r"(^https?://pje1g\.trf|login-actions)"), timeout=30_000,
        )
    except Exception:
        pass
    await asyncio.sleep(2)

    # TOTP
    otp = page.locator("input[name='otp'], input[id='otp']")
    if await otp.count() > 0:
        code = pyotp.TOTP(TOTP_SECRET).now()
        await otp.first.fill(code)
        await asyncio.sleep(0.3)
        await page.locator("input[id='kc-login']").evaluate("el => el.click()")
        try:
            await page.wait_for_url(
                re.compile(r"^https?://pje1g\.trf"), timeout=30_000,
            )
        except Exception:
            pass
        await asyncio.sleep(3)
        log.info("TOTP: %s", code)

    ok = "pje1g.trf1" in page.url
    log.info("Login %s: %s", "OK" if ok else "FALHOU", page.url)
    return ok


async def navegar_para_popup(page):
    """Navega para busca do processo e retorna popup URL."""
    log.info("Navegando para Petição Avulsa...")
    await page.goto(
        "https://pje1g.trf1.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam",
        wait_until="domcontentloaded", timeout=30_000,
    )
    await asyncio.sleep(3)

    await page.evaluate("""(p) => {
        const set = (id, val) => {
            const el = document.getElementById(id);
            if(el) { el.value=val; el.dispatchEvent(new Event('change',{bubbles:true})); }
        };
        set('fPP:numeroProcesso:numeroSequencial', p.sequencial);
        set('fPP:numeroProcesso:numeroDigitoVerificador', p.digito);
        set('fPP:numeroProcesso:Ano', p.ano);
        set('fPP:numeroProcesso:ramoJustica', p.ramo);
        set('fPP:numeroProcesso:respectivoTribunal', p.tribunal);
        set('fPP:numeroProcesso:NumeroOrgaoJustica', p.orgao);
    }""", PROCESSO)
    await asyncio.sleep(1)

    await page.evaluate(
        "() => document.getElementById('fPP:searchProcessosPeticao')?.click()"
    )
    await asyncio.sleep(8)

    body = await page.inner_text("body")
    if "resultados encontrados" not in body:
        log.error("Processo não encontrado!")
        return None

    popup_url = await page.evaluate("""() => {
        return new Promise((resolve) => {
            window.openPopUp = function(title, url) { resolve(url); };
            const link = document.querySelector('a[id*="idPet"]');
            if (link) link.click();
            else resolve(null);
            setTimeout(() => resolve(null), 15000);
        });
    }""")
    log.info("Popup URL: %s", (popup_url or "NONE")[:120])
    return popup_url


async def main():
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    from app.scrapers.pje_peticionamento import (
        _extract_pem_from_pfx, _get_certchain_b64, _sign_md5_rsa,
    )
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    from urllib.parse import parse_qs, unquote, urlparse

    with open(PFX_PATH, "rb") as f:
        pfx_bytes = f.read()
    cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, PFX_PASSWORD)
    pkcs = load_pkcs12(pfx_bytes, PFX_PASSWORD.encode())
    private_key = pkcs.key
    certchain_b64 = _get_certchain_b64(
        pkcs.cert.certificate,
        [c.certificate for c in (pkcs.additional_certs or [])],
    )

    # Usar PDF real do processo Iran
    pdf_path = PDF_PATH_REAL
    if not os.path.exists(pdf_path):
        log.error("PDF não encontrado: %s", pdf_path)
        return
    log.info("PDF real: %s (%d bytes)", pdf_path, os.path.getsize(pdf_path))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            ignore_https_errors=True,
            locale="pt-BR",
            viewport={"width": 1920, "height": 1080},
            client_certificates=[
                {"origin": o, "certPath": cert_path, "keyPath": key_path}
                for o in [
                    "https://sso.cloud.pje.jus.br",
                    "https://pje1g.trf1.jus.br",
                ]
            ],
        )
        await Stealth().apply_stealth_async(ctx)
        page = await ctx.new_page()

        # ═══ LOGIN ═══
        if not await login(page, private_key, certchain_b64):
            await browser.close()
            return

        # ═══ NAVEGAR AO PROCESSO ═══
        popup_url = await navegar_para_popup(page)
        if not popup_url:
            await browser.close()
            return

        # Abrir popup
        await page.goto(popup_url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(5)

        # Fechar modal PJeOffice se existir
        await page.evaluate("""() => {
            document.querySelectorAll(
                '[data-dismiss="modal"], .modal .close'
            ).forEach(b => b.click());
            const s = document.getElementById('mpPJeOfficeIndisponivelOpenedState');
            if(s) s.value='';
            document.querySelectorAll('.modal').forEach(m => {
                m.style.display='none'; m.classList.remove('in','show');
            });
            const bd = document.querySelector('.modal-backdrop');
            if(bd) bd.remove();
        }""")
        await asyncio.sleep(2)
        log.info("Popup aberta: %s", page.url[:100])
        await page.screenshot(path="/tmp/debug_01_popup.png", full_page=True)

        # ═══ PREENCHER FORMULÁRIO ═══
        log.info("Preenchendo formulário...")

        # 1. Tipo: Petição intercorrente / Outras peças
        tipo_select = page.locator("select[id='cbTDDecoration:cbTD']")
        if await tipo_select.count() > 0:
            try:
                await tipo_select.first.select_option(label="Petição intercorrente")
                log.info("Tipo: Petição intercorrente")
            except Exception:
                await tipo_select.first.select_option(label="Outras peças")
                log.info("Tipo: Outras peças (fallback)")
        await asyncio.sleep(3)

        # 2. Descrição
        await page.evaluate("""() => {
            const el = document.getElementById('ipDescDecoration:ipDesc');
            if (el) {
                el.value = 'chamamento JOSE IRAN DE FIGUEIREDO';
                el.dispatchEvent(new Event('change',{bubbles:true}));
            }
        }""")
        log.info("Descrição preenchida")

        # 3. Radio Arquivo PDF
        radio = page.locator("input[id='raTipoDocPrincipal:0']")
        if await radio.count() > 0:
            await radio.first.click()
            log.info("Radio 'Arquivo PDF' clicado")
        await asyncio.sleep(5)

        await page.screenshot(path="/tmp/debug_02_form_preenchido.png", full_page=True)

        # ═══════════════════════════════════════════════════════════
        # HIPÓTESE 1: commandLinkAdicionar abre file picker?
        # ═══════════════════════════════════════════════════════════
        log.info("=" * 60)
        log.info("TESTE H1: commandLinkAdicionar abre file picker?")
        log.info("=" * 60)

        # Info sobre o botão Adicionar
        adicionar_info = await page.evaluate("""() => {
            const el = document.getElementById('commandLinkAdicionar');
            if (!el) return {found: false};
            return {
                found: true, tag: el.tagName,
                onclick: (el.getAttribute('onclick') || '').substring(0, 300),
                href: (el.getAttribute('href') || '').substring(0, 200),
                text: (el.textContent||'').trim().substring(0, 50),
                outerHTML: el.outerHTML.substring(0, 500),
            };
        }""")
        log.info("commandLinkAdicionar: %s", json.dumps(adicionar_info, indent=2, ensure_ascii=False))

        # Listar file inputs ANTES
        file_inputs_before = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input[type="file"]')).map(i => ({
                id: i.id, name: i.name, accept: i.accept,
                display: getComputedStyle(i).display,
                visibility: getComputedStyle(i).visibility,
                parentHTML: i.parentElement?.outerHTML?.substring(0, 200) || ''
            }));
        }""")
        log.info("File inputs ANTES: %d", len(file_inputs_before))
        for fi in file_inputs_before:
            log.info("  id=%s name=%s accept=%s display=%s vis=%s",
                     fi["id"], fi["name"], fi["accept"], fi["display"], fi["visibility"])

        # ── TESTE A: expect_file_chooser + commandLinkAdicionar ──
        file_chooser_triggered = False
        try:
            log.info("Tentando expect_file_chooser + commandLinkAdicionar.click()...")
            async with page.expect_file_chooser(timeout=8000) as fc_info:
                await page.evaluate(
                    "() => { const el = document.getElementById('commandLinkAdicionar'); if(el) el.click(); }"
                )
            fc = await fc_info.value
            file_chooser_triggered = True
            log.info("FILE CHOOSER DISPAROU! is_multiple=%s", fc.is_multiple)
            # Selecionar nosso PDF real
            await fc.set_files(pdf_path)
            log.info("Arquivo selecionado via file_chooser: %s", pdf_path)
        except Exception as e:
            log.warning("expect_file_chooser timeout/erro: %s", e)

        await asyncio.sleep(5)
        await page.screenshot(path="/tmp/debug_03_apos_adicionar.png", full_page=True)

        if not file_chooser_triggered:
            # ── TESTE B: set_input_files no hidden input + click Adicionar ──
            log.info("File chooser NÃO disparou. Tentando set_input_files + Adicionar...")

            ajax_reqs = []

            def on_req(req):
                if req.method == "POST" and "pje" in req.url:
                    ajax_reqs.append({"url": req.url[:200], "method": req.method})

            page.on("request", on_req)

            await page.evaluate("""() => {
                document.querySelectorAll('input[type="file"]').forEach(i => {
                    i.style.display='block'; i.style.visibility='visible';
                    i.style.opacity='1';
                });
            }""")
            fi = page.locator("input[type='file']")
            if await fi.count() > 0:
                await fi.first.set_input_files(pdf_path)
                log.info("set_input_files OK, aguardando...")
                await asyncio.sleep(3)
                await page.evaluate(
                    "() => document.getElementById('commandLinkAdicionar')?.click()"
                )
                await asyncio.sleep(5)

            log.info("AJAX após set_input_files + Adicionar: %d", len(ajax_reqs))
            for r in ajax_reqs:
                log.info("  %s %s", r["method"], r["url"])
            page.remove_listener("request", on_req)
            await page.screenshot(path="/tmp/debug_04_set_input_files.png", full_page=True)

        # Verificar estado após tentativas
        doc_check = await page.evaluate("""() => {
            const body = document.body.textContent || '';
            const tables = document.querySelectorAll('table');
            let docTable = null;
            for (const t of tables) {
                const txt = t.textContent || '';
                if (txt.includes('.pdf') && !txt.includes('Selecione')) {
                    docTable = txt.trim().substring(0, 300);
                    break;
                }
            }
            const tipoSel = document.getElementById('cbTDDecoration:cbTD');
            const tipoAtual = tipoSel ? tipoSel.options[tipoSel.selectedIndex]?.text : null;
            return {
                bodyHasPdf: body.includes('.pdf'),
                bodyHasAnexo: body.toLowerCase().includes('anexo'),
                docTable: docTable,
                tipoAtual: tipoAtual,
                tipoReset: tipoAtual === '' || tipoAtual === 'Selecione',
            };
        }""")
        log.info("Estado após adicionar: %s", json.dumps(doc_check, indent=2, ensure_ascii=False))

        if doc_check.get("tipoReset"):
            log.info("Tipo resetou → A4J processou (doc provavelmente adicionado)")

        # ═══════════════════════════════════════════════════════════
        # HIPÓTESE 2: Signing endpoint — SSO vs PJe server
        # ═══════════════════════════════════════════════════════════
        log.info("=" * 60)
        log.info("TESTE H2: POST pjeoffice-rest — SSO vs PJe server")
        log.info("=" * 60)

        test_msg = "test-debug-" + str(uuid_mod.uuid4())
        test_sig = _sign_md5_rsa(private_key, test_msg)
        test_token = str(uuid_mod.uuid4())
        test_payload = json.dumps({
            "certChain": certchain_b64,
            "uuid": test_token,
            "mensagem": test_msg,
            "assinatura": test_sig,
        })

        # 2A: POST → SSO (esperado: 200/204)
        log.info("POST → SSO pjeoffice-rest...")
        sso_result = await page.evaluate("""async ([url, p]) => {
            try {
                const r = await fetch(url, {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body:p, credentials:'include'
                });
                const b = await r.text();
                return {status:r.status, body:b.substring(0,200)};
            } catch(e) { return {error:e.message}; }
        }""", ["https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest", test_payload])
        log.info("SSO pjeoffice-rest: %s", sso_result)

        # 2B: POST → PJe server (esperado: 405)
        log.info("POST → PJe server pjeoffice-rest...")
        pje_result = await page.evaluate("""async ([url, p]) => {
            try {
                const r = await fetch(url, {
                    method:'POST', headers:{'Content-Type':'application/json'},
                    body:p, credentials:'include'
                });
                const b = await r.text();
                return {status:r.status, body:b.substring(0,200)};
            } catch(e) { return {error:e.message}; }
        }""", ["https://pje1g.trf1.jus.br/pje/pjeoffice-rest", test_payload])
        log.info("PJe pjeoffice-rest: %s", pje_result)

        # ═══════════════════════════════════════════════════════════
        # TESTE 3: Analisar JS do btn-assinador + PJeOffice challenge
        # ═══════════════════════════════════════════════════════════
        log.info("=" * 60)
        log.info("TESTE 3: JS do botão Assinar + intercept route")
        log.info("=" * 60)

        btn_info = await page.evaluate("""() => {
            const btn = document.getElementById('btn-assinador');
            if (!btn) return {found: false};
            return {
                found: true, tag: btn.tagName,
                onclick: (btn.getAttribute('onclick') || '').substring(0, 500),
                text: (btn.textContent||'').trim(),
                outerHTML: btn.outerHTML.substring(0, 500),
                visible: btn.offsetParent !== null,
                disabled: btn.disabled || btn.classList.contains('disabled'),
            };
        }""")
        log.info("btn-assinador: %s", json.dumps(btn_info, indent=2, ensure_ascii=False))

        # Procurar scripts que mencionam PJeOffice/localhost:8800
        pjeoffice_js = await page.evaluate("""() => {
            const results = [];
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                const text = (s.textContent || '');
                if (text.includes('pjeOffice') || text.includes('localhost:8800') ||
                    text.includes('assinador') || text.includes('8801')) {
                    const idx = Math.max(
                        text.indexOf('pjeOffice'),
                        text.indexOf('localhost:8800'),
                        text.indexOf('assinador'),
                    );
                    results.push({
                        src: (s.src || '').substring(0, 200),
                        snippet: text.substring(Math.max(0, idx-200), idx+600).substring(0, 1000),
                    });
                }
            }
            // funções globais
            const gl = [];
            try { if (typeof assinarDocumentos === 'function') gl.push('assinarDocumentos'); } catch(e){}
            try { if (typeof pjeOffice !== 'undefined') gl.push('pjeOffice'); } catch(e){}
            try { if (typeof enviarRequisicaoAssinador !== 'undefined') gl.push('enviarRequisicaoAssinador'); } catch(e){}
            try { if (typeof verificarAssinador !== 'undefined') gl.push('verificarAssinador'); } catch(e){}
            results.push({globals: gl});
            return results;
        }""")
        log.info("PJeOffice JS:")
        for item in pjeoffice_js:
            log.info("  %s", json.dumps(item, ensure_ascii=False)[:800])

        # Se há documento adicionado, testar o fluxo de assinatura com route intercept
        # CUIDADO: NÃO vamos protocolar de verdade, apenas interceptar o challenge
        log.info("=" * 60)
        log.info("TESTE 4: Interceptar PJeOffice via page.route (NÃO protocola)")
        log.info("=" * 60)

        intercepted_requests = []

        async def _debug_route(route, request):
            req_url = request.url
            log.info("[ROUTE] Interceptado: %s", req_url[:300])
            try:
                parsed = urlparse(req_url)
                params = parse_qs(parsed.query)
                r_raw = params.get("r", [None])[0]
                if r_raw:
                    r_data = json.loads(unquote(r_raw))
                    servidor = r_data.get("servidor", "")
                    tarefa_str = r_data.get("tarefa", "{}")
                    tarefa = json.loads(tarefa_str)
                    log.info("[ROUTE] servidor=%s", servidor[:100])
                    log.info("[ROUTE] tarefaId=%s", r_data.get("tarefaId"))
                    log.info("[ROUTE] enviarPara=%s", tarefa.get("enviarPara"))
                    log.info("[ROUTE] mensagem=%s...", tarefa.get("mensagem", "")[:40])
                    log.info("[ROUTE] token=%s", tarefa.get("token", "")[:20])

                    # Montar endpoint como o código atual faz (BUG: usa servidor)
                    buggy_endpoint = servidor.rstrip("/") + tarefa.get("enviarPara", "/pjeoffice-rest")
                    correct_endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"
                    log.info("[ROUTE] Endpoint BUGGY:   %s", buggy_endpoint)
                    log.info("[ROUTE] Endpoint CORRETO: %s", correct_endpoint)

                    intercepted_requests.append({
                        "servidor": servidor,
                        "enviarPara": tarefa.get("enviarPara"),
                        "tarefaId": r_data.get("tarefaId"),
                        "buggy_endpoint": buggy_endpoint,
                        "correct_endpoint": correct_endpoint,
                    })
            except Exception as e:
                log.error("[ROUTE] Erro parse: %s", e)

            # Não assinar de verdade — apenas devolver 200 vazio
            await route.fulfill(
                status=200, body="debug-intercepted",
                headers={"Access-Control-Allow-Origin": "*", "Content-Type": "text/plain"},
            )

        await page.route("http://localhost:8800/**", _debug_route)
        await page.route("http://localhost:8801/**", _debug_route)
        await page.route("**/pjeOffice/requisicao/**", _debug_route)

        # Clicar Assinar (NÃO vai protocolar porque devolvemos resposta fake)
        if btn_info.get("found"):
            log.info("Clicando btn-assinador (NÃO vai protocolar)...")
            try:
                btn = page.locator("#btn-assinador")
                if await btn.count() > 0:
                    await btn.first.click()
                    log.info("btn-assinador clicado!")
                else:
                    await page.evaluate(
                        "() => { const b = document.getElementById('btn-assinador'); if(b) b.click(); }"
                    )
                    log.info("btn-assinador clicado via JS")
            except Exception as e:
                log.warning("Erro ao clicar assinar: %s", e)

            # Esperar interceptação
            await asyncio.sleep(8)

            log.info("Requests interceptados: %d", len(intercepted_requests))
            for req in intercepted_requests:
                log.info("  %s", json.dumps(req, ensure_ascii=False))

            # Fechar modal PJeOffice Indisponível se apareceu
            await page.evaluate("""() => {
                document.querySelectorAll(
                    '[data-dismiss="modal"], .modal .close, .modal button'
                ).forEach(b => b.click());
            }""")
        else:
            log.warning("btn-assinador NÃO encontrado — doc pode não ter sido adicionado")

        await page.screenshot(path="/tmp/debug_05_final.png", full_page=True)

        # ═══ RESUMO ═══
        log.info("=" * 60)
        log.info("RESUMO DOS TESTES")
        log.info("=" * 60)
        log.info(
            "H1 - File chooser no commandLinkAdicionar: %s",
            "SIM" if file_chooser_triggered else "NÃO",
        )
        log.info("H2 - SSO endpoint:  %s", sso_result)
        log.info("H2 - PJe endpoint:  %s", pje_result)
        log.info("Requests PJeOffice interceptados: %d", len(intercepted_requests))
        if intercepted_requests:
            log.info(
                "  BUGGY endpoint:  %s", intercepted_requests[0].get("buggy_endpoint")
            )
            log.info(
                "  CORRETO endpoint: %s", intercepted_requests[0].get("correct_endpoint")
            )
        log.info("Screenshots em /tmp/debug_*.png")

        await browser.close()

    # Cleanup
    from app.scrapers.pje_peticionamento import _cleanup_pem_files
    _cleanup_pem_files(cert_path, key_path)
    log.info("DONE")


asyncio.run(main())

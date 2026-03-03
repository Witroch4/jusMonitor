"""Teste de login no PJe TRF1 via Playwright com certificado A1.

Executa dentro do container scraper:
  docker compose exec scraper python3 scripts/testar_login_pje.py

Passos:
  1. Carrega PFX e extrai PEM (cert + key)
  2. Lança Chromium com client_certificates (mTLS)
  3. Navega para PJe login
  4. Clica "CERTIFICADO DIGITAL"
  5. Verifica se logou
  6. Navega até o processo
  7. Verifica opções disponíveis (juntar petição etc.)
  8. Screenshots em cada etapa
"""

import asyncio
import base64
import os
import sys
import tempfile
import time
import re

# ── Config ──
PFX_PATH = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
PFX_PASSWORD = "22051998"
PROCESSO = "1000654-37.2026.4.01.3704"
LOGIN_URL = "https://pje1g.trf1.jus.br/pje/login.seam"
BASE_URL = "https://pje1g.trf1.jus.br/pje"
SSO_ORIGINS = [
    "https://sso.cloud.pje.jus.br",
    "https://pje1g.trf1.jus.br",
]
SCREENSHOT_DIR = "/tmp/pje_test"


async def main():
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat,
    )
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    from playwright.async_api import async_playwright

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    step = 0

    def log(msg):
        nonlocal step
        step += 1
        print(f"\n{'='*60}")
        print(f"  STEP {step}: {msg}")
        print(f"{'='*60}")

    async def shot(page, name):
        path = f"{SCREENSHOT_DIR}/{step:02d}_{name}_{int(time.time())}.png"
        try:
            await page.screenshot(path=path, full_page=True)
            print(f"  📸 Screenshot: {path}")
            return path
        except Exception as e:
            print(f"  ⚠️  Screenshot falhou: {e}")
            return None

    # ── Step 1: Load PFX ──
    log("Carregando certificado PFX")
    if not os.path.exists(PFX_PATH):
        print(f"  ❌ PFX não encontrado: {PFX_PATH}")
        sys.exit(1)

    with open(PFX_PATH, "rb") as f:
        pfx_bytes = f.read()
    print(f"  PFX carregado: {len(pfx_bytes)} bytes")

    # ── Step 2: Extract PEM ──
    log("Extraindo PEM do PFX")
    pkcs = load_pkcs12(pfx_bytes, PFX_PASSWORD.encode())

    cert_pem = pkcs.cert.certificate.public_bytes(Encoding.PEM)
    key_pem = pkcs.key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

    chain_pem = b""
    if pkcs.additional_certs:
        for extra in pkcs.additional_certs:
            chain_pem += extra.certificate.public_bytes(Encoding.PEM)
        print(f"  Cadeia: {len(pkcs.additional_certs)} certificados adicionais")

    # Info do certificado
    cert_obj = pkcs.cert.certificate
    subject = cert_obj.subject.rfc4514_string()
    not_after = cert_obj.not_valid_after_utc
    print(f"  Subject: {subject}")
    print(f"  Válido até: {not_after}")

    # Salvar PEM temp
    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem", prefix="test_cert_")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem", prefix="test_key_")
    os.write(cert_fd, cert_pem + chain_pem)
    os.close(cert_fd)
    os.write(key_fd, key_pem)
    os.close(key_fd)
    print(f"  cert_path: {cert_path}")
    print(f"  key_path: {key_path}")

    # ── Step 3: Launch browser ──
    log("Iniciando Playwright + Chromium")
    pw = await async_playwright().start()

    browser = await pw.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--single-process",
        ],
    )
    print("  Browser lançado (headless)")

    client_certs = [
        {"origin": origin, "certPath": cert_path, "keyPath": key_path}
        for origin in SSO_ORIGINS
    ]
    print(f"  mTLS origins: {[c['origin'] for c in client_certs]}")

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        accept_downloads=True,
        client_certificates=client_certs,
    )

    # Stealth (se disponível)
    try:
        from playwright_stealth import Stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        print("  Stealth aplicado")
    except ImportError:
        print("  Stealth não disponível (OK)")

    page = await context.new_page()

    # Console listener
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

    # Request listener para debug de mTLS
    def on_request(req):
        if "sso" in req.url or "login" in req.url or "cert" in req.url.lower():
            print(f"  🌐 REQ: {req.method} {req.url[:120]}")

    def on_response(resp):
        if "sso" in resp.url or "login" in resp.url or "cert" in resp.url.lower():
            print(f"  📥 RESP: {resp.status} {resp.url[:120]}")

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        # ── Step 4: Navigate to login ──
        log(f"Navegando para login: {LOGIN_URL}")
        t0 = time.monotonic()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
        t1 = time.monotonic()
        print(f"  URL: {page.url}")
        print(f"  Title: {await page.title()}")
        print(f"  Tempo: {t1-t0:.1f}s")

        await shot(page, "login_page")
        await asyncio.sleep(2)

        # Listar elementos interativos
        elements = await page.evaluate("""() => {
            const els = [];
            document.querySelectorAll('a, button, input[type="submit"], input[type="button"]').forEach(el => {
                const text = (el.textContent || el.value || '').trim();
                if (text.length > 0 && text.length < 100) {
                    els.push({tag: el.tagName, text: text.substring(0, 80), id: el.id || '', href: (el.href || '').substring(0, 100)});
                }
            });
            return els;
        }""")
        print(f"\n  Elementos interativos ({len(elements)}):")
        for el in elements:
            print(f"    {el['tag']} | text='{el['text'][:60]}' | id='{el['id']}' | href='{el['href'][:80]}'")

        # ── Step 5: Click "CERTIFICADO DIGITAL" ──
        log("Procurando e clicando CERTIFICADO DIGITAL")

        cert_btn = None
        for selector in [
            "button:has-text('CERTIFICADO DIGITAL')",
            "a:has-text('CERTIFICADO DIGITAL')",
            "button:has-text('Certificado Digital')",
            "a:has-text('Certificado Digital')",
            "[id*='certificado']",
            "button:has-text('certificado')",
        ]:
            try:
                el = page.locator(selector)
                if await el.count() > 0:
                    cert_btn = el.first
                    print(f"  Botão encontrado: {selector} (count={await el.count()})")
                    break
            except Exception:
                continue

        if not cert_btn:
            body = await page.inner_text("body")
            print(f"  ❌ Botão não encontrado!")
            print(f"  Texto da página (500 chars): {body[:500]}")
            await shot(page, "no_cert_btn")
            return

        print("  Clicando...")
        t0 = time.monotonic()
        await cert_btn.click()

        # ── Step 6: Aguardar autenticação ──
        log("Aguardando autenticação mTLS + redirect")
        print("  Aguardando até 45s para redirect pós-login...")

        try:
            await page.wait_for_url(
                re.compile(r"(painel|Painel|principal|home|login\.seam\?cid)"),
                timeout=45_000,
            )
        except Exception as e:
            print(f"  ⚠️  Timeout/erro esperando URL: {e}")

        t1 = time.monotonic()
        print(f"  URL pós-login: {page.url}")
        print(f"  Title: {await page.title()}")
        print(f"  Tempo: {t1-t0:.1f}s")

        await shot(page, "post_login")
        await asyncio.sleep(2)

        # Verificar login
        body_text = await page.inner_text("body")
        keywords_check = ["painel", "advogado", "meus processos", "início",
                          "localizar processo", "meu painel", "amanda"]
        found_keywords = [kw for kw in keywords_check if kw in body_text.lower()]
        print(f"\n  Keywords encontradas: {found_keywords}")
        print(f"  Texto (primeiros 1500 chars):\n{body_text[:1500]}")

        is_logged_in = len(found_keywords) > 0

        if not is_logged_in:
            print("\n  ❌ LOGIN NÃO DETECTADO!")
            print(f"  Console msgs: {console_msgs[:10]}")

            # Checar se tem erro na página
            if any(kw in body_text.lower() for kw in ["erro", "falha", "inválido", "negado"]):
                print("  ⚠️  Possível erro de autenticação detectado no texto!")

            await shot(page, "login_failed")

            # Tentar ver se é página SSO
            if "sso" in page.url:
                print("\n  Parece que ficou preso no SSO. Vamos ver o HTML:")
                html = await page.content()
                print(f"  HTML (2000 chars): {html[:2000]}")

            return

        print("\n  ✅ LOGIN CONFIRMADO!")

        # ── Step 7: Explorar painel ──
        log("Explorando painel do advogado")

        # Listar menus/links disponíveis
        links = await page.evaluate("""() => {
            const els = [];
            document.querySelectorAll('a, button, [role="menuitem"]').forEach(el => {
                const text = (el.textContent || '').trim();
                if (text.length > 0 && text.length < 120) {
                    els.push({
                        tag: el.tagName,
                        text: text.substring(0, 100),
                        id: el.id || '',
                        href: (el.href || '').substring(0, 150),
                        class: (el.className || '').substring(0, 60),
                    });
                }
            });
            return els;
        }""")
        print(f"\n  Links/botões no painel ({len(links)}):")
        for lnk in links[:40]:
            print(f"    {lnk['tag']} | '{lnk['text'][:70]}' | id={lnk['id']} | href={lnk['href'][:80]}")

        await shot(page, "painel")

        # ── Step 8: Navegar até o processo ──
        log(f"Navegando até o processo {PROCESSO}")

        # Estratégia 1: Busca rápida
        search_found = False
        for sel in [
            "input[id*='pesquisaRapida']",
            "input[placeholder*='processo']",
            "input[placeholder*='Processo']",
            "input[id*='numeroProcesso']",
            "input[name*='numeroProcesso']",
        ]:
            try:
                campo = page.locator(sel)
                if await campo.count() > 0:
                    print(f"  Campo de busca encontrado: {sel}")
                    await campo.first.fill(PROCESSO)
                    await asyncio.sleep(0.5)
                    await campo.first.press("Enter")
                    print("  Enter pressionado")
                    await asyncio.sleep(4)
                    search_found = True
                    break
            except Exception as e:
                print(f"  Busca {sel}: {e}")

        if not search_found:
            # Estratégia 2: URL de pesquisa
            print("  Tentando URL de pesquisa processual...")
            search_urls = [
                f"{BASE_URL}/Processo/ConsultaProcesso/listView.seam",
                f"{BASE_URL}/ConsultaProcesso/listView.seam",
            ]
            for url in search_urls:
                try:
                    print(f"  Navegando para: {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    await asyncio.sleep(2)
                    body = await page.inner_text("body")
                    print(f"  Texto (500 chars): {body[:500]}")

                    for inp_sel in [
                        "input[id*='numeroProcesso']",
                        "input[id*='numProcesso']",
                        "input[name*='numero']",
                    ]:
                        campo = page.locator(inp_sel)
                        if await campo.count() > 0:
                            print(f"  Campo número: {inp_sel}")
                            await campo.first.fill(PROCESSO)
                            await asyncio.sleep(0.5)

                            for btn_sel in [
                                "input[value*='Pesquisar']",
                                "button:has-text('Pesquisar')",
                                "[id*='btnPesquisar']",
                            ]:
                                btn = page.locator(btn_sel)
                                if await btn.count() > 0:
                                    await btn.first.click()
                                    print(f"  Pesquisa clicada: {btn_sel}")
                                    await asyncio.sleep(4)
                                    search_found = True
                                    break
                            break
                    if search_found:
                        break
                except Exception as e:
                    print(f"  URL {url}: {e}")

        print(f"\n  URL pós-busca: {page.url}")
        body = await page.inner_text("body")
        print(f"  Texto (2000 chars): {body[:2000]}")

        await shot(page, "processo_busca")

        # Verificar se encontrou o processo
        processo_clean = PROCESSO.replace(".", "").replace("-", "")
        if PROCESSO in body or processo_clean in body:
            print(f"\n  ✅ PROCESSO ENCONTRADO!")

            # Clicar no link do processo se estiver em lista de resultados
            proc_link = page.locator(f"a:has-text('{PROCESSO}')")
            if await proc_link.count() > 0:
                print("  Clicando no link do processo...")
                await proc_link.first.click()
                await asyncio.sleep(3)
        else:
            print(f"\n  ⚠️  Processo não encontrado no texto da página")

        await shot(page, "processo_detalhe")

        # ── Step 9: Verificar opções de peticionamento ──
        log("Verificando opções de peticionamento no processo")

        body = await page.inner_text("body")
        print(f"  URL: {page.url}")
        print(f"  Texto (3000 chars): {body[:3000]}")

        # Listar todos os botões/links
        all_elements = await page.evaluate("""() => {
            const els = [];
            document.querySelectorAll('a, button, input[type="submit"], input[type="button"]').forEach(el => {
                const text = (el.textContent || el.value || '').trim();
                if (text.length > 0 && text.length < 120) {
                    els.push({
                        tag: el.tagName,
                        text: text.substring(0, 100),
                        id: el.id || '',
                        href: (el.href || '').substring(0, 150),
                    });
                }
            });
            return els;
        }""")

        print(f"\n  Elementos na página do processo ({len(all_elements)}):")
        for el in all_elements:
            # Destacar elementos relevantes para peticionamento
            highlight = ""
            lower_text = el["text"].lower()
            if any(kw in lower_text for kw in ["juntar", "petição", "peticao", "documento", "protocolar", "incluir", "assinar"]):
                highlight = " <<<< RELEVANTE"
            print(f"    {el['tag']} | '{el['text'][:70]}' | id={el['id']}{highlight}")

        await shot(page, "opcoes_peticao")

        # Verificar selects (tipos de documento etc.)
        selects = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('select').forEach(sel => {
                const options = [];
                sel.querySelectorAll('option').forEach(opt => {
                    options.push({value: opt.value, text: opt.textContent?.trim().substring(0, 80)});
                });
                result.push({id: sel.id, name: sel.name, options: options.slice(0, 20)});
            });
            return result;
        }""")
        if selects:
            print(f"\n  Selects encontrados ({len(selects)}):")
            for sel in selects:
                print(f"    id={sel['id']} name={sel['name']}")
                for opt in sel["options"]:
                    print(f"      - {opt['value']}: {opt['text']}")

        # Verificar inputs de arquivo
        file_inputs = await page.evaluate("""() => {
            const result = [];
            document.querySelectorAll('input[type="file"]').forEach(inp => {
                result.push({id: inp.id, name: inp.name, accept: inp.accept || ''});
            });
            return result;
        }""")
        if file_inputs:
            print(f"\n  Inputs de arquivo ({len(file_inputs)}):")
            for fi in file_inputs:
                print(f"    id={fi['id']} name={fi['name']} accept={fi['accept']}")

        # ── Resumo final ──
        print(f"\n\n{'='*60}")
        print("  RESUMO DO TESTE")
        print(f"{'='*60}")
        print(f"  Login: {'✅ OK' if is_logged_in else '❌ FALHOU'}")
        print(f"  Processo encontrado: {'✅' if PROCESSO in body or processo_clean in body else '❌'}")
        print(f"  Screenshots salvas em: {SCREENSHOT_DIR}/")
        print(f"  Total console msgs: {len(console_msgs)}")

        # Listar screenshots
        print(f"\n  Screenshots:")
        for f in sorted(os.listdir(SCREENSHOT_DIR)):
            fpath = os.path.join(SCREENSHOT_DIR, f)
            size = os.path.getsize(fpath)
            print(f"    {f} ({size/1024:.1f} KB)")

    finally:
        print(f"\n  Fechando browser...")
        await context.close()
        await browser.close()
        await pw.stop()

        # Cleanup PEM
        for p in [cert_path, key_path]:
            try:
                os.unlink(p)
            except Exception:
                pass

        print("  Limpeza concluída.")


if __name__ == "__main__":
    asyncio.run(main())

"""Login no PJe via mesma lógica do scraper e exporta cookies/storage."""
import asyncio
import json
import sys
import base64
import uuid as uuid_mod
import re
import time

sys.path.insert(0, "/app")


async def main():
    from app.scrapers.pje_peticionamento import (
        _extract_pem_from_pfx,
        _sign_md5_rsa,
        _get_certchain_b64,
    )
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    import pyotp

    pfx_path = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    pfx_password = "22051998"
    totp_secret = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"
    tag = "[LOGIN-EXPORT]"

    with open(pfx_path, "rb") as f:
        pfx_bytes = f.read()

    cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)

    # Load crypto objects from PFX (same as scraper)
    pkcs = load_pkcs12(pfx_bytes, pfx_password.encode())
    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]
    certchain_b64 = _get_certchain_b64(cert_obj, additional_certs)
    print(f"{tag} PKIPath certChain: {1 + len(additional_certs)} certs, {len(certchain_b64)} chars b64")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            client_certificates=[
                {"origin": origin, "certPath": cert_path, "keyPath": key_path}
                for origin in ["https://sso.cloud.pje.jus.br", "https://pje1g.trf1.jus.br"]
            ],
        )
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        # Step 1: Navigate to login
        login_url = "https://pje1g.trf1.jus.br/pje/login.seam"
        await page.goto(login_url, wait_until="domcontentloaded", timeout=60_000)
        await asyncio.sleep(2)
        print(f"{tag} 1. Login page: {page.url}")

        # Step 2: Extract challenge from CERTIFICADO DIGITAL button onclick
        onclick_data = await page.evaluate("""() => {
            const btn = document.getElementById('kc-pje-office');
            if (btn) {
                const oc = btn.getAttribute('onclick') || '';
                const m = oc.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
                if (m) return {codigoSeguranca: m[1], mensagem: m[2]};
            }
            // Fallback: any element with autenticar() in onclick
            const allElems = document.querySelectorAll('[onclick]');
            for (const el of allElems) {
                const oc = el.getAttribute('onclick') || '';
                const m = oc.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
                if (m) return {codigoSeguranca: m[1], mensagem: m[2]};
            }
            return null;
        }""")

        if not onclick_data:
            body_text = await page.inner_text("body")
            print(f"{tag} ERROR: Challenge not found! Page text: {body_text[:500]}")
            await page.screenshot(path="/tmp/pje_debug.png")
            await browser.close()
            return

        mensagem_sso = onclick_data["mensagem"]
        print(f"{tag} 2. Nonce: {mensagem_sso[:40]}...")

        form_action = await page.evaluate("""() => {
            const form = document.getElementById('loginForm');
            return form ? form.action : null;
        }""")
        print(f"{tag} 2. Form action: {(form_action or '')[:100]}")

        # Step 3: Sign with MD5withRSA + POST to pjeoffice-rest (via browser fetch)
        token_uuid = str(uuid_mod.uuid4())
        assinatura_b64 = _sign_md5_rsa(private_key, mensagem_sso)

        pjeoffice_endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"
        sso_payload = json.dumps({
            "certChain": certchain_b64,
            "uuid": token_uuid,
            "mensagem": mensagem_sso,
            "assinatura": assinatura_b64,
        })

        rest_result = await page.evaluate(
            """async ([url, payloadStr]) => {
                try {
                    const resp = await fetch(url, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: payloadStr,
                        credentials: 'include',
                    });
                    const body = await resp.text();
                    return {status: resp.status, body: body.substring(0, 500)};
                } catch (e) {
                    return {error: e.message};
                }
            }""",
            [pjeoffice_endpoint, sso_payload],
        )

        if "error" in rest_result:
            print(f"{tag} ERROR pjeoffice-rest: {rest_result['error']}")
            await browser.close()
            return

        rest_status = rest_result.get("status", 0)
        print(f"{tag} 3. pjeoffice-rest: HTTP {rest_status} | {rest_result.get('body', '')[:100]}")

        if rest_status not in (200, 204):
            print(f"{tag} ERROR: pjeoffice-rest failed!")
            await browser.close()
            return

        # Step 4: Submit loginForm with uuid + login-pje-office field
        await page.evaluate(
            """([uuid]) => {
                const code = document.getElementById('pjeoffice-code');
                if (code) code.value = uuid;

                const form = document.getElementById('loginForm');
                if (!form) return;
                const btnField = document.createElement('input');
                btnField.type = 'hidden';
                btnField.name = 'login-pje-office';
                btnField.value = 'CERTIFICADO DIGITAL';
                form.appendChild(btnField);

                form.submit();
            }""",
            [token_uuid],
        )

        print(f"{tag} 4. Form submitted, waiting for redirect...")
        try:
            await page.wait_for_url(
                re.compile(r"(painel|Painel|principal|home|pje1g\.trf|otp|login-actions)"),
                timeout=30_000,
            )
        except Exception:
            pass

        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except Exception:
            pass
        await asyncio.sleep(2)
        print(f"{tag} 4. Post-submit URL: {page.url}")

        # Step 5: Handle TOTP if needed
        otp_input = page.locator("input[name='otp'], input[id='otp']")
        if await otp_input.count() > 0:
            code = pyotp.TOTP(totp_secret.strip().upper()).now()
            print(f"{tag} 5. TOTP page detected, entering code: {code}")
            await otp_input.first.fill(code)
            await asyncio.sleep(0.3)

            submit_btn = page.locator("input[name='login'], input[id='kc-login'], button[type='submit']")
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
            else:
                await otp_input.first.press("Enter")

            try:
                await page.wait_for_url(
                    re.compile(r"(painel|Painel|principal|home|pje1g\.trf)"),
                    timeout=20_000,
                )
            except Exception:
                pass
            await asyncio.sleep(2)
            print(f"{tag} 5. Post-TOTP URL: {page.url}")
        else:
            print(f"{tag} 5. No TOTP required")

        # Step 6: Save session data
        print(f"{tag} 6. Final URL: {page.url}")
        await page.screenshot(path="/tmp/pje_logged_in.png", full_page=True)
        await context.storage_state(path="/tmp/pje_storage.json")
        cookies = await context.cookies()
        with open("/tmp/pje_cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"{tag} 6. Saved {len(cookies)} cookies + storage state")

        # Step 7: Navigate to painel
        await page.goto(
            "https://pje1g.trf1.jus.br/pje/Painel/painel_usuario/advogado.seam",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/pje_painel.png", full_page=True)
        print(f"{tag} 7. Painel URL: {page.url}")

        # Step 8: Try searching for process
        numero = "1000654-37.2026.4.01.3704"
        pesquisa = page.locator("input[id*='pesquisaRapida']")
        if await pesquisa.count() > 0:
            await pesquisa.first.fill(numero)
            await pesquisa.first.press("Enter")
            await asyncio.sleep(5)
            await page.screenshot(path="/tmp/pje_busca_resultado.png", full_page=True)
            print(f"{tag} 8. Search result URL: {page.url}")
        else:
            print(f"{tag} 8. No quick search field found")
            body = await page.inner_text("body")
            print(f"{tag} 8. Page text (500 chars): {body[:500]}")

        # Step 9: Try direct URL to process
        direct_url = "https://pje1g.trf1.jus.br/pje/Processo/ConsultaProcesso/Detalhe/listProcessoCompletoAdvogado.seam?ca=10006543720264013704"
        await page.goto(direct_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/pje_direct_process.png", full_page=True)
        print(f"{tag} 9. Direct process URL: {page.url}")
        body = await page.inner_text("body")
        print(f"{tag} 9. Page text (500 chars): {body[:500]}")

        # Step 10: Try consultation page
        consulta_url = "https://pje1g.trf1.jus.br/pje/Processo/ConsultaProcesso/listView.seam"
        await page.goto(consulta_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.screenshot(path="/tmp/pje_consulta.png", full_page=True)
        print(f"{tag} 10. Consulta URL: {page.url}")

        await browser.close()
        print(f"{tag} DONE - screenshots in /tmp/pje_*.png")


asyncio.run(main())

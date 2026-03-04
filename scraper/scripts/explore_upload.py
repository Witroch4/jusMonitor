"""Explore the Dropzone upload mechanism in PJe's petition form.

Goals:
1. Check all file inputs and their parent containers
2. Intercept AJAX requests when tipo de documento is changed
3. Inspect Dropzone configuration
4. Try upload and intercept the upload request
"""

import asyncio
import base64
import json
import logging
import os
import sys
import time

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
for noisy in ["playwright", "asyncio", "urllib3", "httpx"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("explore_upload")

PFX_PATH = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
PFX_PASSWORD = "22051998"
TOTP_SECRET = "MNFTCT2WKBJFKU3NGN2GYNKUJVDVKM3X"
PROCESSO = "1000654-37.2026.4.01.3704"


def _make_test_pdf() -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 750, "TESTE AUTOMATIZADO DE PETICIONAMENTO")
    c.drawString(72, 730, "Este documento e um teste.")
    c.save()
    return buf.getvalue()


async def main():
    from app.scrapers.pje_peticionamento import protocolar_peticao_pje, _parse_numero_processo

    # We'll reuse the login + navigation but stop before signing
    # Instead, let's use Playwright directly for exploration

    with open(PFX_PATH, "rb") as f:
        pfx_bytes = f.read()

    from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
    private_key, cert, chain = pkcs12.load_key_and_certificates(pfx_bytes, PFX_PASSWORD.encode())

    # Export cert and key as PEM for mTLS
    import tempfile
    cert_pem = cert.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())

    # Write temp files
    cert_f = tempfile.NamedTemporaryFile(delete=False, suffix=".pem", prefix="cert_")
    cert_f.write(cert_pem)
    if chain:
        for c in chain:
            cert_f.write(c.public_bytes(Encoding.PEM))
    cert_f.close()

    key_f = tempfile.NamedTemporaryFile(delete=False, suffix=".pem", prefix="key_")
    key_f.write(key_pem)
    key_f.close()

    # Build PKIPath certChain for SSO
    all_certs = [cert] + list(chain or [])
    from cryptography.hazmat.primitives.serialization import Encoding as CEnc
    der_list = [c.public_bytes(CEnc.DER) for c in all_certs]
    import struct
    # PKIPath: ASN.1 SEQUENCE OF Certificate
    inner = b"".join(der_list)
    if len(inner) < 128:
        seq = b"\x30" + bytes([len(inner)]) + inner
    elif len(inner) < 256:
        seq = b"\x30\x81" + bytes([len(inner)]) + inner
    else:
        l = len(inner)
        seq = b"\x30\x82" + struct.pack(">H", l) + inner
    certchain_b64 = base64.b64encode(seq).decode()

    from playwright.async_api import async_playwright
from playwright_stealth import stealth as stealth_sync

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            ignore_https_errors=True,
            client_certificates=[
                {
                    "origin": "https://sso.cloud.pje.jus.br",
                    "certPath": cert_f.name,
                    "keyPath": key_f.name,
                },
                {
                    "origin": "https://pje1g.trf1.jus.br",
                    "certPath": cert_f.name,
                    "keyPath": key_f.name,
                },
            ],
        )
        page = await ctx.new_page()
        await stealth_async(page)

        # ═══ LOGIN ═══
        logger.info("Navigating to login...")
        await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)

        # Extract challenge
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
            logger.error("No challenge found!")
            return

        logger.info("Challenge: %s", onclick_data["mensagem"])

        # Sign with MD5withRSA
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        sig = private_key.sign(
            onclick_data["mensagem"].encode(),
            padding.PKCS1v15(),
            hashes.MD5(),
        )
        sig_b64 = base64.b64encode(sig).decode()

        import uuid
        token_uuid = str(uuid.uuid4())
        pjeoffice_endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"
        payload = json.dumps({
            "certChain": certchain_b64,
            "uuid": token_uuid,
            "mensagem": onclick_data["mensagem"],
            "assinatura": sig_b64,
        })

        result = await page.evaluate("""async ([url, payloadStr]) => {
            try {
                const resp = await fetch(url, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: payloadStr, credentials: 'include',
                });
                return {status: resp.status};
            } catch (e) { return {error: e.message}; }
        }""", [pjeoffice_endpoint, payload])

        logger.info("pjeoffice-rest: %s", result)

        if result.get("status") not in (200, 204):
            logger.error("SSO signing failed!")
            return

        # Submit form
        form_action = await page.evaluate("""() => {
            const f = document.getElementById('loginForm');
            return f ? f.action : null;
        }""")
        logger.info("Form action: %s", form_action)

        await page.evaluate("""([uuid]) => {
            const c = document.getElementById('pjeoffice-code');
            if (c) c.value = uuid;
            const f = document.getElementById('loginForm');
            if (!f) return;
            const b = document.createElement('input');
            b.type = 'hidden'; b.name = 'login-pje-office'; b.value = 'CERTIFICADO DIGITAL';
            f.appendChild(b);
            f.submit();
        }""", [token_uuid])

        import re
        try:
            await page.wait_for_url(
                re.compile(r"(^https?://pje1g\.trf|login-actions)"),
                timeout=30000,
            )
        except Exception:
            pass
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await asyncio.sleep(2)

        # TOTP
        otp_input = page.locator("input[name='otp'], input[id='otp']")
        if await otp_input.count() > 0:
            logger.info("TOTP page detected")
            import pyotp
            totp = pyotp.TOTP(TOTP_SECRET, digest="sha1", digits=6, interval=30)
            code = totp.now()
            logger.info("TOTP code: %s", code)
            await otp_input.first.fill(code)
            await asyncio.sleep(0.3)
            submit_btn = page.locator("input[id='kc-login']")
            if await submit_btn.count() > 0:
                await submit_btn.first.evaluate("el => el.click()")
            try:
                await page.wait_for_url(re.compile(r"(^https?://pje1g\.trf)"), timeout=30000)
            except Exception:
                pass
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(2)

        logger.info("Post-login URL: %s", page.url)
        body = await page.inner_text("body")
        if "peticionar" not in body.lower() and "expedientes" not in body.lower():
            logger.error("Login failed! Body: %s", body[:500])
            return

        logger.info("✅ LOGIN OK!")

        # ═══ NAVIGATE TO PETITION POPUP ═══
        logger.info("Navigating to Petição Avulsa...")
        await page.goto(
            "https://pje1g.trf1.jus.br/pje/Processo/peticaoavulsa.seam",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await asyncio.sleep(3)

        # Parse process number
        parts = _parse_numero_processo(PROCESSO)
        logger.info("Process parts: %s", parts)

        # Fill the process number fields
        field_map = {
            "fPP:numeroProcesso:NumeroOrgaoJustica": parts["orgao"],
            "fPP:numeroProcesso:NumeroSequencial": parts["numero"],
            "fPP:numeroProcesso:NumeroDigitoVerificador": parts["digito"],
            "fPP:numeroProcesso:NumeroAno": parts["ano"],
            "fPP:numeroProcesso:NumeroSegmento": parts["justica"],
            "fPP:numeroProcesso:NumeroTR": parts["tribunal"],
            "fPP:numeroProcesso:NumeroOrigem": parts["origem"],
        }
        for field_id, value in field_map.items():
            await page.evaluate(f"""() => {{
                const el = document.getElementById('{field_id}');
                if (el) {{ el.value = '{value}'; el.dispatchEvent(new Event('input', {{bubbles:true}})); }}
            }}""")

        # Click search
        await page.evaluate("""() => {
            const btn = document.getElementById('fPP:searchProcessos');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(5)

        # Get popup URL from openPopUp
        popup_url = await page.evaluate("""() => {
            const orig = window.openPopUp;
            return new Promise((resolve) => {
                window.openPopUp = function(url) { resolve(url); };
                // Click the process link
                const links = document.querySelectorAll('a[onclick*="openPopUp"]');
                if (links.length > 0) links[0].click();
                else resolve(null);
            });
        }""")

        if not popup_url:
            logger.error("No popup URL found!")
            body = await page.inner_text("body")
            logger.info("Body: %s", body[:2000])
            return

        logger.info("Popup URL: %s", popup_url)
        full_url = "https://pje1g.trf1.jus.br" + popup_url if popup_url.startswith("/") else popup_url

        # Navigate to popup
        await page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        # Dismiss PJeOffice modal
        await page.evaluate("""() => {
            const modals = document.querySelectorAll('.modal, [id*="modal"], [class*="modal"]');
            modals.forEach(m => {
                const close = m.querySelector('.close, [data-dismiss="modal"], button');
                if (close) close.click();
            });
        }""")
        await asyncio.sleep(1)

        logger.info("Popup loaded: %s", page.url)

        # ═══ INVESTIGATION: Form structure ═══
        logger.info("=" * 60)
        logger.info("INVESTIGATING FORM STRUCTURE")
        logger.info("=" * 60)

        # 1. Check all file inputs
        file_inputs = await page.evaluate("""() => {
            const inputs = document.querySelectorAll('input[type="file"]');
            return Array.from(inputs).map((inp, i) => ({
                index: i,
                id: inp.id,
                name: inp.name,
                className: inp.className,
                parentId: inp.parentElement?.id || null,
                parentClass: inp.parentElement?.className || null,
                grandparentId: inp.parentElement?.parentElement?.id || null,
                grandparentClass: inp.parentElement?.parentElement?.className || null,
                accept: inp.accept,
                display: getComputedStyle(inp).display,
                visibility: getComputedStyle(inp).visibility,
            }));
        }""")
        logger.info("File inputs found: %d", len(file_inputs))
        for fi in file_inputs:
            logger.info("  [%d] id=%s name=%s parent=%s/%s grandparent=%s/%s accept=%s visible=%s/%s",
                        fi["index"], fi["id"], fi["name"],
                        fi["parentId"], fi["parentClass"],
                        fi["grandparentId"], fi["grandparentClass"],
                        fi["accept"], fi["display"], fi["visibility"])

        # 2. Check Dropzone instances
        dz_info = await page.evaluate("""() => {
            const results = [];
            // Check Dropzone global instances
            if (typeof Dropzone !== 'undefined') {
                results.push({global: true, instances: Dropzone.instances?.length || 0});
                if (Dropzone.instances) {
                    Dropzone.instances.forEach((dz, i) => {
                        results.push({
                            instance: i,
                            elementId: dz.element?.id || null,
                            elementClass: dz.element?.className || null,
                            url: dz.options?.url || null,
                            paramName: dz.options?.paramName || null,
                            autoProcessQueue: dz.options?.autoProcessQueue,
                            acceptedFiles: dz.options?.acceptedFiles || null,
                            params: JSON.stringify(dz.options?.params || {}),
                            headers: JSON.stringify(dz.options?.headers || {}),
                        });
                    });
                }
            } else {
                results.push({global: false, msg: 'Dropzone not found globally'});
            }
            // Check elements with dz- classes
            const dzElems = document.querySelectorAll('[class*="dz-"], .dropzone, [id*="dropzone"]');
            if (dzElems.length > 0) {
                results.push({dzElements: dzElems.length});
                Array.from(dzElems).slice(0, 5).forEach(el => {
                    results.push({
                        tag: el.tagName,
                        id: el.id,
                        className: el.className.substring(0, 100),
                    });
                });
            }
            return results;
        }""")
        logger.info("Dropzone info:")
        for item in dz_info:
            logger.info("  %s", json.dumps(item, default=str))

        # 3. Check the tipo select element and its A4J configuration
        tipo_info = await page.evaluate("""() => {
            const sel = document.getElementById('cbTDDecoration:cbTD');
            if (!sel) return {found: false};
            return {
                found: true,
                id: sel.id,
                name: sel.name,
                onchange: sel.getAttribute('onchange'),
                hasEventListeners: typeof sel._events !== 'undefined' || null,
                optionCount: sel.options.length,
                currentValue: sel.value,
                currentLabel: sel.options[sel.selectedIndex]?.text || null,
                parentFormId: sel.closest('form')?.id || null,
                // Check if there's an a4j:support handler
                a4jHandlerInOnchange: sel.getAttribute('onchange')?.includes('A4J') || false,
                a4jHandlerInChangeListener: sel.getAttribute('onchange')?.includes('RichFaces') || false,
            };
        }""")
        logger.info("Tipo select info: %s", json.dumps(tipo_info, default=str))

        # 4. Check what happens in RichFaces/A4J when clicking the radio
        radio_info = await page.evaluate("""() => {
            const r0 = document.getElementById('raTipoDocPrincipal:0');
            const r1 = document.getElementById('raTipoDocPrincipal:1');
            return {
                r0_found: !!r0,
                r0_checked: r0?.checked,
                r0_onchange: r0?.getAttribute('onchange'),
                r0_onclick: r0?.getAttribute('onclick'),
                r1_found: !!r1,
                r1_checked: r1?.checked,
                r1_onchange: r1?.getAttribute('onchange'),
                r1_onclick: r1?.getAttribute('onclick'),
            };
        }""")
        logger.info("Radio info: %s", json.dumps(radio_info, default=str))

        # 5. Check all A4J forms and hidden fields in the form
        form_info = await page.evaluate("""() => {
            const forms = document.querySelectorAll('form');
            return Array.from(forms).map(f => ({
                id: f.id,
                action: f.action,
                method: f.method,
                hiddenFields: Array.from(f.querySelectorAll('input[type="hidden"]')).map(h => ({
                    name: h.name,
                    value: h.value?.substring(0, 100),
                })),
            }));
        }""")
        logger.info("Forms found: %d", len(form_info))
        for fi in form_info:
            logger.info("  Form id=%s action=%s hiddens=%d", fi["id"], fi["action"][:100] if fi["action"] else None, len(fi["hiddenFields"]))
            for h in fi["hiddenFields"][:10]:
                logger.info("    hidden: %s = %s", h["name"], h["value"])

        # ═══ INVESTIGATION: Type selection with request interception ═══
        logger.info("=" * 60)
        logger.info("TESTING TIPO SELECTION WITH REQUEST INTERCEPTION")
        logger.info("=" * 60)

        # Set up request listener
        ajax_requests = []

        def on_request(req):
            if "pje" in req.url and (req.method == "POST" or "a4j" in req.url.lower()):
                ajax_requests.append({
                    "url": req.url[:200],
                    "method": req.method,
                    "post_data": req.post_data[:500] if req.post_data else None,
                    "content_type": req.headers.get("content-type", ""),
                })

        page.on("request", on_request)

        # Now select tipo
        logger.info("Selecting tipo 'Petição intercorrente' via select_option...")
        tipo_select = page.locator("select[id='cbTDDecoration:cbTD']")
        try:
            await tipo_select.first.select_option(label="Petição intercorrente")
            logger.info("select_option() done!")
        except Exception as e:
            logger.error("select_option failed: %s", e)

        # Wait for any AJAX
        await asyncio.sleep(5)

        logger.info("AJAX requests after tipo selection: %d", len(ajax_requests))
        for req in ajax_requests:
            logger.info("  %s %s", req["method"], req["url"])
            if req["post_data"]:
                logger.info("    post_data: %s", req["post_data"][:300])

        # Check if tipo was registered server-side
        tipo_after = await page.evaluate("""() => {
            const sel = document.getElementById('cbTDDecoration:cbTD');
            return sel ? {value: sel.value, label: sel.options[sel.selectedIndex]?.text} : null;
        }""")
        logger.info("Tipo after select_option: %s", tipo_after)

        # If no AJAX fired, try manual trigger
        if len(ajax_requests) == 0:
            logger.warning("No AJAX request fired! Trying manual A4J trigger...")

            # Check for onchange attribute
            onchange = await page.evaluate("""() => {
                const sel = document.getElementById('cbTDDecoration:cbTD');
                return sel?.getAttribute('onchange') || null;
            }""")
            logger.info("onchange attribute: %s", onchange)

            if onchange:
                # Execute the onchange handler
                await page.evaluate("""() => {
                    const sel = document.getElementById('cbTDDecoration:cbTD');
                    if (sel && sel.onchange) {
                        sel.onchange(new Event('change', {bubbles: true}));
                    }
                }""")
                await asyncio.sleep(3)
                logger.info("AJAX requests after manual onchange: %d", len(ajax_requests))
                for req in ajax_requests:
                    logger.info("  %s %s", req["method"], req["url"])

        # ═══ INVESTIGATION: Radio click ═══
        logger.info("=" * 60)
        logger.info("TESTING RADIO CLICK WITH REQUEST INTERCEPTION")
        logger.info("=" * 60)

        ajax_requests.clear()

        radio = page.locator("input[id='raTipoDocPrincipal:0']")
        if await radio.count() > 0:
            logger.info("Clicking radio 'Arquivo PDF'...")
            await radio.first.click()
            await asyncio.sleep(5)

            logger.info("AJAX requests after radio click: %d", len(ajax_requests))
            for req in ajax_requests:
                logger.info("  %s %s", req["method"], req["url"])
                if req["post_data"]:
                    logger.info("    post_data: %s", req["post_data"][:300])

        # ═══ INVESTIGATION: File upload ═══
        logger.info("=" * 60)
        logger.info("TESTING FILE UPLOAD WITH REQUEST INTERCEPTION")
        logger.info("=" * 60)

        ajax_requests.clear()

        # Check file inputs again after radio click
        file_inputs_after = await page.evaluate("""() => {
            const inputs = document.querySelectorAll('input[type="file"]');
            return Array.from(inputs).map((inp, i) => ({
                index: i,
                id: inp.id,
                name: inp.name,
                parentId: inp.parentElement?.id || null,
                parentClass: inp.parentElement?.className?.substring(0, 100) || null,
                display: getComputedStyle(inp).display,
            }));
        }""")
        logger.info("File inputs after radio: %d", len(file_inputs_after))
        for fi in file_inputs_after:
            logger.info("  [%d] id=%s name=%s parent=%s/%s display=%s",
                        fi["index"], fi["id"], fi["name"],
                        fi["parentId"], fi["parentClass"], fi["display"])

        # Make file visible and upload
        await page.evaluate("""() => {
            document.querySelectorAll('input[type="file"]').forEach(i => {
                i.style.display = 'block';
                i.style.visibility = 'visible';
                i.style.opacity = '1';
                i.style.position = 'relative';
            });
        }""")

        # Create test PDF
        pdf_bytes = _make_test_pdf()
        pdf_path = "/tmp/explore_test.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        logger.info("Test PDF: %d bytes at %s", len(pdf_bytes), pdf_path)

        # Upload to FIRST file input
        file_input = page.locator("input[type='file']")
        count = await file_input.count()
        logger.info("Uploading to first of %d file inputs...", count)

        await file_input.first.set_input_files(pdf_path)
        await asyncio.sleep(5)

        logger.info("AJAX requests after upload: %d", len(ajax_requests))
        for req in ajax_requests:
            logger.info("  %s %s content-type=%s", req["method"], req["url"], req["content_type"][:100])
            if req["post_data"] and "multipart" not in req["content_type"].lower():
                logger.info("    post_data: %s", req["post_data"][:500])

        # Check page for errors
        page_text = await page.inner_text("body")
        if "erro" in page_text.lower() or "error" in page_text.lower():
            # Find the error
            for line in page_text.split("\n"):
                line = line.strip()
                if ("erro" in line.lower() or "error" in line.lower()) and len(line) < 200:
                    logger.warning("Error in page: %s", line)

        # Check Dropzone state after upload
        dz_state = await page.evaluate("""() => {
            if (typeof Dropzone === 'undefined') return {dropzone: false};
            const res = {dropzone: true, instances: []};
            if (Dropzone.instances) {
                Dropzone.instances.forEach((dz, i) => {
                    res.instances.push({
                        i: i,
                        files: dz.files?.length || 0,
                        fileDetails: dz.files?.map(f => ({
                            name: f.name,
                            size: f.size,
                            status: f.status,
                            accepted: f.accepted,
                        })) || [],
                        uploadUrl: dz.options?.url || null,
                    });
                });
            }
            return res;
        }""")
        logger.info("Dropzone state after upload: %s", json.dumps(dz_state, default=str))

        logger.info("=" * 60)
        logger.info("EXPLORATION COMPLETE")
        logger.info("=" * 60)

        # Cleanup
        page.remove_listener("request", on_request)
        await browser.close()

    os.unlink(cert_f.name)
    os.unlink(key_f.name)
    os.unlink(pdf_path)


if __name__ == "__main__":
    asyncio.run(main())

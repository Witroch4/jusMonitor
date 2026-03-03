"""Teste completo: simular PJeOffice para login via certificado no PJe SSO.

Fluxo:
1. Navegar para login SSO do PJe
2. Extrair codigoSeguranca e mensagem do onclick do botão CERTIFICADO DIGITAL
3. Assinar mensagem com o certificado A1 (PKCS#7/CMS)
4. POSTar para /pjeoffice-rest com certChain, uuid, mensagem, assinatura
5. Submeter form com pjeoffice-code = uuid
6. Verificar se logou
"""

import asyncio
import base64
import json
import os
import re
import tempfile
import time
import uuid

async def main():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
    from cryptography.hazmat.primitives.serialization import pkcs7
    from playwright.async_api import async_playwright

    # ── Load PFX ──
    print("=" * 60)
    print("  STEP 1: Carregando certificado PFX")
    print("=" * 60)

    with open("/app/docs/Amanda Alves de Sousa_07071649316.pfx", "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, b"22051998")

    private_key = pkcs.key
    cert_obj = pkcs.cert.certificate
    additional_certs = [c.certificate for c in (pkcs.additional_certs or [])]

    print(f"  Subject: {cert_obj.subject.rfc4514_string()}")
    print(f"  Valid until: {cert_obj.not_valid_after_utc}")
    print(f"  Chain certs: {len(additional_certs)}")

    # Prepare PEM files for Playwright mTLS
    cert_pem = cert_obj.public_bytes(Encoding.PEM)
    key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain_pem = b""
    for c in additional_certs:
        chain_pem += c.public_bytes(Encoding.PEM)

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
    os.write(cert_fd, cert_pem + chain_pem); os.close(cert_fd)
    os.write(key_fd, key_pem); os.close(key_fd)

    # Prepare certChain for pjeoffice-rest (base64 DER of each cert)
    cert_chain_b64 = []
    cert_chain_b64.append(base64.b64encode(cert_obj.public_bytes(Encoding.DER)).decode("ascii"))
    for c in additional_certs:
        cert_chain_b64.append(base64.b64encode(c.public_bytes(Encoding.DER)).decode("ascii"))
    print(f"  certChain entries: {len(cert_chain_b64)}")

    # ── Launch browser ──
    print("\n" + "=" * 60)
    print("  STEP 2: Iniciando Playwright")
    print("=" * 60)

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process"],
    )

    client_certs = [
        {"origin": "https://sso.cloud.pje.jus.br", "certPath": cert_path, "keyPath": key_path},
        {"origin": "https://pje1g.trf1.jus.br", "certPath": cert_path, "keyPath": key_path},
    ]

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        locale="pt-BR", timezone_id="America/Sao_Paulo",
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        client_certificates=client_certs,
    )

    try:
        from playwright_stealth import Stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        print("  Stealth applied")
    except ImportError:
        pass

    page = await context.new_page()

    # Request/response logging
    def on_req(req):
        if any(kw in req.url for kw in ["sso", "login", "pjeoffice"]):
            print(f"  >> REQ: {req.method} {req.url[:120]}")
    def on_resp(resp):
        if any(kw in resp.url for kw in ["sso", "login", "pjeoffice"]):
            print(f"  << RESP: {resp.status} {resp.url[:120]}")
    page.on("request", on_req)
    page.on("response", on_resp)

    # ── Navigate to login ──
    print("\n" + "=" * 60)
    print("  STEP 3: Navegando para login PJe TRF1")
    print("=" * 60)

    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
    print(f"  URL: {page.url}")
    await asyncio.sleep(2)

    # ── Extract codigoSeguranca and mensagem from button onclick ──
    print("\n" + "=" * 60)
    print("  STEP 4: Extraindo challenge do botão CERTIFICADO DIGITAL")
    print("=" * 60)

    onclick_data = await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (!btn) return null;
        const onclick = btn.getAttribute('onclick') || '';
        // Parse: autenticar('codigoSeguranca', 'mensagem');
        const match = onclick.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
        if (match) {
            return {codigoSeguranca: match[1], mensagem: match[2]};
        }
        return {raw: onclick};
    }""")

    if not onclick_data or "raw" in onclick_data:
        print(f"  ERRO: Não conseguiu extrair dados do onclick: {onclick_data}")
        return

    codigo_seguranca = onclick_data["codigoSeguranca"]
    mensagem = onclick_data["mensagem"]
    print(f"  codigoSeguranca: {codigo_seguranca[:80]}...")
    print(f"  mensagem: {mensagem}")

    # Get form action URL
    form_action = await page.evaluate("""() => {
        const form = document.getElementById('loginForm');
        return form ? form.action : null;
    }""")
    print(f"  Form action: {form_action[:150] if form_action else 'N/A'}")

    # ── Create PKCS#7/CMS signature ──
    print("\n" + "=" * 60)
    print("  STEP 5: Assinando mensagem com certificado")
    print("=" * 60)

    # The mensagem is what PJeOffice signs
    mensagem_bytes = mensagem.encode("utf-8")
    print(f"  Mensagem a assinar: {mensagem_bytes}")

    # Try different signature approaches
    # Approach 1: Raw RSA signature
    raw_signature = private_key.sign(
        mensagem_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    raw_sig_b64 = base64.b64encode(raw_signature).decode("ascii")
    print(f"  Raw RSA-SHA256 signature: {raw_sig_b64[:80]}...")

    # Approach 2: PKCS#7/CMS detached signature
    # Using cryptography's pkcs7 module
    try:
        builder = pkcs7.PKCS7SignatureBuilder().set_data(mensagem_bytes)
        builder = builder.add_signer(cert_obj, private_key, hashes.SHA256())
        for ca_cert in additional_certs:
            builder = builder.add_certificate(ca_cert)

        # Detached signature (DER format)
        cms_sig_der = builder.sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature])
        cms_sig_b64 = base64.b64encode(cms_sig_der).decode("ascii")
        print(f"  CMS detached sig (DER): {len(cms_sig_der)} bytes → b64: {cms_sig_b64[:80]}...")

        # Also try PEM format
        cms_sig_pem = builder.sign(serialization.Encoding.PEM, [pkcs7.PKCS7Options.DetachedSignature])
        cms_sig_pem_b64 = base64.b64encode(cms_sig_pem).decode("ascii")
        print(f"  CMS detached sig (PEM): {len(cms_sig_pem)} bytes")
    except Exception as e:
        print(f"  PKCS#7 signing error: {e}")
        cms_sig_b64 = raw_sig_b64

    # Generate UUID for this session
    token_uuid = str(uuid.uuid4())
    print(f"  Token UUID: {token_uuid}")

    # ── POST to pjeoffice-rest ──
    print("\n" + "=" * 60)
    print("  STEP 6: Enviando assinatura para pjeoffice-rest")
    print("=" * 60)

    endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"

    # Try multiple payload variations
    payloads = [
        {
            "name": "Approach 1: CMS DER b64 + certChain as array",
            "payload": {
                "certChain": cert_chain_b64,
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": cms_sig_b64,
            },
        },
        {
            "name": "Approach 2: Raw RSA sig + certChain as string",
            "payload": {
                "certChain": cert_chain_b64[0],  # just main cert
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": raw_sig_b64,
            },
        },
        {
            "name": "Approach 3: CMS DER + certChain as single string (all certs concat)",
            "payload": {
                "certChain": "\n".join(cert_chain_b64),
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": cms_sig_b64,
            },
        },
        {
            "name": "Approach 4: Raw sig + full chain as array",
            "payload": {
                "certChain": cert_chain_b64,
                "uuid": token_uuid,
                "mensagem": mensagem,
                "assinatura": raw_sig_b64,
            },
        },
    ]

    successful_payload = None

    for approach in payloads:
        print(f"\n  --- {approach['name']} ---")
        payload_json = json.dumps(approach["payload"])
        # Use page.evaluate with fetch to send from browser context (same cookies/session)
        result = await page.evaluate("""async (payloadStr) => {
            try {
                const resp = await fetch('""" + endpoint + """', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: payloadStr,
                    credentials: 'include',
                });
                const text = await resp.text();
                return {status: resp.status, body: text.substring(0, 500)};
            } catch (e) {
                return {error: e.message};
            }
        }""", payload_json)

        print(f"  Status: {result.get('status', 'ERR')} Body: {result.get('body', result.get('error', ''))[:300]}")

        if result.get("status") == 200:
            body_text = result.get("body", "")
            if "error" not in body_text.lower() or "unknown" not in body_text.lower():
                print(f"  *** POSSIBLE SUCCESS! ***")
                successful_payload = approach
                break

    if not successful_payload:
        print("\n  Nenhuma abordagem retornou sucesso limpo. Tentando submeter form mesmo assim...")

    # ── Submit login form ──
    print("\n" + "=" * 60)
    print("  STEP 7: Submetendo formulário de login")
    print("=" * 60)

    # Set pjeoffice-code and submit
    await page.evaluate(f"""() => {{
        document.getElementById('pjeoffice-code').value = '{token_uuid}';
        console.log('pjeoffice-code set to:', document.getElementById('pjeoffice-code').value);
    }}""")
    print(f"  pjeoffice-code set to: {token_uuid}")

    # Submit the form
    print("  Submitting loginForm...")
    t0 = time.monotonic()

    await page.evaluate("""() => {
        document.getElementById('loginForm').submit();
    }""")

    # Wait for navigation
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  Wait error: {e}")

    t1 = time.monotonic()
    print(f"  Post-submit URL: {page.url}")
    print(f"  Post-submit Title: {await page.title()}")
    print(f"  Time: {t1-t0:.1f}s")

    # Take screenshot
    os.makedirs("/tmp/pje_test", exist_ok=True)
    await page.screenshot(path=f"/tmp/pje_test/login_result_{int(time.time())}.png", full_page=True)

    # Check if logged in
    body_text = await page.inner_text("body")
    print(f"\n  Body text (3000 chars): {body_text[:3000]}")

    keywords = ["painel", "advogado", "meus processos", "amanda", "localizar"]
    found = [kw for kw in keywords if kw in body_text.lower()]
    print(f"\n  Keywords found: {found}")

    if found:
        print("\n  *** LOGIN SUCCESSFUL! ***")
    else:
        print("\n  Login failed or uncertain.")
        # Check for error messages
        if any(kw in body_text.lower() for kw in ["erro", "falha", "inválido", "expirad"]):
            print("  Error detected in page text!")

    # Cleanup
    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cert_path)
    os.unlink(key_path)


if __name__ == "__main__":
    asyncio.run(main())

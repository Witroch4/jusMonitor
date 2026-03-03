"""Investiga a página de OTP/TOTP do PJe SSO.

Após o login com certificado, Keycloak está redirecionando para setup de OTP.
Este script verifica se há opção de pular/skip, e captura o conteúdo completo.
"""
import asyncio
import base64
import json
import os
import re
import sys
import tempfile
import time
import uuid as uuid_mod

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
from playwright.async_api import async_playwright


def build_pkipath(cert_ders):
    content = b"".join(cert_ders)
    n = len(content)
    lb = bytes([n]) if n < 0x80 else (bytes([0x81, n]) if n < 0x100 else bytes([0x82, n >> 8, n & 0xFF]))
    return bytes([0x30]) + lb + content


async def main():
    PFX = "/app/docs/Amanda Alves de Sousa_07071649316.pfx"
    PWD = "22051998"

    with open(PFX, "rb") as f:
        pfx_bytes = f.read()
    pkcs = load_pkcs12(pfx_bytes, PWD.encode())
    pk = pkcs.key
    cert = pkcs.cert.certificate
    chain = [c.certificate for c in (pkcs.additional_certs or [])]

    cert_pem = cert.public_bytes(Encoding.PEM)
    key_pem = pk.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    chain_pem = b"".join(c.public_bytes(Encoding.PEM) for c in chain)

    cfd, cpath = tempfile.mkstemp(suffix=".pem")
    kfd, kpath = tempfile.mkstemp(suffix=".pem")
    os.write(cfd, cert_pem + chain_pem); os.close(cfd)
    os.write(kfd, key_pem); os.close(kfd)

    cert_ders = [cert.public_bytes(Encoding.DER)] + [c.public_bytes(Encoding.DER) for c in chain]
    certchain_b64 = base64.b64encode(build_pkipath(cert_ders)).decode()

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"])
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        locale="pt-BR",
        ignore_https_errors=True,
        client_certificates=[
            {"origin": "https://sso.cloud.pje.jus.br", "certPath": cpath, "keyPath": kpath},
            {"origin": "https://pje1g.trf1.jus.br", "certPath": cpath, "keyPath": kpath},
        ],
    )
    page = await context.new_page()

    # Log all requests/responses for SSO
    def on_resp(resp):
        if "sso" in resp.url or "login-actions" in resp.url:
            print(f"RESP {resp.status} {resp.url[:120]}")
    page.on("response", on_resp)

    await page.goto("https://pje1g.trf1.jus.br/pje/login.seam", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(2)

    # Extract challenge
    data = await page.evaluate("""() => {
        const btn = document.getElementById('kc-pje-office');
        if (!btn) return null;
        const m = btn.getAttribute('onclick').match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
        const form = document.getElementById('loginForm');
        return m ? {mensagem: m[2], action: form ? form.action : null} : null;
    }""")
    print(f"Challenge: {data}")

    mensagem = data['mensagem']
    form_action = data['action']
    uuid_token = str(uuid_mod.uuid4())
    sig = pk.sign(mensagem.encode(), padding.PKCS1v15(), hashes.MD5())
    sig_b64 = base64.b64encode(sig).decode()

    # POST pjeoffice-rest
    payload = json.dumps({"certChain": certchain_b64, "uuid": uuid_token, "mensagem": mensagem, "assinatura": sig_b64})
    rest = await page.evaluate(
        """async ([url, body]) => {
            const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body, credentials:'include'});
            return {status: r.status};
        }""",
        ["https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest", payload]
    )
    print(f"pjeoffice-rest: {rest}")

    # Submit form
    await page.evaluate("""([uuid]) => {
        document.getElementById('pjeoffice-code').value = uuid;
        document.getElementById('loginForm').submit();
    }""", [uuid_token])
    await asyncio.sleep(5)

    print(f"\n=== POST SUBMIT ===")
    print(f"URL: {page.url}")

    # Save screenshot
    path = "/tmp/otp_investigate.png"
    await page.screenshot(path=path, full_page=True)
    print(f"Screenshot: {path}")

    # Get full page content
    body = await page.inner_text("body")
    print(f"\nBody text:\n{body[:3000]}")

    # Get all interactive elements
    elems = await page.evaluate("""() => {
        const res = [];
        document.querySelectorAll('a, button, input[type="submit"], input[type="button"]').forEach(el => {
            const text = (el.textContent || el.value || '').trim();
            res.push({tag:el.tagName, text: text.substring(0,80), id: el.id||'', href: el.href||'', name: el.name||''});
        });
        return res;
    }""")
    print(f"\nInteractive elements ({len(elems)}):")
    for e in elems:
        print(f"  {e['tag']} id={e['id']} name={e['name']} text={e['text'][:60]} href={e['href'][:60]}")

    # Get all form fields
    forms = await page.evaluate("""() => {
        const res = [];
        document.querySelectorAll('form').forEach(form => {
            const fields = [];
            form.querySelectorAll('input, select, textarea').forEach(f => {
                fields.push({name: f.name, type: f.type, id: f.id, value: f.value?.substring(0,50)});
            });
            res.push({action: form.action, method: form.method, fields});
        });
        return res;
    }""")
    print(f"\nForms:")
    for form in forms:
        print(f"  action={form['action'][:100]} method={form['method']}")
        for f in form['fields']:
            print(f"    {f['type']} name={f['name']} id={f['id']} value={f['value']}")

    await context.close()
    await browser.close()
    await pw.stop()
    os.unlink(cpath)
    os.unlink(kpath)


if __name__ == "__main__":
    asyncio.run(main())

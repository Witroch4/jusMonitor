"""PJe Peticionamento via Playwright (RPA) — protocola petição via interface web.

Usado quando o endpoint MNI SOAP está bloqueado pelo firewall do tribunal (ex: TRF1).
Simula o advogado acessando o PJe pelo browser:
  1. Login com certificado A1 (mTLS no Playwright)
  2. Navega até o processo
  3. Clica "Juntar petição/documento"
  4. Preenche tipo + descrição + upload PDF
  5. Assina e protocola
  6. Captura número do protocolo

Logging minucioso (DEBUG) em cada etapa para diagnóstico.
"""

import asyncio
import base64
import json
import logging
import os
import re
import tempfile
import time
import uuid as uuid_mod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pyotp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)
from playwright_stealth import Stealth

from app.browser_pool import BROWSER_ARGS, USER_AGENT, human_delay

logger = logging.getLogger(__name__)

_stealth = Stealth()


# ──────────────────────────────────────────────────────────────────
# PJeOffice SSO helpers — simula o PJeOffice desktop para autenticar
# ──────────────────────────────────────────────────────────────────


def _build_pkipath_der(cert_ders: list) -> bytes:
    """ASN.1 SEQUENCE OF Certificate (PKIPath DER), conforme signer4j."""
    content = b"".join(cert_ders)
    n = len(content)
    if n < 0x80:
        lb = bytes([n])
    elif n < 0x100:
        lb = bytes([0x81, n])
    elif n < 0x10000:
        lb = bytes([0x82, n >> 8, n & 0xFF])
    else:
        lb = bytes([0x83, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
    return bytes([0x30]) + lb + content


def _get_certchain_b64(cert_obj, additional_certs) -> str:
    """PKIPath base64 (end-entity first), campo certChain do pjeoffice-rest."""
    cert_ders = [cert_obj.public_bytes(Encoding.DER)]
    for c in additional_certs:
        cert_ders.append(c.public_bytes(Encoding.DER))
    return base64.b64encode(_build_pkipath_der(cert_ders)).decode("ascii")


def _sign_md5_rsa(private_key, mensagem: str) -> str:
    """MD5withRSA PKCS1v15 — algoritmo usado pelo PJeOffice (signer4j)."""
    sig = private_key.sign(mensagem.encode("utf-8"), padding.PKCS1v15(), hashes.MD5())
    return base64.b64encode(sig).decode("ascii")


# ──────────────────────────────────────────────────────────────────
# PJe Login URLs per tribunal (SSO-based)
# ──────────────────────────────────────────────────────────────────

PJE_LOGIN_URLS = {
    "trf1": "https://pje1g.trf1.jus.br/pje/login.seam",
    "trf3": "https://pje1g.trf3.jus.br/pje/login.seam",
    "trf5": "https://pje.jfce.jus.br/pje/login.seam",
    "trf6": "https://pje1g.trf6.jus.br/pje/login.seam",
    "tjce": "https://pje.tjce.jus.br/pje1grau/login.seam",
}

# PJe base URLs (authenticated area)
PJE_BASE_URLS = {
    "trf1": "https://pje1g.trf1.jus.br/pje",
    "trf3": "https://pje1g.trf3.jus.br/pje",
    "trf5": "https://pje.jfce.jus.br/pje",
    "trf6": "https://pje1g.trf6.jus.br/pje",
    "tjce": "https://pje.tjce.jus.br/pje1grau",
}

# SSO origin for client certificate matching
PJE_SSO_ORIGINS = {
    "trf1": [
        "https://sso.cloud.pje.jus.br",
        "https://pje1g.trf1.jus.br",
    ],
    "trf3": [
        "https://sso.cloud.pje.jus.br",
        "https://pje1g.trf3.jus.br",
    ],
    "trf5": [
        "https://sso.cloud.pje.jus.br",
        "https://pje.jfce.jus.br",
    ],
    "trf6": [
        "https://sso.cloud.pje.jus.br",
        "https://pje1g.trf6.jus.br",
    ],
    "tjce": [
        "https://sso.cloud.pje.jus.br",
        "https://pje.tjce.jus.br",
    ],
}


@dataclass
class PeticionamentoResult:
    """Resultado do peticionamento via Playwright."""
    sucesso: bool
    mensagem: str
    numero_protocolo: Optional[str] = None
    screenshots: list[str] = None  # Paths das screenshots de debug

    def __post_init__(self):
        if self.screenshots is None:
            self.screenshots = []

    def to_dict(self) -> dict:
        return {
            "sucesso": self.sucesso,
            "mensagem": self.mensagem,
            "numero_protocolo": self.numero_protocolo,
            "screenshots": self.screenshots,
        }


# ──────────────────────────────────────────────────────────────────
# Certificate extraction (PFX → PEM)
# ──────────────────────────────────────────────────────────────────


def _extract_pem_from_pfx(
    pfx_bytes: bytes, pfx_password: str
) -> tuple[str, str]:
    """Extract PEM certificate and private key from PFX.

    Returns: (cert_path, key_path) — temporary file paths the caller must delete.
    """
    logger.debug("[CERT] Extraindo PEM do PFX (tamanho=%d bytes)", len(pfx_bytes))

    pkcs = load_pkcs12(pfx_bytes, pfx_password.encode())

    cert_pem = pkcs.cert.certificate.public_bytes(Encoding.PEM)
    key_pem = pkcs.key.private_bytes(
        Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
    )

    # Incluir certificados da cadeia se existirem
    chain_pem = b""
    if pkcs.additional_certs:
        for extra_cert in pkcs.additional_certs:
            chain_pem += extra_cert.certificate.public_bytes(Encoding.PEM)
        logger.debug("[CERT] Cadeia inclui %d certificados adicionais", len(pkcs.additional_certs))

    cert_fd, cert_path = tempfile.mkstemp(suffix=".pem", prefix="pje_cert_")
    key_fd, key_path = tempfile.mkstemp(suffix=".pem", prefix="pje_key_")

    os.write(cert_fd, cert_pem + chain_pem)
    os.close(cert_fd)
    os.write(key_fd, key_pem)
    os.close(key_fd)

    # Log info do certificado
    try:
        cert_obj = pkcs.cert.certificate
        subject = cert_obj.subject.rfc4514_string()
        not_after = cert_obj.not_valid_after_utc
        logger.info("[CERT] Certificado: subject=%s valido_ate=%s", subject, not_after)
    except Exception as e:
        logger.debug("[CERT] Não conseguiu ler subject: %s", e)

    logger.debug("[CERT] Arquivos PEM criados: cert=%s key=%s", cert_path, key_path)
    return cert_path, key_path


def _cleanup_pem_files(*paths: str) -> None:
    """Remove temporary PEM files."""
    for p in paths:
        try:
            os.unlink(p)
            logger.debug("[CERT] Arquivo removido: %s", p)
        except OSError:
            pass


# ──────────────────────────────────────────────────────────────────
# Screenshot helper
# ──────────────────────────────────────────────────────────────────


async def _screenshot(page: Page, name: str, tag: str) -> str:
    """Take debug screenshot and return the path."""
    path = f"/tmp/pje_peticionamento_{name}_{int(time.time())}.png"
    try:
        await page.screenshot(path=path, full_page=True)
        logger.debug("%s Screenshot salva: %s", tag, path)
        return path
    except Exception as e:
        logger.debug("%s Screenshot falhou: %s", tag, e)
        return ""


# ──────────────────────────────────────────────────────────────────
# Main petitioning function
# ──────────────────────────────────────────────────────────────────


async def protocolar_peticao_pje(
    tribunal_code: str,
    numero_processo: str,
    pfx_base64: str,
    pfx_password: str,
    pdf_base64: str,
    tipo_documento: str = "Petição",
    descricao: str = "",
    totp_secret: Optional[str] = None,
) -> PeticionamentoResult:
    """Protocolar petição via Playwright no PJe.

    Args:
        tribunal_code: Código do tribunal (ex: "trf1")
        numero_processo: Número formatado do processo (ex: "1000654-37.2026.4.01.3704")
        pfx_base64: Certificado A1 em base64
        pfx_password: Senha do certificado
        pdf_base64: PDF da petição em base64
        tipo_documento: Tipo do documento (ex: "Petição", "Contestação")
        descricao: Descrição do documento
        totp_secret: Segredo TOTP (base32) para 2FA, se configurado no SSO

    Returns:
        PeticionamentoResult com sucesso/falha e protocolo
    """
    tag = f"[PJE-PROTOCOLO-{tribunal_code.upper()}]"
    screenshots = []

    login_url = PJE_LOGIN_URLS.get(tribunal_code.lower())
    base_url = PJE_BASE_URLS.get(tribunal_code.lower())
    sso_origins = PJE_SSO_ORIGINS.get(tribunal_code.lower(), [])

    if not login_url or not base_url:
        return PeticionamentoResult(
            sucesso=False,
            mensagem=f"Tribunal '{tribunal_code}' não configurado para peticionamento Playwright.",
        )

    logger.info(
        "%s ══════════ INÍCIO PETICIONAMENTO ══════════", tag
    )
    logger.info(
        "%s tribunal=%s processo=%s login_url=%s",
        tag, tribunal_code, numero_processo, login_url,
    )

    # ── Step 0: Decode inputs ──
    try:
        pfx_bytes = base64.b64decode(pfx_base64)
        logger.info("%s PFX decodificado: %d bytes", tag, len(pfx_bytes))
    except Exception as e:
        logger.error("%s Erro decodificando PFX base64: %s", tag, e)
        return PeticionamentoResult(sucesso=False, mensagem=f"PFX inválido: {e}")

    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        logger.info("%s PDF decodificado: %d bytes (%.1f KB)", tag, len(pdf_bytes), len(pdf_bytes) / 1024)
    except Exception as e:
        logger.error("%s Erro decodificando PDF base64: %s", tag, e)
        return PeticionamentoResult(sucesso=False, mensagem=f"PDF inválido: {e}")

    # Salvar PDF em arquivo temporário para upload
    pdf_fd, pdf_path = tempfile.mkstemp(suffix=".pdf", prefix="pje_doc_")
    os.write(pdf_fd, pdf_bytes)
    os.close(pdf_fd)
    logger.debug("%s PDF salvo em: %s", tag, pdf_path)

    # ── Step 1: Extract PEM from PFX + load crypto objects for SSO signing ──
    cert_path = key_path = None
    try:
        cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)
    except Exception as e:
        logger.error("%s Erro extraindo PEM do PFX: %s", tag, e)
        _cleanup_pem_files(pdf_path)
        return PeticionamentoResult(sucesso=False, mensagem=f"Erro no certificado: {e}")

    # Carregar objetos crypto para assinatura SSO (MD5withRSA + PKIPath DER)
    try:
        _pkcs = load_pkcs12(pfx_bytes, pfx_password.encode())
        _private_key = _pkcs.key
        _cert_obj = _pkcs.cert.certificate
        _additional_certs = [c.certificate for c in (_pkcs.additional_certs or [])]
        _certchain_b64 = _get_certchain_b64(_cert_obj, _additional_certs)
        logger.info(
            "%s PKIPath certChain preparado (%d certs, %d chars b64)",
            tag, 1 + len(_additional_certs), len(_certchain_b64),
        )
    except Exception as e:
        logger.error("%s Erro carregando PKCS12 para assinatura SSO: %s", tag, e)
        _cleanup_pem_files(cert_path or "", key_path or "", pdf_path)
        return PeticionamentoResult(sucesso=False, mensagem=f"Erro no certificado PKCS12: {e}")

    # ── Step 2: Launch browser with mTLS ──
    pw = None
    browser = None
    context = None

    try:
        logger.info("%s Iniciando Playwright + Chromium...", tag)
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=BROWSER_ARGS,
        )
        logger.info("%s Browser lançado (headless)", tag)

        # Build client_certificates for all relevant origins
        client_certs = []
        for origin in sso_origins:
            client_certs.append({
                "origin": origin,
                "certPath": cert_path,
                "keyPath": key_path,
            })
        logger.info(
            "%s Configurando mTLS para %d origins: %s",
            tag, len(client_certs), [c["origin"] for c in client_certs],
        )

        context = await browser.new_context(
            user_agent=USER_AGENT,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            accept_downloads=True,
            client_certificates=client_certs,
        )
        await _stealth.apply_stealth_async(context)
        page = await context.new_page()

        # Console listener para debug
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

        # ── Step 3: Navigate to login page ──
        logger.info("%s Navegando para login: %s", tag, login_url)
        t0 = time.monotonic()
        await page.goto(login_url, wait_until="domcontentloaded", timeout=60_000)
        t1 = time.monotonic()
        logger.info(
            "%s Página de login carregada em %.1fs | URL=%s | Title=%s",
            tag, t1 - t0, page.url, await page.title(),
        )

        s = await _screenshot(page, "01_login_page", tag)
        if s:
            screenshots.append(s)

        await asyncio.sleep(2)

        # ── Step 4: Extract SSO challenge from login page ──
        # O botão CERTIFICADO DIGITAL tem onclick="autenticar(codigoSeguranca, mensagem)"
        # Extraímos mensagem (nonce) e form_action sem clicar no botão
        logger.info("%s Extraindo challenge SSO do botão CERTIFICADO DIGITAL...", tag)

        onclick_data = await page.evaluate("""() => {
            // Tenta pelo id do elemento PJeOffice
            const btn = document.getElementById('kc-pje-office');
            if (btn) {
                const oc = btn.getAttribute('onclick') || '';
                const m = oc.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
                if (m) return {codigoSeguranca: m[1], mensagem: m[2]};
            }
            // Fallback: qualquer elemento com autenticar() no onclick
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
            logger.error(
                "%s Challenge SSO não encontrado! URL=%s | Texto (2000): %s",
                tag, page.url, body_text[:2000],
            )
            s = await _screenshot(page, "01b_no_challenge", tag)
            if s:
                screenshots.append(s)
            return PeticionamentoResult(
                sucesso=False,
                mensagem="Challenge SSO (autenticar) não encontrado na página de login.",
                screenshots=screenshots,
            )

        mensagem_sso = onclick_data["mensagem"]
        logger.info("%s mensagem SSO (nonce): %s", tag, mensagem_sso)

        form_action = await page.evaluate("""() => {
            const form = document.getElementById('loginForm');
            return form ? form.action : null;
        }""")
        logger.info("%s Form action: %s", tag, (form_action or "")[:150])

        if not form_action:
            logger.error("%s Form action não encontrado!", tag)
            return PeticionamentoResult(
                sucesso=False,
                mensagem="Form action do login SSO não encontrado.",
                screenshots=screenshots,
            )

        # ── Step 5: Assinar mensagem com MD5withRSA + POST para pjeoffice-rest ──
        # Simula o PJeOffice desktop (signer4j): assina com MD5withRSA + PKIPath DER
        logger.info("%s Assinando mensagem SSO com MD5withRSA...", tag)
        token_uuid = str(uuid_mod.uuid4())
        assinatura_b64 = _sign_md5_rsa(_private_key, mensagem_sso)

        pjeoffice_endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"
        sso_payload = json.dumps({
            "certChain": _certchain_b64,
            "uuid": token_uuid,
            "mensagem": mensagem_sso,
            "assinatura": assinatura_b64,
        })

        logger.info(
            "%s POST pjeoffice-rest | uuid=%s certChain_len=%d sig_len=%d",
            tag, token_uuid, len(_certchain_b64), len(assinatura_b64),
        )

        # Enviar via browser fetch para usar os cookies de sessão do Keycloak
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
            logger.error("%s Erro no fetch pjeoffice-rest: %s", tag, rest_result["error"])
            return PeticionamentoResult(
                sucesso=False,
                mensagem=f"Erro ao contatar SSO pjeoffice-rest: {rest_result['error']}",
                screenshots=screenshots,
            )

        rest_status = rest_result.get("status", 0)
        logger.info(
            "%s pjeoffice-rest: HTTP %d | body: %s",
            tag, rest_status, rest_result.get("body", "")[:200],
        )

        if rest_status not in (200, 204):
            logger.error(
                "%s pjeoffice-rest falhou! HTTP %d esperado 204. body=%s",
                tag, rest_status, rest_result.get("body", ""),
            )
            s = await _screenshot(page, "01c_pjeoffice_rest_fail", tag)
            if s:
                screenshots.append(s)
            return PeticionamentoResult(
                sucesso=False,
                mensagem=f"SSO pjeoffice-rest falhou: HTTP {rest_status}",
                screenshots=screenshots,
            )

        logger.info("%s ✓ pjeoffice-rest: OK (HTTP %d)! Submetendo formulário...", tag, rest_status)

        # ── Step 6: Submeter loginForm com pjeoffice-code = uuid ──
        # IMPORTANTE: incluir o campo "login-pje-office" com valor "CERTIFICADO DIGITAL"
        # Isso indica ao Keycloak que usou autenticação por certificado (skipa OTP)
        await page.evaluate(
            """([uuid]) => {
                const code = document.getElementById('pjeoffice-code');
                if (code) code.value = uuid;

                // Inclui o nome/valor do botão CERTIFICADO DIGITAL para o Keycloak
                // reconhecer como fluxo de certificado e não pedir OTP
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

        # Aguardar redirect Keycloak → PJe dashboard
        logger.info("%s Aguardando redirect SSO → PJe (até 30s)...", tag)
        t0 = time.monotonic()
        try:
            await page.wait_for_url(
                re.compile(r"(painel|Painel|principal|home|pje1g\.trf|pje\.jf|pje\.tj)"),
                timeout=30_000,
            )
        except PlaywrightTimeout:
            logger.warning(
                "%s Timeout redirect pós-login (30s). URL atual: %s",
                tag, page.url,
            )

        # Aguardar página estabilizar após redirect
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except Exception:
            pass
        await asyncio.sleep(2)

        # ── Step 6b: Verificar e tratar página de TOTP ──
        # Keycloak pode exigir TOTP como segundo fator após certificado
        otp_input = page.locator("input[name='otp'], input[id='otp']")
        if await otp_input.count() > 0:
            logger.info("%s Página de TOTP detectada (URL=%s)", tag, page.url)
            s = await _screenshot(page, "02b_otp_page", tag)
            if s:
                screenshots.append(s)

            if not totp_secret:
                logger.error(
                    "%s TOTP requerido mas totp_secret não fornecido! "
                    "Configure o segredo TOTP no perfil do advogado.",
                    tag,
                )
                return PeticionamentoResult(
                    sucesso=False,
                    mensagem=(
                        "Login requer TOTP (autenticação de 2 fatores). "
                        "Configure o segredo TOTP (base32) no perfil do advogado."
                    ),
                    screenshots=screenshots,
                )

            # Gerar código TOTP atual
            totp_code = pyotp.TOTP(totp_secret.strip().upper()).now()
            logger.info("%s Gerando código TOTP: %s (secret_len=%d)", tag, totp_code, len(totp_secret))

            await otp_input.first.fill(totp_code)
            await asyncio.sleep(0.3)

            # Clicar no botão validar/confirmar OTP
            submit_btn = page.locator("input[name='login'], input[id='kc-login'], button[type='submit']")
            if await submit_btn.count() > 0:
                await submit_btn.first.click()
            else:
                await otp_input.first.press("Enter")

            logger.info("%s TOTP submetido, aguardando redirect (até 20s)...", tag)
            try:
                await page.wait_for_url(
                    re.compile(r"(painel|Painel|principal|home|pje1g\.trf|pje\.jf|pje\.tj)"),
                    timeout=20_000,
                )
            except PlaywrightTimeout:
                logger.warning("%s Timeout após TOTP. URL=%s", tag, page.url)

            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10_000)
            except Exception:
                pass
            await asyncio.sleep(2)
            logger.info("%s Pós-TOTP. URL=%s", tag, page.url)

        t1 = time.monotonic()
        try:
            _page_title = await page.title()
        except Exception:
            _page_title = "(navegando...)"
        logger.info(
            "%s Pós-login em %.1fs | URL=%s | Title=%s",
            tag, t1 - t0, page.url, _page_title,
        )

        s = await _screenshot(page, "02_post_login", tag)
        if s:
            screenshots.append(s)

        # ── Step 7: Verificar se o login foi confirmado ──
        body_text = await page.inner_text("body")
        # Keywords definitivas do painel do advogado (validadas em testes reais)
        is_logged_in = any(kw in body_text.lower() for kw in [
            "expedientes", "localizar processo", "meu painel",
            "nova tarefa", "fila de tarefas", "avisos do sistema",
        ])

        if not is_logged_in:
            logger.error(
                "%s Login não confirmado! URL=%s | Texto (2000 chars): %s",
                tag, page.url, body_text[:2000],
            )
            if console_msgs:
                logger.debug("%s Console msgs: %s", tag, console_msgs[:20])
            return PeticionamentoResult(
                sucesso=False,
                mensagem=f"Login com certificado falhou. URL pós-login: {page.url}",
                screenshots=screenshots,
            )

        logger.info("%s ✓ Login confirmado! Painel do advogado detectado.", tag)

        # ── Step 8: Navegar até o processo ──
        logger.info("%s Navegando até o processo %s...", tag, numero_processo)

        # Tentar navegar direto pela URL de consulta interna
        # PJe pattern: /pje/Processo/ConsultaProcesso/Detalhe/listProcessoView.seam
        # Ou usar a barra de pesquisa do painel
        resultado_busca = await _navegar_para_processo(page, base_url, numero_processo, tag)

        s = await _screenshot(page, "03_processo", tag)
        if s:
            screenshots.append(s)

        if not resultado_busca:
            logger.error(
                "%s Processo %s não encontrado/acessado. URL=%s",
                tag, numero_processo, page.url,
            )
            return PeticionamentoResult(
                sucesso=False,
                mensagem=f"Processo {numero_processo} não encontrado na busca.",
                screenshots=screenshots,
            )

        logger.info("%s ✓ Processo localizado!", tag)

        # ── Step 9: Abrir "Juntar Petição/Documento" ──
        logger.info("%s Procurando opção de juntar petição/documento...", tag)

        result_juntar = await _abrir_juntar_documento(page, tag)

        s = await _screenshot(page, "04_juntar_documento", tag)
        if s:
            screenshots.append(s)

        if not result_juntar:
            logger.error("%s Opção de juntar documento não encontrada", tag)
            body_text = await page.inner_text("body")
            logger.debug("%s Texto da página (processo): %s", tag, body_text[:3000])
            return PeticionamentoResult(
                sucesso=False,
                mensagem="Opção 'Juntar documento' não encontrada no processo.",
                screenshots=screenshots,
            )

        logger.info("%s ✓ Formulário de juntar documento aberto!", tag)

        # ── Step 10: Preencher tipo + descrição ──
        logger.info("%s Preenchendo formulário: tipo=%s descricao=%s", tag, tipo_documento, descricao[:80])

        await _preencher_formulario_peticao(page, tipo_documento, descricao, tag)

        s = await _screenshot(page, "05_formulario_preenchido", tag)
        if s:
            screenshots.append(s)

        # ── Step 11: Upload PDF ──
        logger.info("%s Fazendo upload do PDF (%d bytes)...", tag, len(pdf_bytes))

        upload_ok = await _upload_pdf(page, pdf_path, tag)

        s = await _screenshot(page, "06_pdf_uploaded", tag)
        if s:
            screenshots.append(s)

        if not upload_ok:
            logger.error("%s Upload do PDF falhou", tag)
            return PeticionamentoResult(
                sucesso=False,
                mensagem="Upload do PDF falhou.",
                screenshots=screenshots,
            )

        logger.info("%s ✓ PDF uploaded!", tag)

        # ── Step 12: Assinar e enviar ──
        logger.info("%s Assinando e enviando petição...", tag)

        protocolo = await _assinar_e_enviar(page, tag)

        s = await _screenshot(page, "07_enviado", tag)
        if s:
            screenshots.append(s)

        if protocolo:
            logger.info(
                "%s ══════════ PETIÇÃO PROTOCOLADA ══════════ protocolo=%s",
                tag, protocolo,
            )
            return PeticionamentoResult(
                sucesso=True,
                mensagem=f"Petição protocolada com sucesso! Protocolo: {protocolo}",
                numero_protocolo=protocolo,
                screenshots=screenshots,
            )
        else:
            body_text = await page.inner_text("body")
            logger.warning(
                "%s Envio aparentemente concluído mas protocolo não capturado. Texto: %s",
                tag, body_text[:3000],
            )
            return PeticionamentoResult(
                sucesso=False,
                mensagem="Envio concluído mas número de protocolo não capturado. Verificar screenshots.",
                screenshots=screenshots,
            )

    except PlaywrightTimeout as e:
        logger.error("%s TIMEOUT: %s", tag, e)
        return PeticionamentoResult(
            sucesso=False,
            mensagem=f"Timeout durante peticionamento: {e}",
            screenshots=screenshots,
        )
    except Exception as e:
        logger.error("%s ERRO INESPERADO: %s", tag, e, exc_info=True)
        return PeticionamentoResult(
            sucesso=False,
            mensagem=f"Erro inesperado: {type(e).__name__}: {e}",
            screenshots=screenshots,
        )
    finally:
        # Cleanup
        logger.debug("%s Limpando recursos...", tag)
        if context:
            try:
                await context.close()
            except Exception:
                pass
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if pw:
            try:
                await pw.stop()
            except Exception:
                pass
        _cleanup_pem_files(cert_path or "", key_path or "", pdf_path)
        logger.info("%s ══════════ FIM PETICIONAMENTO ══════════", tag)


# ──────────────────────────────────────────────────────────────────
# Sub-steps: cada etapa do fluxo PJe
# ──────────────────────────────────────────────────────────────────


async def _navegar_para_processo(
    page: Page, base_url: str, numero_processo: str, tag: str
) -> bool:
    """Navega até o processo dentro do PJe autenticado.

    Estratégias:
    1. Busca pelo campo de pesquisa rápida no painel
    2. Navega para a URL de consulta processual direta
    3. Usa menu Processo > Pesquisar
    """
    numero_clean = numero_processo.replace(".", "").replace("-", "").replace(" ", "")

    # Estratégia 1: Campo de pesquisa rápida no painel
    logger.debug("%s Tentando busca rápida no painel...", tag)
    for selector in [
        "input[id*='pesquisaRapida']",
        "input[placeholder*='processo']",
        "input[placeholder*='Processo']",
        "input[id*='numeroProcesso']",
        "input[name*='numeroProcesso']",
    ]:
        try:
            campo = page.locator(selector)
            if await campo.count() > 0:
                logger.info("%s Campo de busca encontrado: %s", tag, selector)
                await campo.first.fill(numero_processo)
                await human_delay(0.3, 0.6)

                # Pressionar Enter ou clicar botão de busca
                await campo.first.press("Enter")
                logger.info("%s Enter pressionado na busca rápida", tag)

                await asyncio.sleep(3)
                logger.debug("%s URL pós-busca: %s", tag, page.url)

                # Verificar se chegou na página do processo
                body = await page.inner_text("body")
                if numero_processo in body or numero_clean in body:
                    logger.info("%s Processo encontrado via busca rápida!", tag)
                    return True
                break
        except Exception as e:
            logger.debug("%s Busca rápida com %s falhou: %s", tag, selector, e)

    # Estratégia 2: Navegar pela URL de pesquisa processual
    logger.debug("%s Tentando navegar pela URL de pesquisa processual...", tag)
    search_urls = [
        f"{base_url}/Processo/ConsultaProcesso/listView.seam",
        f"{base_url}/ConsultaProcesso/listView.seam",
    ]

    for search_url in search_urls:
        try:
            logger.debug("%s Navegando para: %s", tag, search_url)
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
            await asyncio.sleep(2)

            # Procurar campo de número do processo
            for input_sel in [
                "input[id*='numeroProcesso']",
                "input[id*='numProcesso']",
                "input[name*='numero']",
            ]:
                campo = page.locator(input_sel)
                if await campo.count() > 0:
                    logger.info("%s Campo número processo: %s", tag, input_sel)
                    await campo.first.fill(numero_processo)
                    await human_delay(0.3, 0.6)

                    # Buscar botão de pesquisa
                    for btn_sel in [
                        "input[value*='Pesquisar']",
                        "button:has-text('Pesquisar')",
                        "a:has-text('Pesquisar')",
                        "[id*='btnPesquisar']",
                    ]:
                        btn = page.locator(btn_sel)
                        if await btn.count() > 0:
                            await btn.first.click()
                            logger.info("%s Pesquisa executada", tag)
                            await asyncio.sleep(3)
                            break

                    body = await page.inner_text("body")
                    if numero_processo in body or numero_clean in body:
                        # Clicar no link do processo nos resultados
                        proc_link = page.locator(f"a:has-text('{numero_processo}')")
                        if await proc_link.count() > 0:
                            await proc_link.first.click()
                            await asyncio.sleep(2)
                        logger.info("%s Processo encontrado via pesquisa processual!", tag)
                        return True
                    break
        except Exception as e:
            logger.debug("%s URL %s falhou: %s", tag, search_url, e)

    # Estratégia 3: Tentar URL direta de autos digitais
    logger.debug("%s Tentando URL direta de autos digitais...", tag)
    try:
        autos_url = f"{base_url}/Processo/ConsultaProcesso/Detalhe/listProcessoCompletoView.seam"
        await page.goto(autos_url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(2)
        logger.debug("%s Autos URL carregada: %s", tag, page.url)
    except Exception as e:
        logger.debug("%s URL direta falhou: %s", tag, e)

    # Log estado final para debug
    body = await page.inner_text("body")
    logger.debug("%s Estado final busca. URL=%s Texto (1500 chars): %s", tag, page.url, body[:1500])

    return False


async def _abrir_juntar_documento(page: Page, tag: str) -> bool:
    """Abre a interface de 'Juntar documento' ou 'Incluir petição'.

    O PJe pode ter diferentes caminhos:
    - Aba "Expedientes" > "Juntar Petição/Documento"
    - Botão "Incluir petição/documento" direto na página do processo
    - Menu lateral "Outras ações" > "Juntar petição"
    """
    # Listar todos os links/botões na página para debug
    all_buttons = await page.evaluate("""() => {
        const elements = [];
        document.querySelectorAll('a, button, input[type="submit"], input[type="button"]').forEach(el => {
            const text = (el.textContent || el.value || '').trim();
            if (text.length > 0 && text.length < 100) {
                elements.push({
                    tag: el.tagName,
                    text: text.substring(0, 80),
                    id: el.id || '',
                    href: el.href || '',
                });
            }
        });
        return elements;
    }""")
    logger.debug(
        "%s Botões/links na página do processo (%d): %s",
        tag, len(all_buttons), all_buttons[:30],
    )

    # Seletores para a opção de juntar documento
    selectors = [
        "a:has-text('Juntar Petição')",
        "a:has-text('Juntar petição')",
        "a:has-text('Juntar Documento')",
        "a:has-text('Juntar documento')",
        "a:has-text('Incluir Petição')",
        "a:has-text('Incluir petição')",
        "a:has-text('Incluir Documento')",
        "a:has-text('Incluir documento')",
        "a:has-text('Protocolar Petição')",
        "button:has-text('Juntar')",
        "[id*='juntarDocumento']",
        "[id*='juntarPeticao']",
        "[id*='incluirDocumento']",
        "[id*='incluirPeticao']",
        "a:has-text('Petições avulsas')",
        "a:has-text('Petição avulsa')",
    ]

    for selector in selectors:
        try:
            el = page.locator(selector)
            if await el.count() > 0:
                logger.info("%s Opção encontrada: %s (contagem=%d)", tag, selector, await el.count())
                await el.first.click()
                await asyncio.sleep(2)

                logger.info("%s Pós-clique juntar. URL=%s", tag, page.url)
                return True
        except Exception as e:
            logger.debug("%s Seletor %s falhou: %s", tag, selector, e)

    # Tentar expandir menus colapsados
    for menu_sel in [
        "a:has-text('Outras ações')",
        "a:has-text('Ações')",
        "[id*='outrasAcoes']",
        ".panel-heading:has-text('Expedientes')",
    ]:
        try:
            menu = page.locator(menu_sel)
            if await menu.count() > 0:
                logger.info("%s Expandindo menu: %s", tag, menu_sel)
                await menu.first.click()
                await asyncio.sleep(1)

                # Tentar novamente os seletores
                for selector in selectors[:6]:
                    el = page.locator(selector)
                    if await el.count() > 0:
                        await el.first.click()
                        await asyncio.sleep(2)
                        return True
        except Exception:
            continue

    return False


async def _preencher_formulario_peticao(
    page: Page, tipo_documento: str, descricao: str, tag: str
) -> None:
    """Preenche o formulário de peticionamento (tipo + descrição)."""

    # Selecionar tipo de documento
    tipo_selectors = [
        "select[id*='tipoDocumento']",
        "select[id*='tipo']",
        "[id*='tipoDocumento'] select",
    ]

    for sel in tipo_selectors:
        try:
            select = page.locator(sel)
            if await select.count() > 0:
                logger.info("%s Selecionando tipo documento: %s → %s", tag, sel, tipo_documento)
                # Tentar pelo texto da opção
                await select.first.select_option(label=tipo_documento)
                logger.info("%s Tipo selecionado!", tag)
                break
        except Exception as e:
            logger.debug("%s Tipo selector %s falhou: %s", tag, sel, e)

    await human_delay(0.3, 0.6)

    # Preencher descrição
    desc_selectors = [
        "textarea[id*='descricao']",
        "input[id*='descricao']",
        "textarea[id*='observacao']",
        "input[id*='observacao']",
    ]

    if descricao:
        for sel in desc_selectors:
            try:
                campo = page.locator(sel)
                if await campo.count() > 0:
                    logger.info("%s Preenchendo descrição: %s", tag, sel)
                    await campo.first.fill(descricao)
                    logger.info("%s Descrição preenchida!", tag)
                    break
            except Exception as e:
                logger.debug("%s Descrição selector %s falhou: %s", tag, sel, e)

    await human_delay(0.2, 0.5)

    # Log do estado do formulário
    form_state = await page.evaluate("""() => {
        const selects = document.querySelectorAll('select');
        const inputs = document.querySelectorAll('input, textarea');
        const state = {};
        selects.forEach(s => { if (s.id) state[s.id] = s.value; });
        inputs.forEach(i => { if (i.id && i.type !== 'hidden') state[i.id] = i.value?.substring(0, 50); });
        return state;
    }""")
    logger.debug("%s Estado do formulário: %s", tag, form_state)


async def _upload_pdf(page: Page, pdf_path: str, tag: str) -> bool:
    """Faz upload do PDF no formulário de peticionamento."""

    # Procurar input de arquivo
    file_selectors = [
        "input[type='file']",
        "input[id*='arquivo']",
        "input[id*='upload']",
        "input[name*='arquivo']",
        "input[name*='upload']",
        "input[accept*='pdf']",
    ]

    for sel in file_selectors:
        try:
            file_input = page.locator(sel)
            if await file_input.count() > 0:
                logger.info("%s Input de arquivo encontrado: %s (count=%d)", tag, sel, await file_input.count())
                await file_input.first.set_input_files(pdf_path)
                logger.info("%s Arquivo selecionado!", tag)
                await asyncio.sleep(2)

                # Algumas páginas têm um botão "Enviar" ou "Adicionar" após selecionar arquivo
                for btn_sel in [
                    "button:has-text('Enviar')",
                    "button:has-text('Adicionar')",
                    "input[value*='Enviar']",
                    "input[value*='Adicionar']",
                    "[id*='btnEnviar']",
                    "[id*='btnAdicionar']",
                ]:
                    btn = page.locator(btn_sel)
                    if await btn.count() > 0:
                        logger.info("%s Clicando botão de enviar arquivo: %s", tag, btn_sel)
                        await btn.first.click()
                        await asyncio.sleep(2)
                        break

                return True
        except Exception as e:
            logger.debug("%s File input %s falhou: %s", tag, sel, e)

    # Tentar drag-and-drop zone
    logger.debug("%s Procurando dropzone para upload...", tag)
    dropzone = page.locator("[class*='dropzone'], [class*='upload-area'], [class*='file-drop']")
    if await dropzone.count() > 0:
        logger.info("%s Dropzone encontrada, tentando set_input_files via JS", tag)
        # Forçar criação de input file
        await page.evaluate("""() => {
            const input = document.createElement('input');
            input.type = 'file';
            input.id = '__pje_upload_hack';
            input.style.display = 'none';
            document.body.appendChild(input);
        }""")
        hack_input = page.locator("#__pje_upload_hack")
        await hack_input.set_input_files(pdf_path)
        return True

    logger.error("%s Nenhum input de arquivo encontrado na página!", tag)
    return False


async def _assinar_e_enviar(page: Page, tag: str) -> Optional[str]:
    """Assina e envia a petição. Retorna número de protocolo se sucesso."""

    # 1. Clicar no botão de assinar/protocolar
    sign_selectors = [
        "button:has-text('Assinar')",
        "button:has-text('Protocolar')",
        "button:has-text('Peticionar')",
        "a:has-text('Assinar')",
        "a:has-text('Protocolar')",
        "a:has-text('Peticionar')",
        "input[value*='Assinar']",
        "input[value*='Protocolar']",
        "input[value*='Peticionar']",
        "[id*='btnAssinar']",
        "[id*='btnProtocolar']",
        "[id*='btnPeticionar']",
        "button:has-text('Gravar')",
        "button:has-text('Confirmar')",
        "button:has-text('Salvar')",
    ]

    btn_found = False
    for sel in sign_selectors:
        try:
            btn = page.locator(sel)
            if await btn.count() > 0:
                logger.info("%s Botão de assinar/protocolar encontrado: %s", tag, sel)
                await btn.first.click()
                btn_found = True
                logger.info("%s Clicado! Aguardando resposta do tribunal...", tag)
                await asyncio.sleep(5)

                # Verificar se apareceu dialog de confirmação
                confirm_btn = page.locator(
                    "button:has-text('Sim'), button:has-text('Confirmar'), button:has-text('OK')"
                )
                if await confirm_btn.count() > 0:
                    logger.info("%s Confirmação detectada, clicando...", tag)
                    await confirm_btn.first.click()
                    await asyncio.sleep(3)

                break
        except Exception as e:
            logger.debug("%s Botão %s falhou: %s", tag, sel, e)

    if not btn_found:
        logger.error("%s Nenhum botão de assinar/protocolar encontrado!", tag)
        return None

    # 2. Aguardar resultado e capturar protocolo
    logger.info("%s Aguardando resultado do tribunal (até 30s)...", tag)
    await asyncio.sleep(5)

    body_text = await page.inner_text("body")
    logger.debug("%s Texto pós-envio (2000 chars): %s", tag, body_text[:2000])

    # Padrões para capturar número de protocolo
    protocolo_patterns = [
        r"[Pp]rotocolo\s*(?::|nº|n\.?º?|número)?\s*(\d[\d./-]+\d)",
        r"[Pp]rotocolad[ao]\s*(?:com\s+(?:o\s+)?(?:número|nº))?\s*(\d[\d./-]+\d)",
        r"[Rr]ecibo\s*(?::|nº|n\.?º?)?\s*(\d[\d./-]+\d)",
        r"(?:nº|número)\s*(?:do\s+)?protocolo\s*:\s*(\d[\d./-]+\d)",
    ]

    for pattern in protocolo_patterns:
        match = re.search(pattern, body_text)
        if match:
            protocolo = match.group(1)
            logger.info("%s PROTOCOLO CAPTURADO: %s (padrão: %s)", tag, protocolo, pattern)
            return protocolo

    # Verificar se houve sucesso mesmo sem capturar protocolo
    success_keywords = ["sucesso", "protocolad", "recebid", "registrad"]
    if any(kw in body_text.lower() for kw in success_keywords):
        logger.warning("%s Sucesso detectado mas protocolo não extraído do texto", tag)
        return "SUCESSO_SEM_NUMERO"

    # Verificar se houve erro
    error_keywords = ["erro", "falha", "rejeitad", "inválid", "negad"]
    if any(kw in body_text.lower() for kw in error_keywords):
        logger.error("%s Erro detectado no envio! Texto: %s", tag, body_text[:1000])
        return None

    return None

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
from urllib.parse import parse_qs, unquote, urlparse

import pyotp
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
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

# Mapa CNJ J+TT → código interno do tribunal
# Formato CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO
_CNJ_J4 = {  # Justiça Federal (J=4)
    "01": "trf1",
    "02": "trf2",
    "03": "trf3",
    "04": "trf4",
    "05": "trf5",
    "06": "trf6",
}
_CNJ_J8 = {  # TJ estadual (J=8) — estado = código IBGE da UF
    "01": "tjac", "02": "tjal", "03": "tjap", "04": "tjam",
    "05": "tjba", "06": "tjce", "07": "tjdft", "08": "tjes",
    "09": "tjgo", "10": "tjma", "11": "tjmt", "12": "tjms",
    "13": "tjmg", "14": "tjpa", "15": "tjpb", "16": "tjpr",
    "17": "tjpe", "18": "tjpi", "19": "tjrj", "20": "tjrn",
    "21": "tjrs", "22": "tjro", "23": "tjrr", "24": "tjsc",
    "25": "tjsp", "26": "tjse", "27": "tjto",
}

_CNJ_PROCESSO_RE = re.compile(
    r'^\d{7}-\d{2}\.\d{4}\.(\d)\.(\d{2})\.\d{4}$'
)


def tribunal_from_processo(numero: str) -> str | None:
    """Infere o código do tribunal a partir do número CNJ do processo.

    Formato: NNNNNNN-DD.AAAA.J.TT.OOOO
    Exemplos:
      '1014980-12.2025.4.01.4100' → 'trf1'
      '0001234-56.2025.8.06.0001' → 'tjce'

    Retorna None se o número não corresponder ao padrão ou tribunal desconhecido.
    """
    m = _CNJ_PROCESSO_RE.match(numero.strip())
    if not m:
        return None
    j, tt = m.group(1), m.group(2)
    if j == "4":
        return _CNJ_J4.get(tt)
    if j == "8":
        return _CNJ_J8.get(tt)
    return None


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
    totp_algorithm: Optional[str] = None,
    totp_digits: Optional[int] = None,
    totp_period: Optional[int] = None,
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
        totp_algorithm: Algoritmo TOTP (SHA1, SHA256, SHA512). Padrão: SHA1
        totp_digits: Número de dígitos (6 ou 8). Padrão: 6
        totp_period: Período em segundos (30 ou 60). Padrão: 30

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

        # Aguardar redirect Keycloak → PJe dashboard (ou TOTP page)
        # NOTA: Os padrões de domínio PJe usam âncora ^ para não bater com
        # redirect_uri em query-strings de URLs SSO (ex: pje1g.trf em ?redirect_uri=)
        logger.info("%s Aguardando redirect SSO → PJe ou TOTP (até 30s)...", tag)
        t0 = time.monotonic()
        try:
            await page.wait_for_url(
                re.compile(r"(^https?://pje1g\.trf|^https?://pje\.jf|^https?://pje\.tj|login-actions)"),
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

        # Se ainda estamos no openid-connect/auth, esperar mais um pouco
        # (o redirect pode estar em andamento)
        current_url = page.url
        if "openid-connect/auth" in current_url:
            logger.info("%s Ainda em openid-connect/auth, aguardando redirect final...", tag)
            try:
                await page.wait_for_url(
                    re.compile(r"(^https?://pje1g\.trf|^https?://pje\.jf|^https?://pje\.tj|login-actions)"),
                    timeout=15_000,
                )
            except PlaywrightTimeout:
                pass
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10_000)
            except Exception:
                pass
            await asyncio.sleep(2)

        # Verificar se o SSO retornou erro inesperado
        current_url = page.url
        logger.info("%s Pós-form-submit URL: %s", tag, current_url)
        if "login-actions" in current_url:
            body_check = await page.inner_text("body")
            if "erro inesperado" in body_check.lower():
                logger.warning(
                    "%s SSO retornou 'Erro inesperado'. Tentando recarregar login...",
                    tag,
                )
                s = await _screenshot(page, "02a_sso_error", tag)
                if s:
                    screenshots.append(s)
                # Retry: navegar de volta ao login e tentar novamente
                await page.goto(login_url, wait_until="domcontentloaded", timeout=60_000)
                await asyncio.sleep(3)

                # Re-extract challenge
                onclick_data2 = await page.evaluate("""() => {
                    const allElems = document.querySelectorAll('[onclick]');
                    for (const el of allElems) {
                        const oc = el.getAttribute('onclick') || '';
                        const m = oc.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
                        if (m) return {codigoSeguranca: m[1], mensagem: m[2]};
                    }
                    return null;
                }""")

                if onclick_data2:
                    logger.info("%s Retry: new nonce=%s", tag, onclick_data2["mensagem"])
                    token_uuid2 = str(uuid_mod.uuid4())
                    assinatura_b64_2 = _sign_md5_rsa(_private_key, onclick_data2["mensagem"])
                    sso_payload2 = json.dumps({
                        "certChain": _certchain_b64,
                        "uuid": token_uuid2,
                        "mensagem": onclick_data2["mensagem"],
                        "assinatura": assinatura_b64_2,
                    })
                    rest_result2 = await page.evaluate(
                        """async ([url, payloadStr]) => {
                            try {
                                const resp = await fetch(url, {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: payloadStr,
                                    credentials: 'include',
                                });
                                return {status: resp.status};
                            } catch (e) { return {error: e.message}; }
                        }""",
                        [pjeoffice_endpoint, sso_payload2],
                    )
                    logger.info("%s Retry pjeoffice-rest: %s", tag, rest_result2)

                    if rest_result2.get("status") in (200, 204):
                        await page.evaluate(
                            """([uuid]) => {
                                const c = document.getElementById('pjeoffice-code');
                                if (c) c.value = uuid;
                                const f = document.getElementById('loginForm');
                                if (!f) return;
                                const b = document.createElement('input');
                                b.type = 'hidden'; b.name = 'login-pje-office';
                                b.value = 'CERTIFICADO DIGITAL';
                                f.appendChild(b);
                                f.submit();
                            }""",
                            [token_uuid2],
                        )
                        try:
                            await page.wait_for_url(
                                re.compile(r"(^https?://pje1g\.trf|^https?://pje\.jf|^https?://pje\.tj|login-actions)"),
                                timeout=30_000,
                            )
                        except PlaywrightTimeout:
                            pass
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
                        except Exception:
                            pass
                        await asyncio.sleep(2)
                        logger.info("%s Retry pós-submit URL: %s", tag, page.url)

        # ── Step 6b: Verificar e tratar página de TOTP ──
        # Keycloak pode exigir TOTP como segundo fator após certificado
        # Retry loop: a página pode ainda estar carregando/redirectionando
        otp_input = page.locator("input[name='otp'], input[id='otp']")
        otp_found = await otp_input.count() > 0
        if not otp_found and "login-actions" in page.url:
            # Estamos em login-actions mas OTP input ainda não apareceu — esperar
            logger.info("%s Em login-actions mas OTP input não encontrado, aguardando...", tag)
            for _retry in range(5):
                await asyncio.sleep(1)
                otp_found = await otp_input.count() > 0
                if otp_found:
                    break
        if otp_found:
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

            # Gerar código TOTP atual (com parâmetros do otpauth URI se disponíveis)
            algo = (totp_algorithm or "SHA1").lower()
            digits = totp_digits or 6
            period = totp_period or 30
            totp_obj = pyotp.TOTP(
                totp_secret.strip().upper(),
                digest=algo,
                digits=digits,
                interval=period,
            )
            totp_code = totp_obj.now()
            logger.info(
                "%s Gerando código TOTP: %s (algo=%s, digits=%d, period=%ds, secret_len=%d)",
                tag, totp_code, algo.upper(), digits, period, len(totp_secret),
            )

            await otp_input.first.fill(totp_code)
            await asyncio.sleep(0.3)

            # Clicar no botão validar/confirmar OTP via JS evaluate
            # (Playwright .click() pode causar timeout no PJe — usar JS direto)
            submit_btn = page.locator("input[id='kc-login']")
            if await submit_btn.count() > 0:
                await submit_btn.first.evaluate("el => el.click()")
            else:
                # Fallback para outros seletores
                submit_btn2 = page.locator("input[name='login'], button[type='submit']")
                if await submit_btn2.count() > 0:
                    await submit_btn2.first.evaluate("el => el.click()")
                else:
                    await otp_input.first.press("Enter")

            logger.info("%s TOTP submetido, aguardando redirect (até 30s)...", tag)
            try:
                await page.wait_for_url(
                    re.compile(r"(^https?://pje1g\.trf|^https?://pje\.jf|^https?://pje\.tj)"),
                    timeout=30_000,
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
        current_url = page.url

        # Verificação 1: URL dentro da área autenticada do tribunal
        # (ex: TJCE cai em /QuadroAviso/... após login — não contém keywords TRF1)
        is_logged_in_by_url = base_url and current_url.startswith(base_url)

        # Verificação 2: Keywords do painel do advogado por tribunal
        # TRF1/TRF3/TRF5/TRF6 → painel clássico com expedientes/peticionar
        # TJCE e TJs estaduais → cai no "Quadro de avisos" (QuadroAviso)
        body_lower = body_text.lower()
        is_logged_in_by_text = any(kw in body_lower for kw in [
            # TRF1/TRFx — painel do advogado
            "expedientes", "peticionar", "painel do advogado",
            "novo processo", "consulta processos", "meu painel",
            # TJs estaduais (ex: TJCE) — quadro de avisos pós-login
            "quadro de avisos", "último acesso em", "audiências e sessões",
            "abrir menu",
        ])

        is_logged_in = is_logged_in_by_url or is_logged_in_by_text

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

        # ── Step 8: Navegar até Petição Avulsa e buscar processo ──
        logger.info("%s Navegando até Petição Avulsa para processo %s...", tag, numero_processo)

        popup_url = await _navegar_para_processo(page, base_url, numero_processo, tag)

        s = await _screenshot(page, "03_processo_busca", tag)
        if s:
            screenshots.append(s)

        if not popup_url:
            logger.error(
                "%s Processo %s não encontrado ou popup URL não capturada. URL=%s",
                tag, numero_processo, page.url,
            )
            return PeticionamentoResult(
                sucesso=False,
                mensagem=f"Processo {numero_processo} não encontrado na Petição Avulsa.",
                screenshots=screenshots,
            )

        logger.info("%s ✓ Processo localizado! Popup URL: %s", tag, popup_url[:150])

        # ── Step 9: Abrir popup de peticionamento (peticaoPopUp.seam) ──
        logger.info("%s Abrindo formulário de peticionamento...", tag)

        form_ok = await _abrir_popup_peticao(page, popup_url, tag)

        s = await _screenshot(page, "04_popup_peticao", tag)
        if s:
            screenshots.append(s)

        if not form_ok:
            logger.error("%s Formulário de peticionamento não encontrado", tag)
            return PeticionamentoResult(
                sucesso=False,
                mensagem="Formulário de peticionamento não encontrado no popup.",
                screenshots=screenshots,
            )

        logger.info("%s ✓ Formulário de peticionamento aberto!", tag)

        # ── Step 10: Preencher tipo + descrição + selecionar modo PDF ──
        logger.info("%s Preenchendo formulário: tipo=%s descricao=%s", tag, tipo_documento, descricao[:80])

        await _preencher_formulario_peticao(page, tipo_documento, descricao, tag)

        s = await _screenshot(page, "05_formulario_preenchido", tag)
        if s:
            screenshots.append(s)

        # ── Step 11: Upload PDF via RichFaces rich:fileUpload ──
        logger.info("%s Fazendo upload do PDF via RichFaces (%d bytes)...", tag, len(pdf_bytes))

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

        logger.info("%s ✓ PDF uploaded via RichFaces!", tag)

        # ── Step 11b: Aguardar classificação + habilitação do btn-assinador ──
        logger.info("%s Aguardando classificação do documento...", tag)

        add_ok = await _adicionar_documento(page, tag)

        s = await _screenshot(page, "06b_documento_classificado", tag)
        if s:
            screenshots.append(s)

        if not add_ok:
            logger.warning("%s btn-assinador não habilitou — tentando prosseguir", tag)

        # ── Step 12: Assinar e protocolar via PJeOffice ──
        logger.info("%s Assinando e enviando petição...", tag)

        protocolo = await _assinar_e_enviar(
            page, _private_key, _certchain_b64, tag,
            pdf_bytes=pdf_bytes,
            cert_der_b64=base64.b64encode(_cert_obj.public_bytes(Encoding.DER)).decode("ascii"),
        )

        s = await _screenshot(page, "07_enviado", tag)
        if s:
            screenshots.append(s)

        if protocolo == "SUCESSO_SEM_NUMERO":
            # Petição avulsa: sucesso sem número de protocolo (comportamento normal)
            logger.info(
                "%s ══════════ PETIÇÃO AVULSA ENVIADA ══════════ (sem protocolo)",
                tag,
            )
            return PeticionamentoResult(
                sucesso=True,
                mensagem="Petição avulsa enviada com sucesso!",
                numero_protocolo=None,
                screenshots=screenshots,
            )
        elif protocolo:
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
# Sub-steps: cada etapa do fluxo PJe (Petição Avulsa)
# Fluxo validado: peticaoavulsa.seam → Pesquisar → openPopUp →
#   peticaoPopUp.seam → preencher form → upload PDF → Adicionar → Assinar
# ──────────────────────────────────────────────────────────────────


def _parse_numero_processo(numero: str) -> dict:
    """Parse 'NNNNNNN-DD.AAAA.J.TT.OOOO' into field values for PJe form.

    Aceita tanto o formato formatado (com hífen/pontos) quanto 20 dígitos puros.
    """
    raw = numero.strip()
    # Se vier só dígitos (20), aplica máscara automaticamente
    digits_only = re.sub(r"\D", "", raw)
    if re.fullmatch(r"\d{20}", digits_only) and not re.search(r"[-\.]", raw):
        raw = f"{digits_only[:7]}-{digits_only[7:9]}.{digits_only[9:13]}.{digits_only[13:14]}.{digits_only[14:16]}.{digits_only[16:20]}"
    m = re.match(
        r"(\d{7})-(\d{2})\.(\d{4})\.(\d{1,2})\.(\d{2})\.(\d{4})",
        raw,
    )
    if not m:
        raise ValueError(f"Número de processo inválido: {numero}")
    return {
        "sequencial": m.group(1),
        "digito": m.group(2),
        "ano": m.group(3),
        "ramo": m.group(4),
        "tribunal": m.group(5),
        "orgao": m.group(6),
    }


async def _navegar_para_processo(
    page: Page, base_url: str, numero_processo: str, tag: str,
) -> Optional[str]:
    """Navigate to Petição Avulsa, search process, capture popup URL.

    Flow:
      1. Navigate to peticaoavulsa.seam
      2. Fill process number fields (sequencial, digito, ano, ramo, tribunal, orgao)
      3. Click Pesquisar
      4. Override window.openPopUp(), click idPet link
      5. Capture the popup URL (peticaoPopUp.seam?idProcesso=X&ca=Y)

    Returns: popup URL string or None on failure.
    """
    # Parse process number into form fields
    try:
        proc = _parse_numero_processo(numero_processo)
    except ValueError as e:
        logger.error("%s %s", tag, e)
        return None

    logger.info("%s Parsed processo: %s", tag, proc)

    # Navigate to Petição Avulsa page
    peticao_url = f"{base_url}/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam"
    logger.info("%s Navegando para Petição Avulsa: %s", tag, peticao_url)

    await page.goto(peticao_url, wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(3)

    # Fill process number fields via JS (ensures correct events)
    logger.info("%s Preenchendo número do processo...", tag)
    await page.evaluate(
        """(p) => {
            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) {
                    el.value = val;
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
            };
            set('fPP:numeroProcesso:numeroSequencial', p.sequencial);
            set('fPP:numeroProcesso:numeroDigitoVerificador', p.digito);
            set('fPP:numeroProcesso:Ano', p.ano);
            set('fPP:numeroProcesso:ramoJustica', p.ramo);
            set('fPP:numeroProcesso:respectivoTribunal', p.tribunal);
            set('fPP:numeroProcesso:NumeroOrgaoJustica', p.orgao);
        }""",
        proc,
    )
    await asyncio.sleep(1)

    # Click Pesquisar button
    logger.info("%s Clicando Pesquisar...", tag)
    await page.evaluate(
        "() => document.getElementById('fPP:searchProcessosPeticao')?.click()"
    )
    # Wait for A4J response (processo search can be slow)
    await asyncio.sleep(8)

    # Check results
    body = await page.inner_text("body")
    if "resultados encontrados" not in body.lower():
        logger.error(
            "%s Processo não encontrado na pesquisa! Body (1500): %s",
            tag, body[:1500],
        )
        return None

    logger.info("%s Processo encontrado na pesquisa!", tag)

    # Override openPopUp() BEFORE clicking to capture the final assembled URL.
    # PJe A4J response builds URL in JS: var link="...pje" + "/Processo/..." ; link += "id&ca=...";
    # then calls openPopUp('Peticionamento', link). We intercept it.
    logger.info("%s Capturando URL do popup via openPopUp override...", tag)
    popup_url = await page.evaluate(
        """() => {
            return new Promise((resolve) => {
                // PJe calls openPopUp('Peticionamento', link) after A4J response
                window.openPopUp = function(title, url) {
                    resolve(url);
                };
                // Fallback: intercept window.open
                const origWinOpen = window.open;
                window.open = function(url) {
                    resolve(url);
                    return null;
                };
                const link = document.querySelector('a[id*="idPet"]');
                if (link) link.click();
                else resolve(null);
                setTimeout(() => resolve(null), 15000);
            });
        }"""
    )

    if popup_url:
        logger.info("%s Popup URL capturada: %s", tag, popup_url[:200])
    else:
        logger.error("%s Falha ao capturar popup URL (openPopUp não chamado)", tag)

    return popup_url


async def _abrir_popup_peticao(page: Page, popup_url: str, tag: str) -> bool:
    """Navigate to the petition popup page (peticaoPopUp.seam).

    Dismisses PJeOffice modals if present, verifies the form is accessible.
    """
    logger.info("%s Navegando para popup de peticionamento...", tag)
    await page.goto(popup_url, wait_until="domcontentloaded", timeout=30_000)
    await asyncio.sleep(5)

    # Dismiss any modal (PJeOffice indisponível)
    await page.evaluate(
        """() => {
            document.querySelectorAll(
                '[data-dismiss="modal"], .modal .close, .rich-mpnl-controls .close'
            ).forEach(b => b.click());
            const s = document.getElementById('mpPJeOfficeIndisponivelOpenedState');
            if (s) s.value = '';
        }"""
    )
    await asyncio.sleep(2)

    # Verify we're on the petition form
    title = await page.title()
    logger.info("%s Popup page title: %s | URL: %s", tag, title, page.url)

    # Check for the tipo de documento select (primary form indicator)
    has_form = await page.evaluate(
        """() => {
            const sel = document.getElementById('cbTDDecoration:cbTD');
            const desc = document.getElementById('ipDescDecoration:ipDesc');
            return {
                hasTipoSelect: !!sel,
                hasDescInput: !!desc,
                tipoVisible: sel ? sel.offsetParent !== null : false,
                descVisible: desc ? desc.offsetParent !== null : false,
            };
        }"""
    )

    logger.info("%s Form check: %s", tag, has_form)

    if has_form.get("hasTipoSelect"):
        logger.info("%s ✓ Formulário de peticionamento detectado!", tag)
        return True

    # If form not directly visible, try clicking "Juntar documentos" button
    # (some PJe versions open a process detail page first)
    logger.info(
        "%s Formulário não visível diretamente, procurando botão 'Juntar documentos'...",
        tag,
    )
    clicked = await page.evaluate(
        """() => {
            const all = document.querySelectorAll('a, button, i, span');
            for (const el of all) {
                const title = (el.title || el.getAttribute('data-original-title') || '')
                    .toLowerCase();
                if (title.includes('juntar')) {
                    el.click();
                    return 'clicked: ' + (el.id || title);
                }
            }
            for (const el of all) {
                const text = (el.textContent || '').trim().toLowerCase();
                if (text.includes('juntar documento')) {
                    el.click();
                    return 'clicked: ' + (el.id || text);
                }
            }
            return null;
        }"""
    )

    if clicked:
        logger.info("%s %s", tag, clicked)
        await asyncio.sleep(5)

        # Re-check form
        has_form_after = await page.evaluate(
            "() => !!document.getElementById('cbTDDecoration:cbTD')"
        )
        if has_form_after:
            logger.info("%s ✓ Formulário visível após Juntar documentos!", tag)
            return True

    logger.error("%s Formulário de peticionamento não encontrado!", tag)
    return False


async def _preencher_formulario_peticao(
    page: Page, tipo_documento: str, descricao: str, tag: str,
) -> None:
    """Fill the petition form: tipo de documento, descrição, select PDF mode.

    Field IDs (discovered from real PJe TRF1):
      - Tipo de documento: select#cbTDDecoration:cbTD (82 options)
      - Descrição: input#ipDescDecoration:ipDesc
      - Modo: radio#raTipoDocPrincipal:0 (Arquivo PDF) / :1 (Editor HTML)
    """
    # 1. Select tipo de documento — using Playwright native select_option
    # This triggers real browser events that JSF/RichFaces A4J can intercept
    logger.info("%s Selecionando tipo de documento: '%s'", tag, tipo_documento)

    tipo_select = page.locator("select[id='cbTDDecoration:cbTD']")
    if await tipo_select.count() == 0:
        # Fallback: try partial ID match
        tipo_select = page.locator("select[id*='cbTD']")

    selected_label = None
    if await tipo_select.count() > 0:
        # First, find the best matching option label
        match_result = await page.evaluate(
            """(tipo) => {
                const sel = document.getElementById('cbTDDecoration:cbTD');
                if (!sel) return null;
                const tipoLower = tipo.toLowerCase();

                // Exact case-sensitive
                for (const opt of sel.options) {
                    if (opt.text.trim() === tipo)
                        return {label: opt.text.trim(), value: opt.value};
                }
                // Exact case-insensitive
                for (const opt of sel.options) {
                    if (opt.text.trim().toLowerCase() === tipoLower)
                        return {label: opt.text.trim(), value: opt.value};
                }
                // Partial — shortest match
                let best = null, bestLen = 99999;
                for (const opt of sel.options) {
                    const t = opt.text.trim();
                    if (t.toLowerCase().includes(tipoLower) && t.length < bestLen) {
                        best = {label: t, value: opt.value};
                        bestLen = t.length;
                    }
                }
                if (best) return best;
                // Fallback
                for (const opt of sel.options) {
                    const t = opt.text.trim().toLowerCase();
                    if (t === 'petição intercorrente' || t === 'outras peças')
                        return {label: opt.text.trim(), value: opt.value, fallback: true};
                }
                return null;
            }""",
            tipo_documento,
        )

        if match_result:
            selected_label = match_result["label"]
            logger.info(
                "%s Tipo encontrado: '%s' (value=%s%s)",
                tag, selected_label, match_result["value"],
                " FALLBACK" if match_result.get("fallback") else "",
            )
            # Use Playwright's native select_option — fires real browser change events
            # that JSF/A4J intercepts to update server-side component state
            try:
                await tipo_select.first.select_option(label=selected_label)
                logger.info("%s Tipo selecionado via Playwright select_option!", tag)
            except Exception as e:
                logger.warning("%s Playwright select_option falhou: %s — tentando JS", tag, e)
                # Fallback to JS + manual A4J trigger
                await page.evaluate(
                    """(val) => {
                        const sel = document.getElementById('cbTDDecoration:cbTD');
                        if (sel) {
                            sel.value = val;
                            sel.dispatchEvent(new Event('change', {bubbles: true}));
                            if (sel.onchange) sel.onchange();
                        }
                    }""",
                    match_result["value"],
                )
        else:
            logger.error("%s Nenhuma opção encontrada para '%s'", tag, tipo_documento)
    else:
        logger.error("%s Select de tipo de documento não encontrado!", tag)

    # Wait for A4J to process the tipo selection server-side
    await asyncio.sleep(3)

    # 2. Fill description
    if descricao:
        logger.info("%s Preenchendo descrição: %s", tag, descricao[:80])
        desc_filled = await page.evaluate(
            """(desc) => {
                const el = document.getElementById('ipDescDecoration:ipDesc');
                if (!el) return false;
                el.value = desc;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }""",
            descricao[:200],
        )
        if desc_filled:
            logger.info("%s Descrição preenchida!", tag)
        else:
            logger.warning("%s Campo descrição (ipDescDecoration:ipDesc) não encontrado", tag)

    await human_delay(0.3, 0.6)

    # 3. Click "Arquivo PDF" radio button using Playwright native click
    # This fires proper browser events for JSF/A4J to process server-side
    logger.info("%s Selecionando modo 'Arquivo PDF'...", tag)
    pdf_radio = page.locator("input[id='raTipoDocPrincipal:0']")
    if await pdf_radio.count() > 0:
        await pdf_radio.first.click()
        logger.info("%s Radio 'Arquivo PDF' clicado via Playwright!", tag)
    else:
        # Fallback: JS click
        await page.evaluate(
            """() => {
                const r = document.getElementById('raTipoDocPrincipal:0');
                if (r) {
                    r.checked = true;
                    r.dispatchEvent(new Event('change', {bubbles: true}));
                    r.click();
                }
            }"""
        )
        logger.info("%s Radio 'Arquivo PDF' selecionado via JS fallback", tag)

    # Wait for A4J to update the form after radio change
    # (switches from TinyMCE editor to file upload mode — can take several seconds)
    await asyncio.sleep(5)

    # Verify the file upload area (dropzone) appeared
    has_upload = await page.evaluate(
        """() => {
            const fi = document.querySelector('input[type="file"]');
            const dz = document.querySelector('.dropzone');
            return {hasFileInput: !!fi, hasDropzone: !!dz};
        }"""
    )
    logger.info("%s Upload area check: %s", tag, has_upload)
    if not has_upload.get("hasFileInput") and not has_upload.get("hasDropzone"):
        logger.warning("%s Upload area não visível — esperando mais...", tag)
        await asyncio.sleep(5)

    # Log form state for debug
    form_state = await page.evaluate(
        """() => {
            const sel = document.getElementById('cbTDDecoration:cbTD');
            const desc = document.getElementById('ipDescDecoration:ipDesc');
            const r0 = document.getElementById('raTipoDocPrincipal:0');
            const r1 = document.getElementById('raTipoDocPrincipal:1');
            return {
                tipo: sel ? sel.options[sel.selectedIndex]?.text : null,
                descricao: desc ? desc.value : null,
                radioPdf: r0 ? r0.checked : null,
                radioEditor: r1 ? r1.checked : null,
            };
        }"""
    )
    logger.info("%s Estado do formulário: %s", tag, form_state)


async def _upload_pdf(page: Page, pdf_path: str, tag: str) -> bool:
    """Upload PDF via RichFaces rich:fileUpload component.

    O PJe usa o componente RichFaces rich:fileUpload (NÃO Dropzone.js).
    O input hidden relevante tem id contendo 'uploadDocumentoPrincipal'.
    Ao setar o arquivo via set_input_files(), disparamos o onchange que
    faz o RichFaces componente iniciar o upload AJAX automaticamente.
    Após o upload o documento aparece como "Enviado" na lista.
    """
    logger.info("%s Upload PDF via RichFaces rich:fileUpload...", tag)

    # 1. Encontrar e preparar o input[type=file] do RichFaces
    #    ID real: uploadDocumentoPrincipalDecoration:uploadDocumentoPrincipal:file
    file_input_info = await page.evaluate(
        """() => {
            const inputs = document.querySelectorAll('input[type="file"]');
            const result = [];
            inputs.forEach(i => {
                result.push({
                    id: i.id,
                    name: i.name,
                    className: i.className,
                    display: getComputedStyle(i).display,
                });
            });
            return result;
        }"""
    )
    logger.info("%s Inputs type=file encontrados: %s", tag, file_input_info)

    # Tornar o input visível para Playwright poder interagir
    await page.evaluate(
        """() => {
            document.querySelectorAll('input[type="file"]').forEach(i => {
                i.style.display = 'block';
                i.style.visibility = 'visible';
                i.style.opacity = '1';
                i.style.position = 'relative';
                i.style.width = '200px';
                i.style.height = '30px';
                i.style.zIndex = '9999';
                i.removeAttribute('disabled');
            });
        }"""
    )
    await asyncio.sleep(0.5)

    # 2. Selecionar o input correto (priorizar o do RichFaces uploadDocumentoPrincipal)
    richfaces_input = page.locator(
        "input[type='file'][id*='uploadDocumentoPrincipal']"
    )
    generic_input = page.locator("input[type='file']")

    target_input = None
    if await richfaces_input.count() > 0:
        target_input = richfaces_input.first
        logger.info("%s Usando RichFaces input (uploadDocumentoPrincipal)", tag)
    elif await generic_input.count() > 0:
        target_input = generic_input.first
        logger.info("%s Usando input[type=file] genérico (fallback)", tag)
    else:
        logger.error("%s Nenhum input[type='file'] encontrado na página!", tag)
        return False

    # 3. Setar o arquivo — dispara onchange → RichFaces processa upload AJAX
    try:
        await target_input.set_input_files(pdf_path)
        logger.info("%s set_input_files OK: %s", tag, pdf_path)
    except Exception as e:
        logger.error("%s set_input_files falhou: %s", tag, e)
        return False

    # 4. Disparar o upload RichFaces manualmente via JS (backup para garantir)
    await page.evaluate(
        """() => {
            // Tentar acionar o componente RichFaces de upload
            const fileInput = document.querySelector(
                "input[type='file'][id*='uploadDocumentoPrincipal']"
            );
            if (fileInput) {
                // Disparar evento change manualmente
                fileInput.dispatchEvent(new Event('change', {bubbles: true}));
            }
            // Tentar via componente RichFaces global
            try {
                const compId = 'uploadDocumentoPrincipalDecoration:uploadDocumentoPrincipal';
                const comp = window.$(compId);
                if (comp && comp.component && comp.component.add) {
                    comp.component.add(fileInput);
                }
            } catch(e) {
                console.log('RichFaces component trigger fallback:', e);
            }
        }"""
    )

    # 5. Aguardar RichFaces processar o upload (olhar por "Enviado" ou ".pdf")
    logger.info("%s Aguardando RichFaces processar upload...", tag)
    upload_confirmed = False
    for attempt in range(20):  # até ~20s
        await asyncio.sleep(1)
        state = await page.evaluate(
            """() => {
                const body = document.body.textContent || '';
                const bodyLower = body.toLowerCase();
                // RichFaces mostra "Enviado" quando upload completa
                const hasEnviado = bodyLower.includes('enviado');
                const hasPdf = body.includes('.pdf');
                // Verificar se documento apareceu na tabela de documentos
                const docTable = document.querySelector(
                    '[id*="tabelaDocumentos"], [id*="documentoList"], table.rich-table'
                );
                const hasDocInTable = docTable ? docTable.textContent.includes('.pdf') : false;
                // Verificar se o upload do RichFaces mostra "Uploaded"
                const uploadList = document.querySelector('.rich-fileupload-list-decor');
                const hasUploadItem = uploadList ? uploadList.children.length > 0 : false;
                // Dropzone fallback check
                const dzSuccess = !!document.querySelector('.dz-success, .dz-complete');
                return {
                    hasEnviado, hasPdf, hasDocInTable, hasUploadItem, dzSuccess,
                };
            }"""
        )
        if any([
            state.get("hasEnviado"),
            state.get("hasDocInTable"),
            state.get("hasUploadItem"),
            state.get("dzSuccess"),
        ]):
            upload_confirmed = True
            logger.info("%s Upload RichFaces confirmado (attempt=%d): %s", tag, attempt, state)
            break
        if state.get("hasPdf") and attempt >= 3:
            upload_confirmed = True
            logger.info("%s PDF detectado no body (attempt=%d): %s", tag, attempt, state)
            break
        if attempt % 5 == 0:
            logger.info("%s Aguardando upload... (attempt=%d): %s", tag, attempt, state)

    if not upload_confirmed:
        logger.warning("%s Upload não confirmado em 20s — continuando mesmo assim", tag)

    return True


async def _adicionar_documento(page: Page, tag: str) -> bool:
    """Aguarda que o documento seja classificado e btn-assinador habilitado.

    Após o upload via RichFaces (feito em _upload_pdf), o PJe processa
    a classificação do documento via callback A4J. Quando o upload via
    RichFaces é feito corretamente, o btn-assinador habilita rapidamente
    (observado no teste manual: habilita imediatamente). Mantemos fallback
    via atualizaApplet(true) por segurança.
    """
    logger.info("%s Aguardando classificação do documento e habilitação do btn-assinador...", tag)

    # Primeiro verificar se o documento aparece na página
    doc_check = await page.evaluate(
        """() => {
            const body = document.body.textContent || '';
            return {
                bodyHasPdf: body.includes('.pdf'),
                bodyHasAnexo: body.toLowerCase().includes('anexo'),
            };
        }"""
    )
    logger.info("%s Documento na página: %s", tag, doc_check)

    # Aguardar até 30s para btn-assinador ser habilitado (classificação A4J)
    btn_enabled = False
    for attempt in range(30):
        btn_state = await page.evaluate(
            """() => {
                const btn = document.getElementById('btn-assinador');
                if (!btn) return {found: false};
                return {
                    found: true,
                    disabled: btn.disabled || btn.hasAttribute('disabled'),
                    value: btn.value || btn.textContent || '',
                    onclick: (btn.getAttribute('onclick') || '').substring(0, 100),
                };
            }"""
        )
        if btn_state.get("found") and not btn_state.get("disabled"):
            btn_enabled = True
            logger.info("%s btn-assinador HABILITADO (attempt=%d): %s", tag, attempt, btn_state)
            break
        if attempt % 5 == 0:
            logger.info("%s btn-assinador ainda desabilitado (attempt=%d): %s", tag, attempt, btn_state)
        await asyncio.sleep(1)

    if not btn_enabled:
        # Fallback: forçar habilitação via JS (atualizaApplet)
        logger.warning("%s btn-assinador não habilitou em 30s — forçando via atualizaApplet(true)", tag)
        await page.evaluate(
            """() => {
                // Tentar chamar a função nativa do PJe
                if (typeof atualizaApplet === 'function') {
                    atualizaApplet(true);
                    return;
                }
                // Fallback manual
                const btn = document.getElementById('btn-assinador');
                if (btn) {
                    btn.removeAttribute('disabled');
                    btn.value = 'Assinar documento(s)';
                }
            }"""
        )
        await asyncio.sleep(2)

        # Verificar novamente
        btn_state = await page.evaluate(
            """() => {
                const btn = document.getElementById('btn-assinador');
                return btn ? {disabled: btn.disabled, value: btn.value} : {found: false};
            }"""
        )
        btn_enabled = btn_state.get("found", True) and not btn_state.get("disabled", True)
        logger.info("%s btn-assinador após forçar: enabled=%s state=%s", tag, btn_enabled, btn_state)

    return btn_enabled


async def _assinar_e_enviar(
    page: Page, private_key, certchain_b64: str, tag: str,
    pdf_bytes: Optional[bytes] = None,
    cert_der_b64: str = "",
) -> Optional[str]:
    """Assina e submete a petição. Retorna protocolo ou 'SUCESSO_SEM_NUMERO'.

    Documentação completa: docs/PJEOFFICE_INTEGRACAO.md

    ═══════════════════════════════════════════════════════════════════════
    COMO O PJe SE COMUNICA COM O PJEOFFICE
    ═══════════════════════════════════════════════════════════════════════
    O PJe JS usa:
        const img = new Image();
        img.onload = () => { /* sucesso → A4J submit */ };
        img.onerror = () => { /* falha → modal "PJeOffice Indisponível" */ };
        img.src = "http://localhost:8800/pjeOffice/requisicao/?r=<JSON>";

    O parâmetro `r` contém:
        {
          "aplicacao": "PJe",
          "servidor": "https://pje1g.trf1.jus.br",
          "tarefaId": "cnj.assinadorHash",
          "tarefa": "{\"mensagem\":\"<HASH_BASE64>\",\"enviarPara\":\"/pjeoffice-rest\",\"token\":\"<UUID>\"}"
        }

    ═══════════════════════════════════════════════════════════════════════
    POR QUE page.route().fulfill() NÃO FUNCIONA AQUI
    ═══════════════════════════════════════════════════════════════════════
    Interceptar no nível de rede com page.route() responde o HTTP request,
    mas o Chromium headless NÃO dispara img.onload para imagens dinâmicas
    interceptadas assim. Resultado: sempre cai no modal "PJeOffice Indisponível".

    ═══════════════════════════════════════════════════════════════════════
    SOLUÇÃO: MONKEY-PATCH NO NÍVEL JS (antes da rede)
    ═══════════════════════════════════════════════════════════════════════
    Patcheamos HTMLImageElement.prototype.src SETTER via page.evaluate().
    Quando o PJe JS atribui img.src = "http://localhost:8800/...", nosso
    setter intercepta ANTES do request ir à rede:
      1. Extrai JSON do parâmetro `r`
      2. Chama Python via window.__pjeSignDoc() (expose_function bridge)
      3. Python assina com RSA+MD5 e faz POST ao SSO (→ HTTP 204)
      4. JS dispara img.onload artificialmente
      5. PJe JS recebe onload → submete formulário via A4J.AJAX.Submit

    ═══════════════════════════════════════════════════════════════════════
    BUG CRÍTICO 1: Array.prototype.toJSON (Prototype.js)
    ═══════════════════════════════════════════════════════════════════════
    O PJe usa Prototype.js que redefine Array.prototype.toJSON. O Playwright
    internamente usa JSON.stringify([args]) para serializar chamadas expose_function.
    Com toJSON redefinido, a serialização corrompe → "serializedArgs is not an array".
    FIX: deletar Array.prototype.toJSON antes de cada chamada via _callPjeSign().

    ═══════════════════════════════════════════════════════════════════════
    BUG CRÍTICO 2: Loop de re-signing após modal
    ═══════════════════════════════════════════════════════════════════════
    O modal "PJeOffice Indisponível" pode aparecer mesmo após signing bem-sucedido
    (PJe tem timeout próprio). Forçar A4J.AJAX.Submit quando _signed_challenges > 0
    cria CONFLITO com o inflight request do img.onload. O código NÃO deve
    re-acionar o botão se já temos challenges assinados — apenas aguardar.
    """
    logger.info("%s Configurando interceptação PJeOffice via JS monkey-patch...", tag)

    _signed_challenges: list[str] = []

    # ── 1. Expor função de assinatura ao browser ──
    async def _browser_sign_handler(r_json_str: str) -> str:
        """Chamado pelo JS patcheado. Roteia pelo tarefaId:
        - cnj.assinadorHash → assina bytes do doc e POST para uploadUrl no PJe
        - sso.autenticador  → assina mensagem e POST ao SSO Keycloak
        """
        try:
            r_data = json.loads(r_json_str)
            tarefa_id = r_data.get("tarefaId", "")
            tarefa = json.loads(r_data.get("tarefa", "{}"))
            servidor = r_data.get("servidor", "")

            logger.info(
                "%s [JS-SIGN] tarefaId=%s servidor=%s tarefa_keys=%s",
                tag, tarefa_id, servidor[:60], list(tarefa.keys()),
            )

            # ── Ramo 1: assinatura de documentos (PJeOffice cnj.assinadorHash) ──
            # CONFIRMADO POR DECOMPILAÇÃO DO PJEOFFICE PRO:
            #   PjeHashSigningTask → signer.process(hashToBytes(hash))
            #     → ASN1MD5withRSA = Prehashed(MD5) + PKCS1v15
            #   PjeWebClient FORMAT 2 → form-encoded:
            #     assinatura + cadeiaCertificado + ALL arquivo fields (giveBack)
            #   HashedOutputDocument.giveBack() → envia TODOS os campos do JSON
            #   CertificateAware.getCertificateChain64() → PkiPath base64
            if tarefa_id == "cnj.assinadorHash":
                upload_url = tarefa.get("uploadUrl", "")
                algoritmo = tarefa.get("algoritmoAssinatura", "ASN1MD5withRSA")
                arquivos = tarefa.get("arquivos", [])

                logger.info(
                    "%s [JS-SIGN] cnj.assinadorHash uploadUrl=%s algoritmo=%s arquivos=%d",
                    tag, upload_url, algoritmo, len(arquivos),
                )

                if not upload_url or not arquivos:
                    logger.error(
                        "%s [JS-SIGN] cnj.assinadorHash sem uploadUrl ou arquivos! tarefa=%s",
                        tag, json.dumps(tarefa)[:400],
                    )
                    return "ERROR:missing_upload_params"

                full_upload_url = servidor.rstrip("/") + upload_url
                from urllib.parse import urlencode
                pdf_bytes = None  # PjeHashSigningTask não precisa de bytes completos

                for idx, arquivo in enumerate(arquivos):
                    # PjeHashSigningTask usa document.getHash() → json.get("hash")
                    hash_hex = arquivo.get("hash", arquivo.get("hashDoc", ""))

                    logger.info(
                        "%s [JS-SIGN] arquivo[%d] full=%s",
                        tag, idx, json.dumps(arquivo)[:500],
                    )

                    if not hash_hex:
                        logger.error(
                            "%s [JS-SIGN] arquivo[%d] sem campo 'hash'!", tag, idx,
                        )
                        continue

                    # ══ ASSINATURA: PjeHashSigningTask.hashToBytes(hash) ══
                    # Converte hex → bytes (16 bytes para MD5) e assina com
                    # ASN1MD5withRSA = Prehashed(MD5) = não re-hash, só
                    # DigestInfo wrapping + PKCS1v15 + RSA.
                    # Fallback: se Prehashed falhar, tenta MD5 normal (double-hash).
                    hash_bytes = bytes.fromhex(hash_hex)

                    sig_bytes = None
                    # Tentativa 1: Prehashed (correto conforme decompilação)
                    try:
                        sig_bytes = private_key.sign(
                            hash_bytes,
                            padding.PKCS1v15(),
                            Prehashed(hashes.MD5()),
                        )
                        logger.info(
                            "%s [JS-SIGN] arquivo[%d] assinado com Prehashed(MD5) hash=%s sigLen=%d",
                            tag, idx, hash_hex[:16], len(sig_bytes),
                        )
                    except Exception as e_pre:
                        logger.warning(
                            "%s [JS-SIGN] Prehashed(MD5) falhou: %s — tentando MD5 normal",
                            tag, e_pre,
                        )
                        # Tentativa 2: MD5 normal (double-hash)
                        try:
                            sig_bytes = private_key.sign(
                                hash_bytes,
                                padding.PKCS1v15(),
                                hashes.MD5(),
                            )
                            logger.info(
                                "%s [JS-SIGN] arquivo[%d] assinado com MD5 (double-hash) sigLen=%d",
                                tag, idx, len(sig_bytes),
                            )
                        except Exception as e_md5:
                            logger.error(
                                "%s [JS-SIGN] Erro ao assinar arquivo[%d]: %s", tag, idx, e_md5,
                            )
                            continue

                    if sig_bytes is None:
                        continue

                    assinatura_b64 = base64.b64encode(sig_bytes).decode("ascii")
                    _signed_challenges.append(hash_hex)

                    # ══ POST: PjeWebClient FORMAT 2 (form-encoded) ══
                    # PjeWebClient.createOutput(endpoint, signedData, document):
                    #   assinatura = signedData.getSignature64()
                    #   cadeiaCertificado = signedData.getCertificateChain64() [PkiPath]
                    #   + document.giveBack() → ALL fields from arquivo JSON
                    form_params = {
                        "assinatura": assinatura_b64,
                        "cadeiaCertificado": certchain_b64,
                    }
                    # giveBack() envia TODOS os campos do arquivo JSON
                    for key, val in arquivo.items():
                        form_params[key] = str(val)

                    form_data = urlencode(form_params)
                    logger.info(
                        "%s [JS-SIGN] POST %s form_keys=%s",
                        tag, full_upload_url, list(form_params.keys()),
                    )

                    try:
                        resp = await page.context.request.post(
                            full_upload_url,
                            data=form_data,
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                        )
                        resp_body_bytes = await resp.body()
                        resp_body = resp_body_bytes.decode("utf-8", errors="replace")[:500]
                        logger.info(
                            "%s [JS-SIGN] uploadUrl HTTP %d body=%s",
                            tag, resp.status, resp_body,
                        )

                        # PjeWebClient verifica: resposta começa com "Sucesso"
                        if resp.ok and (
                            resp_body.startswith("Sucesso")
                            or not resp_body.startswith("Erro:")
                        ):
                            logger.info(
                                "%s [JS-SIGN] ✅ Upload OK! arquivo[%d] hash=%s",
                                tag, idx, hash_hex[:16],
                            )
                            # Sucesso no primeiro formato — continua pro próximo arquivo
                            continue

                        # Se FORMAT 2 falhou com Prehashed, tentar com full PDF bytes
                        # (caso o servidor espere assinatura dos bytes completos)
                        if pdf_bytes and resp_body.startswith("Erro:"):
                            logger.warning(
                                "%s [JS-SIGN] FORMAT 2 falhou (%s), tentando com pdf_bytes completo",
                                tag, resp_body[:80],
                            )
                            try:
                                sig_full = private_key.sign(
                                    pdf_bytes,
                                    padding.PKCS1v15(),
                                    hashes.MD5(),
                                )
                                form_params["assinatura"] = base64.b64encode(sig_full).decode("ascii")
                                form_data2 = urlencode(form_params)
                                resp2 = await page.context.request.post(
                                    full_upload_url,
                                    data=form_data2,
                                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                                )
                                resp2_body = (await resp2.body()).decode("utf-8", errors="replace")[:500]
                                logger.info(
                                    "%s [JS-SIGN] uploadUrl fullbytes HTTP %d body=%s",
                                    tag, resp2.status, resp2_body,
                                )
                                if resp2.ok and not resp2_body.startswith("Erro:"):
                                    logger.info(
                                        "%s [JS-SIGN] ✅ Upload OK com pdf_bytes! arquivo[%d]",
                                        tag, idx,
                                    )
                                    continue
                            except Exception as e_full:
                                logger.warning(
                                    "%s [JS-SIGN] pdf_bytes signing fallback falhou: %s",
                                    tag, e_full,
                                )

                        # Se form-encoded falhou, tentar FORMAT 5 (JSON) como último recurso
                        logger.warning(
                            "%s [JS-SIGN] FORMAT 2 falhou, tentando FORMAT 5 (JSON)",
                            tag,
                        )
                        json_payload = json.dumps([{
                            "hashDoc": hash_hex,
                            "assinaturaBase64": assinatura_b64,
                        }])
                        try:
                            resp3 = await page.context.request.post(
                                full_upload_url,
                                data=json_payload,
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                },
                            )
                            resp3_body = (await resp3.body()).decode("utf-8", errors="replace")[:500]
                            logger.info(
                                "%s [JS-SIGN] uploadUrl JSON HTTP %d body=%s",
                                tag, resp3.status, resp3_body,
                            )
                            if resp3.ok and not resp3_body.startswith("Erro:"):
                                logger.info(
                                    "%s [JS-SIGN] ✅ Upload OK com JSON! arquivo[%d]",
                                    tag, idx,
                                )
                                continue
                        except Exception as e_json:
                            logger.warning(
                                "%s [JS-SIGN] JSON fallback falhou: %s", tag, e_json,
                            )

                    except Exception as e_post:
                        logger.error(
                            "%s [JS-SIGN] POST para uploadUrl falhou: %s", tag, e_post,
                        )

                if not _signed_challenges:
                    return "ERROR:no_doc_signed"

                return f"OK:200"

            # ── Ramo 2: autenticação SSO (sso.autenticador) ──
            mensagem = tarefa.get("mensagem", "")
            enviar_para = tarefa.get("enviarPara", "/pjeoffice-rest")
            token = tarefa.get("token", str(uuid_mod.uuid4()))

            logger.info(
                "%s [JS-SIGN] sso.autenticador mensagem=%s... token=%s",
                tag, mensagem[:40], token[:16],
            )

            assinatura = _sign_md5_rsa(private_key, mensagem)
            _signed_challenges.append(mensagem)

            sign_payload = json.dumps({
                "certChain": certchain_b64,
                "uuid": token,
                "mensagem": mensagem,
                "assinatura": assinatura,
            })

            # Tentar POST ao SSO Keycloak (confirmado 204)
            sso_endpoint = "https://sso.cloud.pje.jus.br/auth/realms/pje" + enviar_para
            logger.info("%s [JS-SIGN] POST SSO %s", tag, sso_endpoint)
            try:
                resp = await page.context.request.post(
                    sso_endpoint,
                    data=sign_payload,
                    headers={"Content-Type": "application/json"},
                )
                status = resp.status
                logger.info("%s [JS-SIGN] SSO: HTTP %d", tag, status)
                if resp.ok:
                    return f"OK:{status}"
            except Exception as e:
                logger.warning("%s [JS-SIGN] SSO falhou: %s", tag, e)

            # Fallback: POST ao servidor PJe
            if servidor:
                pje_endpoint = servidor.rstrip("/") + enviar_para
                logger.info("%s [JS-SIGN] Fallback POST PJe %s", tag, pje_endpoint)
                try:
                    resp2 = await page.context.request.post(
                        pje_endpoint,
                        data=sign_payload,
                        headers={"Content-Type": "application/json"},
                    )
                    logger.info("%s [JS-SIGN] PJe: HTTP %d", tag, resp2.status)
                    if resp2.ok:
                        return f"OK:{resp2.status}"
                except Exception as e:
                    logger.warning("%s [JS-SIGN] PJe falhou: %s", tag, e)

            return "ERROR:no_endpoint_accepted"
        except Exception as e:
            logger.error("%s [JS-SIGN] Erro: %s", tag, e, exc_info=True)
            return f"ERROR:{e}"

    try:
        await page.expose_function("__pjeSignDoc", _browser_sign_handler)
        logger.info("%s expose_function('__pjeSignDoc') OK", tag)
    except Exception as e:
        logger.warning("%s expose_function já registrada: %s", tag, e)

    # ── 2. Monkey-patch JS: HTMLImageElement.prototype.src, XHR, fetch ──
    # NOTA: Patchear window.Image constructor NÃO funciona porque o PJe JS
    # já capturou referência ao constructor original antes do nosso patch.
    # A solução é patchear HTMLImageElement.prototype.src SETTER diretamente,
    # que intercepta TODAS as atribuições img.src independente de como
    # o Image foi criado (new Image(), createElement('img'), etc).
    logger.info("%s Injetando monkey-patch JS para PJeOffice...", tag)
    await page.evaluate(
        """() => {
            // ═══════ Patch HTMLImageElement.prototype.src (GLOBAL) ═══════
            // Isso intercepta QUALQUER img.src = "..." em QUALQUER Image element
            const _srcDescriptor = Object.getOwnPropertyDescriptor(
                HTMLImageElement.prototype, 'src'
            );
            if (!_srcDescriptor || !_srcDescriptor.set) {
                console.error('[PJEPATCH] Não foi possível obter src descriptor!');
                return;
            }

            // Fix para Prototype.js que define Array.prototype.toJSON e quebra
            // a serialização interna do Playwright no expose_function.
            // Deve ser chamado ANTES de qualquer window.__pjeSignDoc(...).
            function _callPjeSign(rParam) {
                const _saved = Array.prototype.toJSON;
                try { delete Array.prototype.toJSON; } catch(e) {}
                const promise = window.__pjeSignDoc(rParam);
                try {
                    if (_saved !== undefined) Array.prototype.toJSON = _saved;
                } catch(e) {}
                return promise;
            }

            // Helper para processar URL do PJeOffice
            function _handlePjeUrl(img, url) {
                console.log('[PJEPATCH] Intercepted img.src:', url.substring(0, 120));
                try {
                    const urlObj = new URL(url);
                    const rParam = urlObj.searchParams.get('r');
                    if (rParam) {
                        try {
                            const rObj = JSON.parse(rParam);
                            const tarefaId = rObj.tarefaId || '?';
                            const tarefa = rObj.tarefa ? JSON.parse(rObj.tarefa) : {};
                            const tarefaKeys = Object.keys(tarefa).join(',');
                            const arquivosLen = (tarefa.arquivos || []).length;
                            console.log('[PJEPATCH] tarefaId=' + tarefaId +
                                ' tarefa_keys=' + tarefaKeys +
                                ' arquivos=' + arquivosLen +
                                ' uploadUrl=' + (tarefa.uploadUrl || ''));
                        } catch(e) { console.log('[PJEPATCH] rParam parse error:', e); }
                        console.log('[PJEPATCH] Chamando __pjeSignDoc com rParam...');
                        _callPjeSign(rParam)
                            .then(result => {
                                console.log('[PJEPATCH] Sign result:', result);
                                if (result && result.startsWith('OK:')) {
                                    console.log('[PJEPATCH] ✓ Firing img.onload (onload type:', typeof img.onload, ')');

                                    // ═══ DIAGNÓSTICO: Interceptar XHR APÓS onload ═══
                                    const _origOpenDebug = XMLHttpRequest.prototype.open;
                                    const _xhrDebugInstalled = !window.__pjeXhrDebug;
                                    if (_xhrDebugInstalled) {
                                        window.__pjeXhrDebug = true;
                                        window.__pjeXhrResponses = [];  // Salvar respostas para inspeção
                                        XMLHttpRequest.prototype.open = function(method, url, ...args) {
                                            this.__dbgUrl = url;
                                            this.__dbgMethod = method;
                                            this.addEventListener('load', function() {
                                                const resp = this.responseText || '';
                                                console.log('[PJEPATCH-XHR] ' + this.__dbgMethod + ' ' +
                                                    (this.__dbgUrl || '').substring(0, 200) +
                                                    ' status=' + this.status + ' len=' + resp.length);
                                                // Salvar response completa para inspeção via page.evaluate
                                                // Buscar oncomplete e keywords no response completo
                                                const onCompleteMatch = resp.match(/org\.ajax4jsf\.oncomplete">([\s\S]*?)<\/span>/);
                                                const hasError = resp.toLowerCase().includes('erro') || resp.toLowerCase().includes('error');
                                                const hasSucesso = resp.toLowerCase().includes('sucesso') ||
                                                    resp.toLowerCase().includes('concluído');
                                                window.__pjeXhrResponses.push({
                                                    url: this.__dbgUrl,
                                                    status: this.status,
                                                    len: resp.length,
                                                    head: resp.substring(0, 3000),
                                                    tail: resp.substring(Math.max(0, resp.length - 2000)),
                                                    oncomplete: onCompleteMatch ? onCompleteMatch[1] : null,
                                                    hasError: hasError,
                                                    hasSucesso: hasSucesso,
                                                });
                                                // Logar chunks do response para ver o XML A4J
                                                for (let i = 0; i < Math.min(resp.length, 6000); i += 2000) {
                                                    console.log('[PJEPATCH-XHR] resp[' + i + ':' + (i+2000) + ']:', resp.substring(i, i+2000));
                                                }
                                            });
                                            this.addEventListener('error', function() {
                                                console.log('[PJEPATCH-XHR] NETWORK ERROR: ' + this.__dbgMethod + ' ' +
                                                    (this.__dbgUrl || '').substring(0, 200));
                                            });
                                            return _origOpenDebug.call(this, method, url, ...args);
                                        };
                                        console.log('[PJEPATCH] ✓ XHR debug interceptor installed');
                                    }

                                    setTimeout(() => {
                                        // Simular carregamento natural da imagem
                                        // CRÍTICO: PJe verifica this.width == 2 (erro) vs != 2 (sucesso)
                                        Object.defineProperty(img, 'complete', {
                                            value: true, configurable: true
                                        });
                                        Object.defineProperty(img, 'width', {
                                            value: 1, configurable: true
                                        });
                                        Object.defineProperty(img, 'height', {
                                            value: 1, configurable: true
                                        });
                                        Object.defineProperty(img, 'naturalWidth', {
                                            value: 1, configurable: true
                                        });
                                        Object.defineProperty(img, 'naturalHeight', {
                                            value: 1, configurable: true
                                        });
                                        // ═══ FIX: Event object correto com target ═══
                                        const evt = new Event('load', {bubbles: false, cancelable: false});
                                        try {
                                            Object.defineProperty(evt, 'target', { value: img, configurable: true });
                                            Object.defineProperty(evt, 'srcElement', { value: img, configurable: true });
                                            Object.defineProperty(evt, 'currentTarget', { value: img, configurable: true });
                                        } catch(e) {
                                            console.warn('[PJEPATCH] Could not set event target:', e.message);
                                        }

                                        if (typeof img.onload === 'function') {
                                            const onloadSrc = img.onload.toString();
                                            window.__pjeOnloadSource = onloadSrc;
                                            // Buscar definição de onSucesso nos scripts da página
                                            const allScripts = document.querySelectorAll('script');
                                            let onSucessoSource = 'not_found_in_scripts';
                                            allScripts.forEach(s => {
                                                const txt = s.textContent || s.innerText || '';
                                                if (txt.includes('onSucesso')) {
                                                    const idx = txt.indexOf('onSucesso');
                                                    onSucessoSource = txt.substring(Math.max(0, idx-100), idx+1000);
                                                }
                                            });
                                            window.__pjeOnSucessoSource = onSucessoSource;
                                            console.log('[PJEPATCH] onSucesso definition found:', onSucessoSource.length, 'chars');
                                            // Patch A4J.AJAX.Submit para capturar o que onSucesso envia
                                            if (!window.__pjeA4jSubmitPatched) {
                                                window.__pjeA4jSubmitPatched = true;
                                                window.__pjeA4jSubmitCalls = [];
                                                const origSubmit = A4J.AJAX.Submit;
                                                A4J.AJAX.Submit = function(formId, event, options) {
                                                    const callInfo = {
                                                        formId: formId,
                                                        optionKeys: options ? Object.keys(options) : [],
                                                        similarityGroupingId: options ? options.similarityGroupingId : null,
                                                        parameters: options ? JSON.stringify(options.parameters || {}).substring(0, 500) : null,
                                                        actionUrl: options ? options.actionUrl : null,
                                                    };
                                                    window.__pjeA4jSubmitCalls.push(callInfo);
                                                    console.log('[PJEPATCH-A4J] Submit called:', JSON.stringify(callInfo));
                                                    return origSubmit.call(this, formId, event, options);
                                                };
                                            }
                                            console.log('[PJEPATCH] Calling img.onload.call(img, evt)...');
                                            try {
                                                img.onload.call(img, evt);
                                                console.log('[PJEPATCH] img.onload() returned OK');
                                            } catch(e) {
                                                console.error('[PJEPATCH] img.onload() THREW:', e.message, e.stack);
                                                // Se onSucesso não está acessível, tentar chamar diretamente
                                                // via avaliação no escopo global
                                                console.log('[PJEPATCH] Tentando chamar onSucesso() diretamente...');
                                                try {
                                                    if (typeof onSucesso === 'function') {
                                                        onSucesso();
                                                        console.log('[PJEPATCH] onSucesso() chamada com sucesso');
                                                    } else {
                                                        console.error('[PJEPATCH] onSucesso não existe no escopo global');
                                                    }
                                                } catch(e2) {
                                                    console.error('[PJEPATCH] onSucesso() falhou:', e2.message);
                                                }
                                            }
                                        } else {
                                            console.warn('[PJEPATCH] img.onload is NOT a function:', typeof img.onload);
                                        }

                                        // Dispatch com event correto
                                        console.log('[PJEPATCH] dispatchEvent load...');
                                        const evt2 = new Event('load', {bubbles: false, cancelable: false});
                                        img.dispatchEvent(evt2);
                                        console.log('[PJEPATCH] dispatchEvent load done');

                                        // ═══ DIAGNÓSTICO: snapshots pós-onload ═══
                                        [100, 500, 2000, 5000, 10000].forEach(ms => {
                                            setTimeout(() => {
                                                const body = document.body.textContent || '';
                                                let a4jState = 'A4J not found';
                                                try {
                                                    if (typeof A4J !== 'undefined' && A4J.AJAX) {
                                                        const eq = A4J.AJAX.EventQueue;
                                                        const rq = A4J.AJAX.RequestQueue;
                                                        a4jState = JSON.stringify({
                                                            eventQueue: eq ? eq.length || Object.keys(eq).length : 'N/A',
                                                            requestQueue: rq ? rq.length || Object.keys(rq).length : 'N/A',
                                                            evtKeys: eq ? Object.keys(eq).slice(0, 10) : [],
                                                            reqKeys: rq ? Object.keys(rq).slice(0, 10) : [],
                                                        });
                                                    }
                                                } catch(e) { a4jState = 'error: ' + e.message; }
                                                console.log('[PJEPATCH] +' + ms + 'ms body(' + body.length + '):', body.substring(0, 200));
                                                console.log('[PJEPATCH] +' + ms + 'ms A4J state:', a4jState);
                                            }, ms);
                                        });

                                        // ═══ Tentar forçar processamento da A4J queue após 3s ═══
                                        setTimeout(() => {
                                            try {
                                                if (typeof A4J !== 'undefined' && A4J.AJAX) {
                                                    // Inspecionar a queue interna do A4J
                                                    const eq = A4J.AJAX.EventQueue;
                                                    console.log('[PJEPATCH] A4J.AJAX.EventQueue type:', typeof eq,
                                                        'constructor:', eq ? eq.constructor.name : 'null');
                                                    if (eq) {
                                                        for (const k of Object.keys(eq)) {
                                                            const item = eq[k];
                                                            console.log('[PJEPATCH] EventQueue[' + k + ']:', typeof item,
                                                                item ? (item.toString || '').call(item).substring(0, 200) : 'null');
                                                        }
                                                    }
                                                    // Verificar se há um request pendente bloqueando
                                                    if (A4J.AJAX._request) {
                                                        console.log('[PJEPATCH] A4J._request status:', A4J.AJAX._request.readyState);
                                                    }
                                                    // Tentar forçar o dequeue
                                                    if (typeof A4J.AJAX.SubmitRequest === 'function') {
                                                        console.log('[PJEPATCH] Tentando A4J.AJAX.SubmitRequest()...');
                                                    }
                                                }
                                            } catch(e) {
                                                console.log('[PJEPATCH] A4J inspection error:', e.message);
                                            }
                                        }, 3000);
                                    }, 50);
                                } else {
                                    console.warn('[PJEPATCH] Sign failed, firing onerror:', result);
                                    setTimeout(() => {
                                        if (typeof img.onerror === 'function') {
                                            img.onerror(new Event('error'));
                                        }
                                        img.dispatchEvent(new Event('error'));
                                    }, 50);
                                }
                            })
                            .catch(err => {
                                console.error('[PJEPATCH] Promise error:', err);
                                setTimeout(() => {
                                    if (typeof img.onerror === 'function') {
                                        img.onerror(new Event('error'));
                                    }
                                }, 50);
                            });
                    } else {
                        // Sem param r → health check → responder ok
                        console.log('[PJEPATCH] No r param (health check?), firing onload');
                        setTimeout(() => {
                            if (typeof img.onload === 'function') {
                                img.onload(new Event('load'));
                            }
                            img.dispatchEvent(new Event('load'));
                        }, 50);
                    }
                } catch(e) {
                    console.error('[PJEPATCH] Error processing URL:', e);
                    // Fallback: deixar o request ir normalmente
                    _srcDescriptor.set.call(img, url);
                }
            }

            Object.defineProperty(HTMLImageElement.prototype, 'src', {
                get() {
                    return _srcDescriptor.get.call(this);
                },
                set(url) {
                    if (typeof url === 'string' &&
                        (url.includes('localhost:8800') ||
                         url.includes('localhost:8801') ||
                         url.includes('pjeOffice/requisicao'))) {
                        _handlePjeUrl(this, url);
                        return;  // NÃO chamar setter original
                    }
                    // Imagens normais: setter original
                    _srcDescriptor.set.call(this, url);
                }
            });

            // ═══════ Patch XMLHttpRequest ═══════
            const _origXHROpen = XMLHttpRequest.prototype.open;
            const _origXHRSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(method, url, ...args) {
                this.__pjeUrl = (typeof url === 'string') ? url : '';
                return _origXHROpen.call(this, method, url, ...args);
            };

            XMLHttpRequest.prototype.send = function(body) {
                if (this.__pjeUrl &&
                    (this.__pjeUrl.includes('localhost:8800') ||
                     this.__pjeUrl.includes('localhost:8801') ||
                     this.__pjeUrl.includes('pjeOffice/requisicao'))) {
                    console.log('[PJEPATCH] Intercepted XHR:', this.__pjeUrl.substring(0, 120));
                    try {
                        const urlObj = new URL(this.__pjeUrl);
                        const rParam = urlObj.searchParams.get('r');
                        if (rParam) {
                            const xhr = this;
                            _callPjeSign(rParam)
                                .then(result => {
                                    console.log('[PJEPATCH] XHR sign result:', result);
                                    Object.defineProperty(xhr, 'status', {value: 200, writable: true});
                                    Object.defineProperty(xhr, 'readyState', {value: 4, writable: true});
                                    Object.defineProperty(xhr, 'responseText', {value: 'ok', writable: true});
                                    if (xhr.onreadystatechange) xhr.onreadystatechange();
                                    if (xhr.onload) xhr.onload(new Event('load'));
                                    xhr.dispatchEvent(new Event('load'));
                                });
                        }
                    } catch(e) {
                        console.error('[PJEPATCH] XHR error:', e);
                        _origXHRSend.call(this, body);
                    }
                    return;
                }
                return _origXHRSend.call(this, body);
            };

            // ═══════ Patch fetch ═══════
            const _origFetch = window.fetch;
            window.fetch = function(input, init) {
                const url = (typeof input === 'string') ? input :
                            (input && input.url) ? input.url : '';
                if (url.includes('localhost:8800') ||
                    url.includes('localhost:8801') ||
                    url.includes('pjeOffice/requisicao')) {
                    console.log('[PJEPATCH] Intercepted fetch:', url.substring(0, 120));
                    try {
                        const urlObj = new URL(url);
                        const rParam = urlObj.searchParams.get('r');
                        if (rParam) {
                            return _callPjeSign(rParam)
                                .then(() => new Response('ok', {status: 200}));
                        }
                    } catch(e) {
                        console.error('[PJEPATCH] fetch error:', e);
                    }
                    return Promise.resolve(new Response('ok', {status: 200}));
                }
                return _origFetch.call(window, input, init);
            };

            // ═══════ Patch Element.prototype.setAttribute ═══════
            // Captura setAttribute('src', 'http://localhost:8800/...') que bypassa o setter
            const _origSetAttribute = Element.prototype.setAttribute;
            Element.prototype.setAttribute = function(name, value) {
                if (name === 'src' && this instanceof HTMLImageElement &&
                    typeof value === 'string' &&
                    (value.includes('localhost:8800') ||
                     value.includes('localhost:8801') ||
                     value.includes('pjeOffice/requisicao'))) {
                    console.log('[PJEPATCH] Intercepted setAttribute src:', value.substring(0, 120));
                    _handlePjeUrl(this, value);
                    return;
                }
                return _origSetAttribute.call(this, name, value);
            };

            // ═══════ Monitorar MutationObserver para novas imagens ═══════
            // Captura img elements adicionados ao DOM com src localhost:8800
            const _observer = new MutationObserver(mutations => {
                mutations.forEach(m => {
                    m.addedNodes.forEach(node => {
                        if (node instanceof HTMLImageElement) {
                            const s = node.getAttribute('src') || '';
                            if (s.includes('localhost:8800') || s.includes('localhost:8801') ||
                                s.includes('pjeOffice/requisicao')) {
                                console.log('[PJEPATCH] MutationObserver img src:', s.substring(0, 120));
                                _handlePjeUrl(node, s);
                            }
                        }
                        if (node.querySelectorAll) {
                            node.querySelectorAll('img').forEach(img => {
                                const s = img.getAttribute('src') || '';
                                if (s.includes('localhost:8800') || s.includes('localhost:8801') ||
                                    s.includes('pjeOffice/requisicao')) {
                                    console.log('[PJEPATCH] MutationObserver nested img src:', s.substring(0, 120));
                                    _handlePjeUrl(img, s);
                                }
                            });
                        }
                    });
                });
            });
            _observer.observe(document.documentElement, {childList: true, subtree: true});

            console.log('[PJEPATCH] ✓ src setter + setAttribute + XHR + fetch + MutationObserver patched');
        }"""
    )
    logger.info("%s ✓ Monkey-patch JS injetado", tag)

    # ── Capturar console do browser para diagnóstico ──
    def _on_console(msg):
        if '[PJEPATCH' in msg.text or '[PJE' in msg.text:
            logger.info("%s [BROWSER-CONSOLE] %s: %s", tag, msg.type, msg.text[:300])
        elif 'pjeOffice' in msg.text.lower() or 'localhost:8800' in msg.text:
            logger.info("%s [BROWSER-CONSOLE] %s: %s", tag, msg.type, msg.text[:300])

    def _on_request_failed(request):
        if 'localhost:88' in request.url or 'pjeOffice' in request.url:
            logger.warning(
                "%s [REQUEST-FAILED] %s %s — errorText=%s",
                tag, request.method, request.url[:200],
                request.failure or 'unknown',
            )

    def _on_request(request):
        if 'localhost:88' in request.url or 'pjeOffice' in request.url.lower():
            logger.info(
                "%s [REQUEST-OBSERVED] %s %s",
                tag, request.method, request.url[:200],
            )

    def _on_response(response):
        url = response.url
        # Logar respostas do PJe (A4J, peticaoPopUp, pjeoffice) — NÃO estáticos
        if any(k in url for k in ['.seam', 'pjeOffice', 'pjeoffice', 'localhost:88', 'A4J', '/a4j/']):
            logger.info(
                "%s [RESPONSE] %s %s → HTTP %d (size=%s)",
                tag, response.request.method, url[:200],
                response.status, response.headers.get('content-length', '?'),
            )

    page.on('console', _on_console)
    page.on('requestfailed', _on_request_failed)
    page.on('request', _on_request)
    page.on('response', _on_response)

    # ── 3. page.route() como safety net (para requests que escapem do patch) ──
    async def _route_safety_net(route, request):
        """Fallback: se algum request escapar do JS patch, intercepta aqui."""
        req_url = request.url
        logger.warning(
            "%s [ROUTE-FALLBACK] Request escapou do JS patch: %s (resource=%s)",
            tag, req_url[:200], request.resource_type,
        )
        # Tentar assinar mesmo que tenha vindo pelo fallback
        try:
            parsed = urlparse(req_url)
            params = parse_qs(parsed.query)
            r_raw = params.get("r", [None])[0]
            if r_raw:
                r_data = json.loads(unquote(r_raw))
                tarefa = json.loads(r_data.get("tarefa", "{}"))
                mensagem = tarefa.get("mensagem", "")
                enviar_para = tarefa.get("enviarPara", "/pjeoffice-rest")
                token = tarefa.get("token", str(uuid_mod.uuid4()))

                assinatura = _sign_md5_rsa(private_key, mensagem)
                _signed_challenges.append(mensagem)

                payload = json.dumps({
                    "certChain": certchain_b64,
                    "uuid": token,
                    "mensagem": mensagem,
                    "assinatura": assinatura,
                })
                sso_url = "https://sso.cloud.pje.jus.br/auth/realms/pje" + enviar_para
                try:
                    resp = await page.context.request.post(
                        sso_url, data=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    logger.info("%s [ROUTE-FALLBACK] SSO: HTTP %d", tag, resp.status)
                except Exception as e:
                    logger.warning("%s [ROUTE-FALLBACK] SSO falhou: %s", tag, e)
        except Exception as e:
            logger.error("%s [ROUTE-FALLBACK] Erro: %s", tag, e)

        # Responder com GIF 1x1
        gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
        await route.fulfill(
            status=200, body=gif,
            headers={"Access-Control-Allow-Origin": "*", "Content-Type": "image/gif"},
        )

    await page.route("http://localhost:8800/**", _route_safety_net)
    await page.route("http://localhost:8801/**", _route_safety_net)

    # ── 4. Clicar 'Assinar documento(s)' ──
    logger.info("%s Clicando 'Assinar documento(s)'...", tag)
    btn_clicked = await page.evaluate(
        """() => {
            const btn = document.getElementById('btn-assinador');
            if (!btn) return false;
            btn.removeAttribute('disabled');
            btn.click();
            return true;
        }"""
    )
    if btn_clicked:
        logger.info("%s btn-assinador clicado via JS", tag)
    else:
        for sel in ["button:has-text('Assinar')", "[id*='assinador']"]:
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    await loc.first.click(force=True)
                    btn_clicked = True
                    logger.info("%s Botão assinar clicado: %s", tag, sel)
                    break
            except Exception:
                pass
        if not btn_clicked:
            logger.warning("%s Nenhum botão assinar encontrado!", tag)

    # ── 5. Aguardar resultado (sucesso ou modal) ──
    logger.info("%s Aguardando resultado da assinatura (até 25s)...", tag)

    resultado = None
    _modal_closed = False  # evitar fechar modal em loop
    _sucesso_interim_attempt: int | None = None  # guarda quando primeiro detectamos "sucesso" intermediário

    for attempt in range(60):  # aumentado para 60s (dá tempo ao A4J concluir)
        await asyncio.sleep(1)
        state = await page.evaluate(
            """() => {
                const body = document.body.textContent || '';
                const bodyLower = body.toLowerCase();
                const html = document.body.innerHTML || '';
                // Detectar modal PJeOffice Indisponível (só se VISÍVEL)
                const modalEl = document.getElementById('mpPJeOfficeIndisponivel');
                const modalVisible = modalEl
                    ? (modalEl.style.display !== 'none' && modalEl.offsetParent !== null)
                    : (html.includes('PJeOffice') && html.includes('Indispon') &&
                       html.includes('display: block'));
                // Verificar btn-enviar (aparece após assinatura em alguns fluxos)
                const btnEnviar = document.getElementById('btn-enviar') ||
                    document.querySelector('button[id*="enviar"]:not([disabled])') ||
                    document.querySelector('input[value*="Enviar"]:not([disabled])') ||
                    document.querySelector('input[value*="Protocolar"]:not([disabled])');
                // Detectar overlay "Por favor aguarde" do RichFaces (loading em progresso)
                const rfOverlay = document.querySelector(
                    '.rich-mpnl-mask-div, .rf-pp-mask, [id*="requestStatusContainer"], ' +
                    '.rich-request-status, .rf-st-busy'
                );
                const rfOverlayVisible = rfOverlay
                    ? (rfOverlay.style.display !== 'none' && rfOverlay.offsetParent !== null)
                    : false;
                // Detectar texto "Por favor aguarde" visível
                const hasPorFavorAguarde = bodyLower.includes('por favor aguarde') ||
                    rfOverlayVisible;
                return {
                    hasSucesso: bodyLower.includes('sucesso'),
                    hasConcluido: bodyLower.includes('concluído'),
                    hasAssinado: bodyLower.includes('assinado(s) com sucesso'),
                    hasProtocolado: bodyLower.includes('protocolad'),
                    hasNavigated: !document.location.href.includes('peticaoPopUp'),
                    hasModalIndisponivel: modalVisible,
                    hasPorFavorAguarde: hasPorFavorAguarde,
                    hasErro: bodyLower.includes('erro') && !bodyLower.includes('indispon'),
                    hasBtnEnviar: !!btnEnviar,
                    btnEnviarId: btnEnviar ? (btnEnviar.id || btnEnviar.name || 'found') : null,
                    url: document.location.href,
                    bodySnippet: body.substring(0, 300),
                };
            }"""
        )

        # Sucesso — popup navegou para outra URL (que não seja peticaoPopUp)
        if state.get("hasNavigated"):
            logger.info(
                "%s ✓ Popup navegou para URL de sucesso (attempt=%d): %s",
                tag, attempt, state.get("url", "")[:100],
            )
            resultado = "SUCESSO"
            break

        # Sucesso explícito no body — mas APENAS se o overlay "Por favor aguarde"
        # NÃO está visível (evitar falso positivo durante A4J.AJAX.Submit em andamento)
        has_sucesso_keyword = (
            state.get("hasSucesso") or state.get("hasConcluido") or state.get("hasAssinado")
        )
        is_loading = state.get("hasPorFavorAguarde", False)

        if has_sucesso_keyword and not state.get("hasModalIndisponivel"):
            if is_loading:
                if _sucesso_interim_attempt is None:
                    _sucesso_interim_attempt = attempt
                    logger.info(
                        "%s Assinatura OK mas A4J ainda processando (attempt=%d, loading=True) "
                        "— aguardando conclusão do envio...",
                        tag, attempt,
                    )
                # Após 5s de loading com challenges confirmados: forçar hideMpProgresso()
                # O servidor retorna oncomplete=hideMpProgresso() mas A4J pode não executar
                if (_sucesso_interim_attempt is not None
                        and _signed_challenges
                        and (attempt - _sucesso_interim_attempt) == 5):
                    logger.info(
                        "%s Loading persiste após 5s com challenges=%d — forçando hideMpProgresso() "
                        "e limpando overlays...",
                        tag, len(_signed_challenges),
                    )
                    cleanup_result = await page.evaluate("""() => {
                        const result = {};
                        // 1. Chamar hideMpProgresso() que o servidor mandou via oncomplete
                        try {
                            if (typeof hideMpProgresso === 'function') {
                                hideMpProgresso();
                                result.hideMpProgresso = 'called';
                            } else {
                                result.hideMpProgresso = 'not_found';
                            }
                        } catch(e) { result.hideMpProgresso = 'error: ' + e.message; }
                        // 2. Remover overlays RichFaces manualmente
                        document.querySelectorAll(
                            '.rich-mpnl-mask-div, .rf-pp-mask, .rich-request-status, ' +
                            '.rf-st-busy, [id*="requestStatusContainer"]'
                        ).forEach(el => {
                            el.style.display = 'none';
                            el.remove();
                        });
                        // 3. Esconder modal de progresso
                        try {
                            if (typeof Richfaces !== 'undefined') {
                                Richfaces.hideModalPanel('mpProgresso');
                            }
                        } catch(e) {}
                        // 4. Inspecionar os divs que o A4J deveria ter atualizado
                        ['expDiv', 'grdBas', 'divArquivos', 'modalPanelMessagesOuter', 'Messages'].forEach(id => {
                            const el = document.getElementById(id);
                            result['div_' + id] = el
                                ? {exists: true, textLen: (el.textContent || '').length,
                                   snippet: (el.textContent || '').substring(0, 200),
                                   visible: el.offsetParent !== null}
                                : {exists: false};
                        });
                        // 5. Body text atualizado
                        result.bodyLen = (document.body.textContent || '').length;
                        result.bodySnippet = (document.body.textContent || '').substring(0, 300);
                        return result;
                    }""")
                    logger.info("%s Cleanup result: %s", tag, json.dumps(cleanup_result, ensure_ascii=False)[:2000])
                # Após 10s de loading com challenges: inspecionar divs atualizados
                if (_sucesso_interim_attempt is not None
                        and _signed_challenges
                        and (attempt - _sucesso_interim_attempt) == 10):
                    # Verificar se Messages contém algo ou se formulário mudou
                    msg_check = await page.evaluate("""() => {
                        const msgs = document.getElementById('Messages');
                        const anexarMsg = document.getElementById('anexarMsg');
                        // Verificar se há botão enviar visível
                        const btnEnviar = document.querySelector(
                            '[id*="enviar"]:not([disabled]), [value*="Enviar"]:not([disabled]), ' +
                            '[value*="Protocolar"]:not([disabled]), [id*="protocolar"]'
                        );
                        // Verificar se grdBas mudou (pode ter botão de envio)
                        const grdBas = document.getElementById('grdBas');
                        return {
                            messages: msgs ? msgs.innerHTML.substring(0, 500) : 'not_found',
                            anexarMsg: anexarMsg ? anexarMsg.innerHTML.substring(0, 500) : 'not_found',
                            btnEnviar: btnEnviar ? {id: btnEnviar.id, value: btnEnviar.value, text: btnEnviar.textContent} : null,
                            grdBas: grdBas ? grdBas.textContent.substring(0, 500) : 'not_found',
                            // Listar TODOS os botões visíveis
                            buttons: Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'))
                                .filter(b => b.offsetParent !== null)
                                .map(b => ({id: b.id, value: b.value || b.textContent, disabled: b.disabled}))
                                .slice(0, 10),
                        };
                    }""")
                    logger.info(
                        "%s [POST-SIGN-STATE] Messages: %s", tag,
                        msg_check.get("messages", "")[:300],
                    )
                    logger.info(
                        "%s [POST-SIGN-STATE] anexarMsg: %s", tag,
                        msg_check.get("anexarMsg", "")[:300],
                    )
                    logger.info(
                        "%s [POST-SIGN-STATE] btnEnviar: %s", tag,
                        msg_check.get("btnEnviar"),
                    )
                    logger.info(
                        "%s [POST-SIGN-STATE] buttons: %s", tag,
                        json.dumps(msg_check.get("buttons", []), ensure_ascii=False)[:500],
                    )
                    logger.info(
                        "%s [POST-SIGN-STATE] grdBas: %s", tag,
                        msg_check.get("grdBas", "")[:300],
                    )
            else:
                # Sem overlay → A4J concluiu, sucesso confirmado
                logger.info(
                    "%s ✓ Sucesso confirmado sem overlay (attempt=%d): %s",
                    tag, attempt, state.get("bodySnippet", "")[:150],
                )
                resultado = "SUCESSO"
                break

        # Após assinatura, btn-enviar pode aparecer — clicar uma vez
        if state.get("hasBtnEnviar") and _signed_challenges and not _modal_closed:
            logger.info(
                "%s btn-enviar encontrado após assinatura (attempt=%d, id=%s) — clicando...",
                tag, attempt, state.get("btnEnviarId"),
            )
            await page.evaluate(
                """() => {
                    const btn = document.getElementById('btn-enviar') ||
                        document.querySelector('button[id*="enviar"]:not([disabled])') ||
                        document.querySelector('input[value*="Enviar"]:not([disabled])') ||
                        document.querySelector('input[value*="Protocolar"]:not([disabled])');
                    if (btn) { btn.removeAttribute('disabled'); btn.click(); return true; }
                    return false;
                }"""
            )

        # Modal "PJeOffice Indisponível" — fechar, mas NÃO re-acionar btn-assinador
        # se já assinamos com sucesso (isso criaria um loop de novo signing)
        if state.get("hasModalIndisponivel") and not _modal_closed:
            logger.warning(
                "%s Modal PJeOffice Indisponível detectado (attempt=%d, signed=%d) — fechando...",
                tag, attempt, len(_signed_challenges),
            )
            _modal_closed = True
            # Fechar modal
            await page.evaluate(
                """() => {
                    try { Richfaces.hideModalPanel('mpPJeOfficeIndisponivel'); } catch(e) {}
                    document.querySelectorAll(
                        '[data-dismiss="modal"], .modal .close, .modal button, ' +
                        '.rich-mpnl-button, [onclick*="hideModalPanel"]'
                    ).forEach(b => b.click());
                    const s = document.getElementById('mpPJeOfficeIndisponivelOpenedState');
                    if (s) s.value = '';
                    document.querySelectorAll(
                        '[id*="mpPJeOffice"], .rich-mpnl-mask-div, .modal-backdrop'
                    ).forEach(el => el.remove());
                    document.querySelectorAll('.modal').forEach(m => {
                        m.style.display = 'none';
                        m.classList.remove('in', 'show');
                    });
                }"""
            )
            await asyncio.sleep(1)

            # SOMENTE forçar A4J se NÃO temos ainda nenhum challenge assinado
            # (ou seja, signing falhou ou não aconteceu) — evitar loop de re-signing
            if not _signed_challenges:
                logger.warning(
                    "%s Nenhuma assinatura detectada — forçando A4J.AJAX.Submit...", tag,
                )
                a4j_result = await page.evaluate(
                    """() => {
                        try {
                            const btn = document.getElementById('btn-assinador');
                            if (!btn) return {error: 'no btn'};
                            btn.removeAttribute('disabled');
                            const onclick = btn.getAttribute('onclick') || '';
                            let code = onclick.replace(/^return\\s+false\\s*;\\s*;?\\s*/, '');
                            if (code.includes('A4J.AJAX.Submit')) {
                                const fn = new Function('event', code);
                                fn.call(btn, new Event('click', {bubbles: true}));
                                return {success: true, method: 'a4j_submit'};
                            }
                            return {error: 'no A4J', onclick: onclick.substring(0, 200)};
                        } catch(e) { return {error: e.message}; }
                    }"""
                )
                logger.info("%s A4J.AJAX.Submit (sem sign): %s", tag, a4j_result)
            else:
                logger.info(
                    "%s Assinatura SSO OK (%d challenges) — aguardando PJe finalizar...",
                    tag, len(_signed_challenges),
                )

        # Erro real
        if state.get("hasErro"):
            logger.error("%s Erro detectado: %s", tag, state.get("bodySnippet", ""))
            break

        if attempt % 5 == 0:
            logger.info(
                "%s Aguardando... (attempt=%d, challenges=%d, loading=%s, interim=%s) url=%s",
                tag, attempt, len(_signed_challenges),
                state.get("hasPorFavorAguarde", False),
                _sucesso_interim_attempt,
                state.get("url", "")[:80],
            )

    # ── 6. Capturar resultado ──
    # Screenshot da tela final (SEMPRE, para diagnóstico)
    final_screenshot = await _screenshot(page, "FINAL_STATE", tag)
    logger.info("%s 📸 Screenshot final: %s | URL=%s", tag, final_screenshot, page.url)

    body_text = await page.inner_text("body")
    logger.info("%s Texto final (2000): %s", tag, body_text[:2000])

    # Logar source da img.onload se capturado
    try:
        onload_src = await page.evaluate("() => window.__pjeOnloadSource || 'not_captured'")
        # Escapar newlines para log
        onload_escaped = onload_src.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        logger.info("%s [ONLOAD-SOURCE] (%d chars): %s", tag, len(onload_src), onload_escaped[:3000])
    except Exception:
        pass

    # ── Inspecionar respostas XHR A4J capturadas ──
    try:
        xhr_analysis = await page.evaluate("""() => {
            const responses = window.__pjeXhrResponses || [];
            return responses.map((xr, i) => {
                const full = xr.head + (xr.tail || '');
                // Buscar termos chave no response completo
                const keywords = ['sucesso', 'concluído', 'concluido', 'assinado',
                    'protocolad', 'erro', 'error', 'falha', 'oncomplete',
                    'ajax4jsf.oncomplete', 'Ajax-Update-Ids', 'gravarDocumento',
                    'Indisponível', 'btn-enviar', 'btn-assinador'];
                const found = {};
                keywords.forEach(kw => {
                    const idx = full.toLowerCase().indexOf(kw.toLowerCase());
                    if (idx >= 0) {
                        found[kw] = full.substring(Math.max(0, idx-50), idx+200);
                    }
                });
                // Extrair oncomplete script
                const onCompleteMatch = full.match(/org\\.ajax4jsf\\.oncomplete">([\s\S]*?)<\\/span>/);
                return {
                    url: xr.url,
                    status: xr.status,
                    len: xr.len,
                    head: xr.head.substring(0, 1500),
                    tail: (xr.tail || '').substring(0, 1500),
                    keywords: found,
                    oncomplete: onCompleteMatch ? onCompleteMatch[1].substring(0, 500) : null,
                };
            });
        }""")
        for i, xr in enumerate(xhr_analysis):
            logger.info(
                "%s [XHR-RESPONSE %d] %s → HTTP %s len=%s",
                tag, i, (xr.get("url") or "")[:120], xr.get("status"), xr.get("len"),
            )
            if xr.get("oncomplete"):
                logger.info("%s [XHR-RESPONSE %d] ONCOMPLETE: %s", tag, i, xr["oncomplete"])
            if xr.get("keywords"):
                for kw, ctx in xr["keywords"].items():
                    logger.info("%s [XHR-RESPONSE %d] KEYWORD '%s': ...%s...", tag, i, kw, ctx[:200])
    except Exception as e:
        logger.warning("%s Não foi possível inspecionar XHR responses: %s", tag, e)

    # NÃO declarar sucesso apenas por ter assinatura SSO + interim keywords.
    # A assinatura SSO 204 não garante que o A4J submeteu o formulário.
    # Só é sucesso REAL se o popup navegou ou keywords apareceram sem loading.
    if resultado is None and _signed_challenges:
        logger.warning(
            "%s Assinatura SSO OK (%d challenges) mas A4J NÃO completou a submissão. "
            "O formulário provavelmente não foi enviado. interim=%s",
            tag, len(_signed_challenges), _sucesso_interim_attempt,
        )

    # Se já detectamos sucesso
    if resultado == "SUCESSO":
        # Tentar extrair protocolo (petição inicial tem, avulsa não)
        for pattern in [
            r"[Pp]rotocolo\s*(?::|nº|n\.?º?|número)?\s*(\d[\d./-]+\d)",
            r"[Pp]rotocolad[ao]\s*(?:com\s+(?:o\s+)?(?:número|nº))?\s*(\d[\d./-]+\d)",
            r"[Rr]ecibo\s*(?::|nº|n\.?º?)?\s*(\d[\d./-]+\d)",
            r"[Nn]úmero[:\s]+(\d{10,})",
        ]:
            match = re.search(pattern, body_text)
            if match:
                protocolo = match.group(1)
                logger.info("%s ✓ PROTOCOLO CAPTURADO: %s", tag, protocolo)
                return protocolo
        # Petição avulsa: sucesso sem número
        logger.info("%s ✓ Sucesso sem número (petição avulsa)", tag)
        return "SUCESSO_SEM_NUMERO"

    # Buscar protocolo no body (pode ter aparecido sem keyword de sucesso)
    protocolo_patterns = [
        r"[Pp]rotocolo\s*(?::|nº|n\.?º?|número)?\s*(\d[\d./-]+\d)",
        r"[Pp]rotocolad[ao]\s*(?:com\s+(?:o\s+)?(?:número|nº))?\s*(\d[\d./-]+\d)",
        r"[Rr]ecibo\s*(?::|nº|n\.?º?)?\s*(\d[\d./-]+\d)",
        r"(?:nº|número)\s*(?:do\s+)?protocolo\s*:\s*(\d[\d./-]+\d)",
        r"[Nn]úmero[:\s]+(\d{10,})",
    ]
    for pattern in protocolo_patterns:
        match = re.search(pattern, body_text)
        if match:
            protocolo = match.group(1)
            logger.info("%s ✓ PROTOCOLO CAPTURADO (late): %s", tag, protocolo)
            return protocolo

    # Keywords de sucesso sem número
    success_keywords = [
        "sucesso", "protocolad", "recebid", "registrad",
        "petição incluída", "documento adicionado", "foi enviada",
        "concluído com sucesso", "assinado(s) com sucesso",
        "peticionamento foi concluído",
    ]
    if any(kw in body_text.lower() for kw in success_keywords):
        logger.info("%s Sucesso detectado no body (sem protocolo)", tag)
        return "SUCESSO_SEM_NUMERO"

    # Erro
    error_keywords = ["erro", "falha", "rejeitad", "inválid", "negad"]
    if any(kw in body_text.lower() for kw in error_keywords):
        logger.error("%s Erro detectado: %s", tag, body_text[:500])
        return None

    logger.warning(
        "%s Resultado indefinido. URL=%s challenges=%d body=%s",
        tag, page.url, len(_signed_challenges), body_text[:500],
    )
    return None

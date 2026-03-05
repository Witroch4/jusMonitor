"""Coleta automatizada de Jurisdições (Comarcas) e Classes Judiciais do PJe TRF1.

Fluxo:
  1. Login com certificado A1 (mTLS + SSO PJeOffice) em pje1g.trf1.jus.br
  2. Navegar para Processo/CadastroPeticaoInicial/cadastrar.seam?newInstance=true
  3. Selecionar Matéria 1861 (DIREITO ADMINISTRATIVO) → aguardar AJAX A4J
  4. Extrair todas as opções do combo Jurisdição  (~68 Seções/Subseções)
  5. Para cada Jurisdição: selecionar → aguardar AJAX → extrair Classes Judiciais
  6. Salvar JSON em /app/app/data/comarcas_trf1.json
  7. Atualizar bloco JURISDICOES["trf1"] em pje_cadastro_dados.py

Execução:
  - Automática via scheduler (a cada 30 h) em main.py
  - Manual via POST /coletar-comarcas
  - Standalone: python3 -m app.scrapers.coletar_comarcas
"""

import asyncio
import base64
import json
import logging
import os
import re
import uuid as uuid_mod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pyotp
from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

from app.browser_pool import BROWSER_ARGS, USER_AGENT
from app.data.pje_cadastro_dados import SELECT_IDS, NO_SELECTION
from app.scrapers.pje_peticionamento import (
    _extract_pem_from_pfx,
    _cleanup_pem_files,
    _get_certchain_b64,
    _sign_md5_rsa,
    PJE_LOGIN_URLS,
    PJE_BASE_URLS,
    PJE_SSO_ORIGINS,
)

logger = logging.getLogger(__name__)

_stealth = Stealth()

# ──────────────────────────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────────────────────────

TRIBUNAL_CODE = "trf1"
LOGIN_URL    = PJE_LOGIN_URLS[TRIBUNAL_CODE]
BASE_URL     = PJE_BASE_URLS[TRIBUNAL_CODE]
SSO_ORIGINS  = PJE_SSO_ORIGINS[TRIBUNAL_CODE]

CADASTRAR_URL = (
    f"{BASE_URL}/Processo/CadastroPeticaoInicial/cadastrar.seam?newInstance=true"
)

# Matéria padrão para disparar o cascade Jurisdição → Classe
MATERIA_DEFAULT = "1861"  # DIREITO ADMINISTRATIVO E OUTRAS MATÉRIAS DE DIREITO PÚBLICO

# Throttle entre seleções de jurisdição — respeitar o servidor
THROTTLE_SECS = 1.0

DATA_DIR           = Path(__file__).parent.parent / "data"
OUTPUT_JSON        = DATA_DIR / "comarcas_trf1.json"
PJE_CADASTRO_PY    = DATA_DIR / "pje_cadastro_dados.py"

# SSO endpoint do PJe Cloud
PJEOFFICE_REST_URL = "https://sso.cloud.pje.jus.br/auth/realms/pje/pjeoffice-rest"


# ──────────────────────────────────────────────────────────────────
# Dataclasses de resultado
# ──────────────────────────────────────────────────────────────────

@dataclass
class ColetaComarcasResult:
    sucesso: bool = False
    tribunal: str = TRIBUNAL_CODE
    colhido_em: str = ""
    total_jurisdicoes: int = 0
    jurisdicoes: list = field(default_factory=list)
    # chave = value da jurisdição, valor = lista de {value, text}
    classes_por_jurisdicao: dict = field(default_factory=dict)
    erro: str = ""


# ──────────────────────────────────────────────────────────────────
# Função principal
# ──────────────────────────────────────────────────────────────────

async def coletar_jurisdicoes_trf1(
    pfx_bytes: bytes,
    pfx_password: str,
    coletar_classes: bool = True,
    totp_secret: Optional[str] = None,
) -> ColetaComarcasResult:
    """Loga no PJe TRF1 e coleta Jurisdições (e Classes Judiciais) do cadastrar.seam.

    Args:
        pfx_bytes:       Conteúdo binário do arquivo .pfx (certificado A1)
        pfx_password:    Senha do certificado
        coletar_classes: Se True, coleta também as Classes Judiciais por jurisdição
        totp_secret:     Segredo TOTP base32 (se 2FA estiver ativo)

    Returns:
        ColetaComarcasResult com jurisdicoes + classes_por_jurisdicao
    """
    tag = "[COMARCAS-TRF1]"
    result = ColetaComarcasResult()

    # ── Passo 1: Extrair chaves do PFX ──────────────────────────────
    cert_path = key_path = None
    try:
        pkcs = load_pkcs12(pfx_bytes, pfx_password.encode())
        _private_key     = pkcs.key
        _cert_obj        = pkcs.cert.certificate
        _additional      = [c.certificate for c in (pkcs.additional_certs or [])]
        _certchain_b64   = _get_certchain_b64(_cert_obj, _additional)
        cert_path, key_path = _extract_pem_from_pfx(pfx_bytes, pfx_password)
        logger.info("%s Certificado carregado OK.", tag)
    except Exception as e:
        result.erro = f"Erro ao processar certificado PFX: {e}"
        logger.error("%s %s", tag, result.erro)
        return result

    pw = browser = context = None
    try:
        # ── Passo 2: Iniciar browser com mTLS ───────────────────────
        logger.info("%s Iniciando Chromium headless...", tag)
        pw      = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True, args=BROWSER_ARGS)

        client_certs = [
            {"origin": origin, "certPath": cert_path, "keyPath": key_path}
            for origin in SSO_ORIGINS
        ]
        context = await browser.new_context(
            user_agent=USER_AGENT,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            client_certificates=client_certs,
        )
        await _stealth.apply_stealth_async(context)
        page = await context.new_page()

        # ── Passo 3: Navegar para login ──────────────────────────────
        logger.info("%s Navegando para login: %s", tag, LOGIN_URL)
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)

        # login.seam redireciona para Keycloak (sso.cloud.pje.jus.br) via JS/meta-refresh.
        # Aguardar o redirect completar — sem isso o challenge ainda não está na página.
        logger.info("%s Aguardando redirect login.seam → Keycloak (até 20s)...", tag)
        try:
            await page.wait_for_url(
                re.compile(r"sso\.cloud\.pje\.jus\.br|login-actions"),
                timeout=20_000,
            )
        except PlaywrightTimeout:
            logger.warning("%s Timeout aguardando redirect Keycloak. URL atual: %s", tag, page.url)

        # Aguardar página do Keycloak estar totalmente carregada
        try:
            await page.wait_for_load_state("load", timeout=15_000)
        except PlaywrightTimeout:
            pass
        await asyncio.sleep(1)

        # Aguardar o botão CERTIFICADO DIGITAL aparecer no DOM (renderizado via JS)
        logger.info("%s Aguardando botão CERTIFICADO DIGITAL (URL=%s)...", tag, page.url)
        try:
            await page.wait_for_selector(
                "[onclick*='autenticar'], #kc-pje-office",
                timeout=15_000,
            )
        except PlaywrightTimeout:
            logger.warning("%s Timeout aguardando botão autenticar. Tentando mesmo assim.", tag)

        # ── Passo 4: Extrair challenge SSO ──────────────────────────
        onclick_data = await page.evaluate("""() => {
            // 1. Tenta pelo id do botão PJeOffice
            const btn = document.getElementById('kc-pje-office');
            if (btn) {
                const oc = btn.getAttribute('onclick') || '';
                const m = oc.match(/autenticar\\('([^']+)',\\s*'([^']+)'\\)/);
                if (m) return {codigoSeguranca: m[1], mensagem: m[2]};
            }
            // 2. Fallback: qualquer elemento com autenticar() no onclick
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
            result.erro = "Challenge SSO (autenticar) não encontrado na página de login."
            logger.error(
                "%s %s | URL=%s | body[:1000]=%s",
                tag, result.erro, page.url, body_text[:1000],
            )
            return result

        logger.info("%s Challenge SSO: nonce=%s", tag, onclick_data["mensagem"])

        form_action = await page.evaluate("""() => {
            const form = document.getElementById('loginForm');
            return form ? form.action : null;
        }""")
        if not form_action:
            result.erro = "Form action do login SSO não encontrado."
            logger.error("%s %s", tag, result.erro)
            return result

        # ── Passo 5: Assinar nonce e submeter via pjeoffice-rest ────
        token_uuid    = str(uuid_mod.uuid4())
        assinatura_b64 = _sign_md5_rsa(_private_key, onclick_data["mensagem"])
        sso_payload   = json.dumps({
            "certChain":  _certchain_b64,
            "uuid":       token_uuid,
            "mensagem":   onclick_data["mensagem"],
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
                    return {status: resp.status};
                } catch (e) { return {error: String(e)}; }
            }""",
            [PJEOFFICE_REST_URL, sso_payload],
        )
        logger.info("%s pjeoffice-rest: %s", tag, rest_result)

        if rest_result.get("status") not in (200, 204):
            result.erro = f"SSO pjeoffice-rest falhou: {rest_result}"
            logger.error("%s %s", tag, result.erro)
            return result

        # Submeter formulário de login
        await page.evaluate(
            """([uuid]) => {
                const code = document.getElementById('pjeoffice-code');
                if (code) code.value = uuid;
                const form = document.getElementById('loginForm');
                if (!form) return;
                const btn = document.createElement('input');
                btn.type = 'hidden';
                btn.name = 'login-pje-office';
                btn.value = 'CERTIFICADO DIGITAL';
                form.appendChild(btn);
                form.submit();
            }""",
            [token_uuid],
        )

        # Aguardar redirect pós-login
        try:
            await page.wait_for_url(
                re.compile(r"(^https?://pje1g\.trf|^https?://pje\.jf|login-actions)"),
                timeout=30_000,
            )
        except PlaywrightTimeout:
            pass
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except Exception:
            pass
        await asyncio.sleep(2)

        # ── Passo 6b: Tratar página de TOTP (2FA) ───────────────────
        otp_input = page.locator("input[name='otp'], input[id='otp']")
        otp_found = await otp_input.count() > 0
        if not otp_found and "login-actions" in page.url:
            logger.info("%s Em login-actions, aguardando TOTP input...", tag)
            for _retry in range(5):
                await asyncio.sleep(1)
                otp_found = await otp_input.count() > 0
                if otp_found:
                    break

        if otp_found:
            logger.info("%s Página de TOTP detectada. URL=%s", tag, page.url)
            if not totp_secret:
                result.erro = (
                    "Login requer TOTP (2FA) mas totp_secret não foi fornecido. "
                    "Configure PJE_TOTP_SECRET no .env ou passe totp_secret no request."
                )
                logger.error("%s %s", tag, result.erro)
                return result

            totp_obj  = pyotp.TOTP(totp_secret.strip().upper())
            totp_code = totp_obj.now()
            logger.info("%s Código TOTP gerado: %s (secret_len=%d)", tag, totp_code, len(totp_secret))

            await otp_input.first.fill(totp_code)
            await asyncio.sleep(0.3)

            submit_btn = page.locator("input[id='kc-login']")
            if await submit_btn.count() > 0:
                await submit_btn.first.evaluate("el => el.click()")
            else:
                btn2 = page.locator("input[name='login'], button[type='submit']")
                if await btn2.count() > 0:
                    await btn2.first.evaluate("el => el.click()")
                else:
                    await otp_input.first.press("Enter")

            logger.info("%s TOTP submetido, aguardando redirect (30s)...", tag)
            try:
                await page.wait_for_url(
                    re.compile(r"(^https?://pje1g\.trf|^https?://pje\.jf)"),
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

        # ── Passo 6: Verificar login ─────────────────────────────────
        current_url = page.url
        body_text   = await page.inner_text("body")
        is_logged   = current_url.startswith(BASE_URL) or any(kw in body_text.lower() for kw in [
            "expedientes", "peticionar", "painel do advogado", "novo processo",
            "consulta processos", "meu painel",
        ])
        if not is_logged:
            result.erro = f"Login não confirmado. URL={current_url}"
            logger.error("%s %s | body[:500]=%s", tag, result.erro, body_text[:500])
            return result

        logger.info("%s ✓ Login confirmado! URL=%s", tag, current_url)

        # ── Passo 7: Navegar para cadastrar.seam ────────────────────
        # Copia exata das 3 estratégias de pje_peticionamento._fluxo_peticao_inicial
        logger.info("%s Navegando para cadastrar.seam...", tag)
        form_loaded = False

        # Tentativa 1: via menu lateral PJe (mais confiável)
        try:
            menu_clicked = await page.evaluate("""() => {
                const links = document.querySelectorAll('a, button');
                for (const a of links) {
                    const text = (a.textContent || '').trim().toLowerCase();
                    if (text.includes('abrir menu') || text.includes('menu de navegação')) {
                        a.click(); return true;
                    }
                }
                return false;
            }""")
            if menu_clicked:
                await asyncio.sleep(2)
                await page.evaluate("""() => {
                    const links = document.querySelectorAll('a');
                    for (const a of links) {
                        const text = (a.textContent || '').trim().toLowerCase();
                        if (text === 'processo' || text.includes('novo processo')) {
                            a.click(); return true;
                        }
                    }
                    return false;
                }""")
                await asyncio.sleep(1.5)
                nav_found = await page.evaluate("""() => {
                    const links = document.querySelectorAll('a');
                    for (const a of links) {
                        const text = (a.textContent || '').trim().toLowerCase();
                        const href  = (a.href || '').toLowerCase();
                        if (href.includes('cadastropeticaoinicial') ||
                            text.includes('novo processo') ||
                            text.includes('cadastrar processo') ||
                            text.includes('petição inicial')) {
                            a.click(); return true;
                        }
                    }
                    return false;
                }""")
                if nav_found:
                    logger.info("%s Navegação via menu PJe...", tag)
                    await asyncio.sleep(4)
                    form_loaded = await page.evaluate(
                        "(id) => !!document.getElementById(id)", SELECT_IDS["materia"]
                    )
        except Exception as e:
            logger.warning("%s Menu nav falhou: %s", tag, e)

        # Tentativa 2: goto direto com networkidle
        if not form_loaded:
            logger.info("%s goto direto com networkidle: %s", tag, CADASTRAR_URL)
            await page.goto(CADASTRAR_URL, wait_until="networkidle", timeout=30_000)
            await asyncio.sleep(3)
            form_loaded = await page.evaluate(
                "(id) => !!document.getElementById(id)", SELECT_IDS["materia"]
            )

        # Tentativa 3: window.location.href (preserva contexto JSF)
        if not form_loaded:
            logger.info("%s window.location.href...", tag)
            await page.evaluate(f"() => window.location.href = '{CADASTRAR_URL}'")
            try:
                await page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass
            await asyncio.sleep(3)
            form_loaded = await page.evaluate(
                "(id) => !!document.getElementById(id)", SELECT_IDS["materia"]
            )

        # Verificar presença via JavaScript (funciona independente de visibilidade)
        materia_present = form_loaded
        if not materia_present:
            body_snap = await page.inner_text("body")
            result.erro = (
                f"Formulário cadastrar.seam não carregou "
                f"(combo Matéria '{SELECT_IDS['materia']}' ausente). "
                f"URL={page.url}"
            )
            logger.error(
                "%s %s | body[:800]=%s",
                tag, result.erro, body_snap[:800],
            )
            return result

        # ── Passo 8: Selecionar Matéria → disparar AJAX Jurisdições ──
        logger.info(
            "%s Selecionando Matéria=%s para carregar combo Jurisdição...",
            tag, MATERIA_DEFAULT,
        )
        await page.evaluate(
            """([selectId, value]) => {
                const el = document.getElementById(selectId);
                if (el) {
                    el.value = value;
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }
            }""",
            [SELECT_IDS["materia"], MATERIA_DEFAULT],
        )

        # Poll: aguardar combo Jurisdição ser populado pelo AJAX A4J (máx 10s)
        for _w in range(20):
            await asyncio.sleep(0.5)
            n = await page.evaluate(
                """(selectId) => {
                    const el = document.getElementById(selectId);
                    if (!el) return 0;
                    return Array.from(el.options).filter(o =>
                        o.value &&
                        o.value !== 'org.jboss.seam.ui.NoSelectionConverter.noSelectionValue' &&
                        o.text.trim() !== ''
                    ).length;
                }""",
                SELECT_IDS["jurisdicao"],
            )
            if n > 0:
                logger.info("%s Combo Jurisdição populado (%d opções) após %.1fs", tag, n, (_w + 1) * 0.5)
                break
        else:
            logger.warning("%s Combo Jurisdição pode não ter carregado (timeout poll)", tag)

        # ── Passo 9: Extrair todas as Jurisdições ───────────────────
        all_jurisdicoes = await page.evaluate(
            """(selectId) => {
                const el = document.getElementById(selectId);
                if (!el) return [];
                return Array.from(el.options)
                    .filter(o => (
                        o.value &&
                        o.value !== 'org.jboss.seam.ui.NoSelectionConverter.noSelectionValue' &&
                        o.text.trim() !== ''
                    ))
                    .map(o => ({value: o.value, text: o.text.trim()}));
            }""",
            SELECT_IDS["jurisdicao"],
        )

        if not all_jurisdicoes:
            result.erro = (
                f"Nenhuma opção encontrada no combo Jurisdição "
                f"(id={SELECT_IDS['jurisdicao']})."
            )
            logger.error("%s %s", tag, result.erro)
            return result

        result.jurisdicoes = all_jurisdicoes
        result.total_jurisdicoes = len(all_jurisdicoes)
        logger.info("%s ✓ %d jurisdições extraídas.", tag, len(all_jurisdicoes))

        # ── Passo 10 (opcional): Classes por Jurisdição ─────────────
        if not coletar_classes:
            result.sucesso = True
            result.colhido_em = datetime.now(timezone.utc).isoformat()
            return result

        logger.info(
            "%s Coletando classes para %d jurisdições (throttle=%.1f s)...",
            tag, len(all_jurisdicoes), THROTTLE_SECS,
        )
        for i, jur in enumerate(all_jurisdicoes, start=1):
            jur_value = jur["value"]
            jur_text  = jur["text"]
            logger.info(
                "%s  [%d/%d] %s (value=%s)",
                tag, i, len(all_jurisdicoes), jur_text, jur_value,
            )

            # Selecionar jurisdição para disparar AJAX das Classes
            await page.evaluate(
                """([selectId, value]) => {
                    const el = document.getElementById(selectId);
                    if (el) {
                        el.value = value;
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""",
                [SELECT_IDS["jurisdicao"], jur_value],
            )

            # Aguardar o combo de Classes ser populado (poll em vez de sleep fixo)
            classes_combo_id = SELECT_IDS["classe"]
            for _wait in range(15):  # máx 7.5s
                await asyncio.sleep(0.5)
                n_opts = await page.evaluate(
                    """(selectId) => {
                        const el = document.getElementById(selectId);
                        if (!el) return 0;
                        return Array.from(el.options).filter(o =>
                            o.value &&
                            o.value !== 'org.jboss.seam.ui.NoSelectionConverter.noSelectionValue' &&
                            o.text.trim() !== ''
                        ).length;
                    }""",
                    classes_combo_id,
                )
                if n_opts > 0:
                    break

            classes = await page.evaluate(
                """(selectId) => {
                    const el = document.getElementById(selectId);
                    if (!el) return [];
                    return Array.from(el.options)
                        .filter(o => (
                            o.value &&
                            o.value !== 'org.jboss.seam.ui.NoSelectionConverter.noSelectionValue' &&
                            o.text.trim() !== ''
                        ))
                        .map(o => ({value: o.value, text: o.text.trim()}));
                }""",
                SELECT_IDS["classe"],
            )
            result.classes_por_jurisdicao[jur_value] = classes
            logger.info("%s    → %d classes judiciais", tag, len(classes))

            # Salvar progresso parcial a cada 10 jurisdições
            if i % 10 == 0:
                result.colhido_em = datetime.now(timezone.utc).isoformat()
                salvar_resultado(result)
                logger.info("%s  ↳ Progresso parcial salvo (%d/%d).", tag, i, len(all_jurisdicoes))

            # Throttle gentil
            await asyncio.sleep(THROTTLE_SECS)

        result.sucesso = True
        result.colhido_em = datetime.now(timezone.utc).isoformat()
        logger.info(
            "%s ✓ Coleta completa! %d jurisdições, %d com classes mapeadas.",
            tag, len(result.jurisdicoes), len(result.classes_por_jurisdicao),
        )
        return result

    except Exception as e:
        result.erro = f"Erro inesperado durante a coleta: {e}"
        logger.exception("%s %s", tag, result.erro)
        return result

    finally:
        # Fechar browser sempre
        try:
            if context:
                await context.close()
        except Exception:
            pass
        try:
            if browser:
                await browser.close()
        except Exception:
            pass
        try:
            if pw:
                await pw.stop()
        except Exception:
            pass
        _cleanup_pem_files(*(x for x in [cert_path, key_path] if x))


# ──────────────────────────────────────────────────────────────────
# Persistência
# ──────────────────────────────────────────────────────────────────

def salvar_resultado(result: ColetaComarcasResult) -> None:
    """Salva o resultado no JSON de dados e atualiza pje_cadastro_dados.py."""
    if not result.sucesso or not result.jurisdicoes:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── JSON completo ────────────────────────────────────────────────
    payload = {
        "colhido_em":          result.colhido_em,
        "tribunal":            result.tribunal,
        "total_jurisdicoes":   result.total_jurisdicoes,
        "jurisdicoes":         result.jurisdicoes,
        "classes_por_jurisdicao": result.classes_por_jurisdicao,
    }
    OUTPUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("[COMARCAS-TRF1] JSON salvo: %s (%d bytes)", OUTPUT_JSON, OUTPUT_JSON.stat().st_size)

    # ── Atualizar pje_cadastro_dados.py ─────────────────────────────
    _update_pje_cadastro_dados(result.jurisdicoes)


def _update_pje_cadastro_dados(jurisdicoes: list) -> None:
    """Reescreve o bloco `"trf1": [...]` em pje_cadastro_dados.py."""
    if not PJE_CADASTRO_PY.exists():
        logger.warning(
            "[COMARCAS-TRF1] pje_cadastro_dados.py não encontrado em: %s", PJE_CADASTRO_PY
        )
        return

    existing = PJE_CADASTRO_PY.read_text(encoding="utf-8")

    # Construir novo bloco da lista trf1
    lines = ['    "trf1": [\n']
    for j in jurisdicoes:
        v = j["value"]
        t = j["text"].replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'        {{"value": "{v}", "text": "{t}"}},\n')
    lines.append("    ],\n")

    # Regex: captura desde `"trf1": [` até o fechamento `],` mais próximo
    pattern = re.compile(r'"trf1":\s*\[.*?\],', re.DOTALL)
    m = pattern.search(existing)
    if not m:
        logger.warning(
            '[COMARCAS-TRF1] Bloco "trf1": [...] não encontrado em pje_cadastro_dados.py'
        )
        return

    updated = existing[: m.start()] + "".join(lines).rstrip("\n") + existing[m.end() :]
    PJE_CADASTRO_PY.write_text(updated, encoding="utf-8")
    logger.info(
        "[COMARCAS-TRF1] pje_cadastro_dados.py atualizado com %d jurisdições.",
        len(jurisdicoes),
    )


# ──────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────

async def main_coletar(
    pfx_path: Optional[str] = None,
    pfx_password: Optional[str] = None,
    totp_secret: Optional[str] = None,
    coletar_classes: bool = True,
) -> ColetaComarcasResult:
    """Ponto de entrada principal: lê PFX do disco, coleta e salva resultado."""
    from app.config import settings

    pfx_path     = pfx_path     or os.environ.get("PJE_PFX_PATH",     settings.pje_pfx_path)
    pfx_password = pfx_password or os.environ.get("PJE_PFX_PASSWORD", settings.pje_pfx_password)
    totp_secret  = totp_secret  or os.environ.get("PJE_TOTP_SECRET",  settings.pje_totp_secret) or None

    if not os.path.exists(pfx_path):
        logger.error("[COMARCAS-TRF1] Certificado PFX não encontrado: %s", pfx_path)
        result = ColetaComarcasResult()
        result.erro = f"Arquivo PFX não encontrado: {pfx_path}"
        return result

    pfx_bytes = Path(pfx_path).read_bytes()
    logger.info(
        "[COMARCAS-TRF1] PFX carregado: %s (%d bytes)", pfx_path, len(pfx_bytes)
    )

    result = await coletar_jurisdicoes_trf1(
        pfx_bytes=pfx_bytes,
        pfx_password=pfx_password,
        coletar_classes=coletar_classes,
        totp_secret=totp_secret,
    )

    if result.sucesso:
        salvar_resultado(result)
    else:
        logger.error("[COMARCAS-TRF1] Coleta falhou: %s", result.erro)

    return result


if __name__ == "__main__":
    # Execução standalone: python3 -m app.scrapers.coletar_comarcas
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    # --no-classes: só jurisdições (mais rápido)
    coletar_classes = "--no-classes" not in sys.argv

    r = asyncio.run(main_coletar(coletar_classes=coletar_classes))
    if r.sucesso:
        print(f"\n✓ Sucesso! {r.total_jurisdicoes} jurisdições coletadas em {r.colhido_em}")
        print(f"  JSON salvo: {OUTPUT_JSON}")
    else:
        print(f"\n✗ Falha: {r.erro}", file=sys.stderr)
        sys.exit(1)

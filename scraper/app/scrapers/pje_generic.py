"""Generic PJe scraper — works for any tribunal running PJe (JBoss Seam + RichFaces/JSF).

All PJe consulta pública instances share the same interface:
- Same form field IDs (fPP:Decoration:numeroOAB, fPP:Decoration:estadoComboOAB, etc.)
- Same search flow (fill OAB + UF → executarPesquisa() → AJAX results)
- Same detail page structure (partes, movimentações, documentos)
- Same PDF download flow (Gerar PDF → expect_download)

Differences between tribunals are ONLY in the base URL.

Provides 3 granular functions for the pipeline:
1. listar_processos_pje()  — search OAB → return list of numero/classe/assunto
2. detalhar_processo_pje() — open one processo → extract partes + movimentações + doc links
3. baixar_documento_pje()  — download one document → upload to S3

Plus the legacy monolithic consultar_oab_pje() for backward compatibility.
"""

import asyncio
import logging
import re
from dataclasses import dataclass

from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeout

from app.s3_client import upload_file
from app.browser_pool import browser_pool, human_delay
from app.config import get_throttle

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# Tribunal configs — each is just a URL; PJe interface is the same
# ──────────────────────────────────────────────────────────────────

@dataclass
class PJeTribunalConfig:
    """Configuration for a PJe tribunal."""
    code: str          # e.g. "trf1", "trf3", "tjce"
    name: str          # Human-readable name
    base_url: str      # Base URL (without /ConsultaPublica/listView.seam)
    search_url: str    # Full URL to the search page


# Registry of all PJe tribunals
PJE_TRIBUNALS: dict[str, PJeTribunalConfig] = {
    "trf1": PJeTribunalConfig(
        code="trf1",
        name="TRF1 - 1ª Região",
        base_url="https://pje1g-consultapublica.trf1.jus.br/consultapublica",
        search_url="https://pje1g-consultapublica.trf1.jus.br/consultapublica/ConsultaPublica/listView.seam",
    ),
    "trf3": PJeTribunalConfig(
        code="trf3",
        name="TRF3 - 3ª Região (SP/MS)",
        base_url="https://pje1g.trf3.jus.br/pje",
        search_url="https://pje1g.trf3.jus.br/pje/ConsultaPublica/listView.seam",
    ),
    "trf5": PJeTribunalConfig(
        code="trf5",
        name="TRF5 - 5ª Região (Nordeste)",
        base_url="https://pje1g.trf5.jus.br/pjeconsulta",
        search_url="https://pje1g.trf5.jus.br/pjeconsulta/ConsultaPublica/listView.seam",
    ),
    "trf6": PJeTribunalConfig(
        code="trf6",
        name="TRF6 - 6ª Região (MG)",
        base_url="https://pje1g.trf6.jus.br/consultapublica",
        search_url="https://pje1g.trf6.jus.br/consultapublica/ConsultaPublica/listView.seam",
    ),
    "tjce": PJeTribunalConfig(
        code="tjce",
        name="TJCE - Tribunal de Justiça do Ceará (1º Grau)",
        base_url="https://pje.tjce.jus.br/pje1grau",
        search_url="https://pje.tjce.jus.br/pje1grau/ConsultaPublica/listView.seam",
    ),
    "tjce2g": PJeTribunalConfig(
        code="tjce2g",
        name="TJCE - Tribunal de Justiça do Ceará (2º Grau)",
        base_url="https://pje.tjce.jus.br/pje2grau",
        search_url="https://pje.tjce.jus.br/pje2grau/ConsultaPublica/listView.seam",
    ),
}

# JSF form field IDs — standard across all PJe instances
FORM_ID = "fPP"
OAB_INPUT_ID = f"{FORM_ID}:Decoration:numeroOAB"
OAB_UF_SELECT_ID = f"{FORM_ID}:Decoration:estadoComboOAB"
SEARCH_BUTTON_ID = f"{FORM_ID}:searchProcessos"

# PDF download form IDs — fixed across PJe instances
PDF_FORM_ID = "j_id43"
PDF_BUTTON_ID = f"{PDF_FORM_ID}:downloadPDF"


# ──────────────────────────────────────────────────────────────────
# Phase 1: List processes (fast — ~10-30s)
# ──────────────────────────────────────────────────────────────────


async def listar_processos_pje(oab_numero: str, oab_uf: str, tribunal_code: str) -> dict:
    """Search a PJe tribunal by OAB number and return the list of processes.

    This is Phase 1 of the pipeline — ONLY searches and parses the list.
    Does NOT open details or download documents.

    Returns:
        {sucesso, mensagem, processos: [{numero, classe, assunto, partes, ...}], total, tribunal}
    """
    config = PJE_TRIBUNALS.get(tribunal_code.lower())
    if not config:
        return {**_error(f"Tribunal PJe '{tribunal_code}' não configurado."), "tribunal": tribunal_code}

    tag = f"[{config.code.upper()}]"
    oab_uf = oab_uf.upper().strip()
    oab_numero = oab_numero.strip()
    throttle = get_throttle(tribunal_code)

    async with browser_pool.acquire() as session:
        page = session.page
        try:
            # ── Navigate ──
            logger.info(f"{tag} Navigating to {config.search_url} | OAB={oab_numero} UF={oab_uf}")
            await page.goto(config.search_url, wait_until="domcontentloaded", timeout=120_000)
            await asyncio.sleep(5)

            # Check A4J
            a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")
            logger.info(f"{tag} A4J defined: {a4j_check}")
            if not a4j_check:
                await asyncio.sleep(5)
                a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")

            # Check captcha
            captcha = await page.query_selector(
                "[class*='h-captcha'], [class*='hcaptcha'], iframe[src*='hcaptcha']"
            )
            if captcha:
                logger.warning(f"{tag} CAPTCHA detected!")
                return {
                    **_error(f"Captcha detectado no site do {config.name}."),
                    "tribunal": config.code,
                    "blocked": True,
                }

            await human_delay(0.3, 0.8)

            # Fill OAB
            oab_input = page.locator(f"[id='{OAB_INPUT_ID}']")
            await oab_input.wait_for(state="visible", timeout=10_000)
            await oab_input.fill(oab_numero)
            logger.info(f"{tag} OAB filled: {oab_numero}")
            await human_delay(0.2, 0.5)

            # Select UF
            await _select_uf_select2(page, oab_uf)
            logger.info(f"{tag} UF selected: {oab_uf}")
            await human_delay(0.3, 0.6)

            # Verify + search
            pre_oab = await page.evaluate(f"() => document.getElementById('{OAB_INPUT_ID}')?.value")
            pre_uf = await page.evaluate(f"() => document.getElementById('{OAB_UF_SELECT_ID}')?.value")
            logger.info(f"{tag} Pre-click values: OAB={pre_oab!r} UF={pre_uf!r}")

            if not a4j_check:
                return {**_error(f"A4J/RichFaces não inicializou no {config.name}."), "tribunal": config.code}

            await page.evaluate("() => executarPesquisa()")
            logger.info(f"{tag} executarPesquisa() called")

            # Wait for AJAX
            try:
                await page.wait_for_function(
                    """() => {
                        const text = document.body.innerText;
                        const match = text.match(/(\\d+)\\s+resultados?\\s+encontrados?/);
                        return match && parseInt(match[1]) > 0;
                    }""",
                    timeout=30_000,
                )
                logger.info(f"{tag} AJAX response received — results found!")
            except PlaywrightTimeout:
                logger.warning(f"{tag} AJAX timeout after 30s")
            await asyncio.sleep(2)

            # Parse total
            body_text = await page.inner_text("body")
            total_match = re.search(r"(\d+)\s*resultados?\s*encontrados?", body_text)
            total = int(total_match.group(1)) if total_match else 0

            if total == 0:
                return {
                    "sucesso": True,
                    "mensagem": f"Nenhum processo encontrado para OAB {oab_numero}/{oab_uf} no {config.name}.",
                    "processos": [],
                    "total": 0,
                    "tribunal": config.code,
                }

            # Parse list (no details, no docs)
            processos = await _parse_results(page, tag)
            logger.info(f"{tag} list_parsed total={total} parsed={len(processos)}")

            return {
                "sucesso": True,
                "mensagem": f"Encontrados {total} processo(s) para OAB {oab_numero}/{oab_uf} no {config.name}.",
                "processos": processos,
                "total": total or len(processos),
                "tribunal": config.code,
            }

        except PlaywrightTimeout as e:
            logger.error(f"{tag} timeout oab={oab_numero} uf={oab_uf} error={e}")
            return {**_error(f"Timeout ao acessar o site do {config.name}."), "tribunal": config.code}
        except Exception as e:
            logger.error(f"{tag} error={e} oab={oab_numero}")
            return {**_error(f"Erro ao consultar {config.name}: {e}"), "tribunal": config.code}


# ──────────────────────────────────────────────────────────────────
# Phase 2: Detail one process (~10-20s)
# ──────────────────────────────────────────────────────────────────


async def detalhar_processo_pje(
    tribunal_code: str, numero: str, oab_numero: str, oab_uf: str
) -> dict:
    """Open the search, find a specific process, and extract its details.

    This is Phase 2 — extracts partes, movimentações, and doc LINKS (not downloads).

    Returns:
        {sucesso, numero, partes_detalhadas, movimentacoes, doc_links: [{index, description, url, id_processo_doc}]}
    """
    config = PJE_TRIBUNALS.get(tribunal_code.lower())
    if not config:
        return {"sucesso": False, "mensagem": f"Tribunal '{tribunal_code}' não configurado.", "numero": numero}

    tag = f"[{config.code.upper()}]"
    throttle = get_throttle(tribunal_code)

    async with browser_pool.acquire() as session:
        page = session.page
        context = session.context

        try:
            # Navigate and search for the process
            logger.info(f"{tag} detail: navigating for {numero}")
            await page.goto(config.search_url, wait_until="domcontentloaded", timeout=90_000)
            await asyncio.sleep(5)

            a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")
            if not a4j_check:
                await asyncio.sleep(5)

            await human_delay(0.3, 0.8)

            # Fill OAB and search
            oab_input = page.locator(f"[id='{OAB_INPUT_ID}']")
            await oab_input.wait_for(state="visible", timeout=10_000)
            await oab_input.fill(oab_numero.strip())
            await human_delay(0.2, 0.5)
            await _select_uf_select2(page, oab_uf.upper().strip())
            await human_delay(0.3, 0.6)

            a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")
            if not a4j_check:
                return {"sucesso": False, "mensagem": "A4J não inicializou", "numero": numero}

            await page.evaluate("() => executarPesquisa()")
            try:
                await page.wait_for_function(
                    """() => {
                        const text = document.body.innerText;
                        const match = text.match(/(\\d+)\\s+resultados?\\s+encontrados?/);
                        return match && parseInt(match[1]) > 0;
                    }""",
                    timeout=30_000,
                )
            except PlaywrightTimeout:
                pass
            await asyncio.sleep(2)

            # Find the specific process in the results
            detail_links = await page.query_selector_all("a[title='Ver detalhes do processo']")
            if not detail_links:
                detail_links = await page.query_selector_all("a:has-text('Ver detalhes')")

            # Match by numero
            target_link = None
            rows = await page.query_selector_all("tbody tr")
            for i, row in enumerate(rows):
                row_text = await row.inner_text()
                if numero in row_text and i < len(detail_links):
                    target_link = detail_links[i]
                    break

            if not target_link and detail_links:
                target_link = detail_links[0]

            if not target_link:
                return {
                    "sucesso": False,
                    "mensagem": f"Processo {numero} não encontrado nos resultados.",
                    "numero": numero,
                }

            # Open detail page and extract data + doc links
            result = await _extract_process_detail_with_doc_links(
                context, page, target_link, numero, tag
            )
            result["sucesso"] = True
            result["numero"] = numero
            return result

        except PlaywrightTimeout as e:
            logger.error(f"{tag} detail_timeout numero={numero} error={e}")
            return {"sucesso": False, "mensagem": f"Timeout: {e}", "numero": numero}
        except Exception as e:
            logger.error(f"{tag} detail_error numero={numero} error={e}")
            return {"sucesso": False, "mensagem": f"Erro: {e}", "numero": numero}


# ──────────────────────────────────────────────────────────────────
# Phase 3: Download one document (~5-30s)
# ──────────────────────────────────────────────────────────────────


async def baixar_documento_pje(
    tribunal_code: str, numero: str, doc_url: str,
    doc_index: int = 0, doc_description: str = "",
) -> dict:
    """Navigate to a document viewer URL, download the PDF, upload to S3.

    This is Phase 3 — downloads ONE document.

    Returns:
        {sucesso, numero, doc_id, s3_url, tamanho_bytes, nome, tipo}
    """
    config = PJE_TRIBUNALS.get(tribunal_code.lower())
    if not config:
        return {"sucesso": False, "mensagem": f"Tribunal '{tribunal_code}' não configurado."}

    tag = f"[{config.code.upper()}]"

    async with browser_pool.acquire() as session:
        page = session.page
        try:
            # Make relative URLs absolute
            if doc_url.startswith("/"):
                doc_url = f"{config.base_url.rstrip('/')}{doc_url}"
                logger.info(f"{tag} doc_url_made_absolute: {doc_url}")

            logger.info(f"{tag} doc_download: navigating to {doc_url}")
            await page.goto(doc_url, wait_until="domcontentloaded", timeout=30_000)
            await asyncio.sleep(2)

            # Extract doc ID from URL
            id_match = re.search(r"idProcessoDoc=(\d+)", doc_url)
            doc_id = id_match.group(1) if id_match else f"unknown_{doc_index}"

            logger.info(f"{tag} doc_viewer_opened url={doc_url} numero={numero}")

            # Download PDF
            pdf_bytes = await _download_pdf(page, tag)

            if not pdf_bytes or len(pdf_bytes) < 100:
                logger.warning(f"{tag} pdf_empty doc_id={doc_id}")
                return {
                    "sucesso": False,
                    "mensagem": "PDF vazio ou muito pequeno",
                    "numero": numero,
                    "doc_id": doc_id,
                }

            # Upload to S3
            safe_numero = re.sub(r"[^\d\-.]", "", numero)
            s3_key = f"processos/{safe_numero}/documentos/{doc_id}.pdf"

            s3_url = upload_file(s3_key, pdf_bytes, "application/pdf")
            logger.info(f"{tag} doc_uploaded key={s3_key} size={len(pdf_bytes)}")

            return {
                "sucesso": True,
                "mensagem": "Documento baixado e enviado ao S3.",
                "numero": numero,
                "doc_id": doc_id,
                "s3_url": s3_url,
                "tamanho_bytes": len(pdf_bytes),
                "nome": doc_description or f"documento_{doc_index}",
                "tipo": _guess_document_type(doc_description),
            }

        except Exception as e:
            logger.error(f"{tag} doc_download_error numero={numero} url={doc_url} error={e}")
            return {"sucesso": False, "mensagem": f"Erro: {e}", "numero": numero}


# ──────────────────────────────────────────────────────────────────
# Legacy monolithic function (backward compat — deprecated)
# ──────────────────────────────────────────────────────────────────


async def consultar_oab_pje(oab_numero: str, oab_uf: str, tribunal_code: str) -> dict:
    """DEPRECATED: Monolithic scrape — use the granular pipeline instead.

    Kept for backward compatibility with old /scrape/consultar-oab endpoint.
    """
    config = PJE_TRIBUNALS.get(tribunal_code.lower())
    if not config:
        return _error(f"Tribunal PJe '{tribunal_code}' não configurado.")

    tag = f"[{config.code.upper()}]"
    oab_uf = oab_uf.upper().strip()
    oab_numero = oab_numero.strip()

    async with browser_pool.acquire() as session:
        page = session.page
        context = session.context

        try:
            # ── PHASE 1: SEARCH ──
            logger.info(f"{tag} Navigating to {config.search_url} | OAB={oab_numero} UF={oab_uf}")
            await page.goto(config.search_url, wait_until="domcontentloaded", timeout=90_000)
            title = await page.title()
            logger.info(f"{tag} Page loaded: {title}")

            # Wait for JS (A4J/RichFaces) to initialize
            await asyncio.sleep(5)

            console_msgs = []
            page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

            # Check A4J availability
            a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")
            logger.info(f"{tag} A4J defined: {a4j_check}")

            if not a4j_check:
                logger.warning(f"{tag} A4J not found, waiting 5s extra...")
                await asyncio.sleep(5)
                a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")
                logger.info(f"{tag} A4J after extra wait: {a4j_check}")

            # Check for captcha
            captcha = await page.query_selector(
                "[class*='h-captcha'], [class*='hcaptcha'], iframe[src*='hcaptcha']"
            )
            if captcha:
                logger.warning(f"{tag} CAPTCHA detected!")
                return _error(f"Captcha detectado no site do {config.name}.")

            await human_delay(0.3, 0.8)

            # Wait for OAB input
            oab_input = page.locator(f"[id='{OAB_INPUT_ID}']")
            await oab_input.wait_for(state="visible", timeout=10_000)

            # Fill OAB number
            await oab_input.fill(oab_numero)
            logger.info(f"{tag} OAB filled: {oab_numero}")
            await human_delay(0.2, 0.5)

            # Select UF via Select2 dropdown
            await _select_uf_select2(page, oab_uf)
            logger.info(f"{tag} UF selected: {oab_uf}")
            await human_delay(0.3, 0.6)

            # Verify values
            pre_oab = await page.evaluate(f"() => document.getElementById('{OAB_INPUT_ID}')?.value")
            pre_uf = await page.evaluate(f"() => document.getElementById('{OAB_UF_SELECT_ID}')?.value")
            logger.info(f"{tag} Pre-click values: OAB={pre_oab!r} UF={pre_uf!r}")

            # Click Pesquisar
            pesquisar_btn = page.locator(f"[id='{SEARCH_BUTTON_ID}']")
            await pesquisar_btn.wait_for(state="visible", timeout=10_000)

            if not a4j_check:
                logger.error(f"{tag} A4J not available — cannot submit search")
                return _error(f"A4J/RichFaces não inicializou no {config.name}.")

            # Call executarPesquisa() directly (bypasses onclick return issue)
            await page.evaluate("() => executarPesquisa()")
            logger.info(f"{tag} executarPesquisa() called")

            # Wait for AJAX response
            try:
                await page.wait_for_function(
                    """() => {
                        const text = document.body.innerText;
                        const match = text.match(/(\\d+)\\s+resultados?\\s+encontrados?/);
                        return match && parseInt(match[1]) > 0;
                    }""",
                    timeout=30_000,
                )
                logger.info(f"{tag} AJAX response received — results found!")
            except PlaywrightTimeout:
                logger.warning(f"{tag} AJAX timeout after 30s. Console msgs: {console_msgs[:5]}")
            await asyncio.sleep(2)

            # Screenshot for debugging
            try:
                await page.screenshot(path=f"/tmp/{config.code}_after_search.png", full_page=True)
            except Exception:
                pass

            # Check for "no results"
            body_text = await page.inner_text("body")
            total_match = re.search(r"(\d+)\s*resultados?\s*encontrados?", body_text)
            total = int(total_match.group(1)) if total_match else 0

            if total == 0:
                return {
                    "sucesso": True,
                    "mensagem": f"Nenhum processo encontrado para OAB {oab_numero}/{oab_uf} no {config.name}.",
                    "processos": [],
                    "total": 0,
                }

            # ── PHASE 2: PARSE LIST ──
            processos = await _parse_results(page, tag)
            logger.info(f"{tag} list_parsed total={total} parsed={len(processos)}")

            # ── PHASE 3: DETAILS + DOCUMENTS ──
            detail_links = await page.query_selector_all("a[title='Ver detalhes do processo']")
            if not detail_links:
                detail_links = await page.query_selector_all("a:has-text('Ver detalhes')")

            for i, processo in enumerate(processos):
                if i >= len(detail_links):
                    break

                try:
                    detail_data = await _extract_process_detail(
                        context, page, detail_links[i], processo["numero"], tag
                    )
                    processo.update(detail_data)
                except Exception as e:
                    logger.warning(f"{tag} detail_error numero={processo.get('numero')} error={e}")

                await human_delay(2.0, 4.0)

            return {
                "sucesso": True,
                "mensagem": f"Encontrados {total} processo(s) para OAB {oab_numero}/{oab_uf} no {config.name}.",
                "processos": processos,
                "total": total or len(processos),
            }

        except PlaywrightTimeout as e:
            logger.error(f"{tag} timeout oab={oab_numero} uf={oab_uf} error={e}")
            return _error(f"Timeout ao acessar o site do {config.name}. Tente novamente.")
        except Exception as e:
            logger.error(f"{tag} error={e} oab={oab_numero}")
            return _error(f"Erro ao consultar {config.name}: {e}")


# ──────────────────────────────────────────────────────────────────
# Select2 UF dropdown
# ──────────────────────────────────────────────────────────────────


async def _select_uf_select2(page: Page, uf: str) -> None:
    """Select UF using Select2 dropdown (standard across all PJe instances)."""
    # Strategy 1: Click Select2 container
    select2_container = await page.query_selector(
        f"[id='{OAB_UF_SELECT_ID}'] + .select2-container, "
        f"[id='{OAB_UF_SELECT_ID}'] ~ .select2-container, "
        f".select2-container[id*='estadoComboOAB']"
    )

    if select2_container:
        await select2_container.click()
        await asyncio.sleep(0.5)

        option = page.locator(f".select2-results__option:has-text('{uf}')")
        if await option.count() > 0:
            await option.first.click()
            await asyncio.sleep(0.3)
            return

    # Strategy 2: combobox role selector
    try:
        uf_combo = page.get_by_role("combobox", name="UF")
        if await uf_combo.count() > 0:
            await uf_combo.click()
            await asyncio.sleep(0.5)

            uf_item = page.get_by_role("treeitem", name=uf)
            if await uf_item.count() > 0:
                await uf_item.click()
                await asyncio.sleep(0.3)
                return
    except Exception:
        pass

    # Strategy 3: Set native <select> via JS
    await page.evaluate(
        """([selectId, uf]) => {
            const sel = document.getElementById(selectId);
            if (!sel) return;
            for (const opt of sel.options) {
                if (opt.text.trim() === uf) {
                    sel.value = opt.value;
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    return;
                }
            }
        }""",
        [OAB_UF_SELECT_ID, uf],
    )


# ──────────────────────────────────────────────────────────────────
# Detail Extraction
# ──────────────────────────────────────────────────────────────────


async def _extract_process_detail(
    context: BrowserContext, list_page: Page, link, numero: str, tag: str
) -> dict:
    """Click 'Ver detalhes' → new tab → extract parties, movements, documents."""
    result = {
        "partes_detalhadas": [],
        "movimentacoes": [],
        "documentos": [],
    }

    async with context.expect_page(timeout=30_000) as popup_info:
        await link.click()

    detail_page = await popup_info.value
    await detail_page.wait_for_load_state("domcontentloaded", timeout=30_000)

    try:
        logger.info(f"{tag} detail_opened numero={numero} url={detail_page.url}")
        await asyncio.sleep(2)

        result["partes_detalhadas"] = await _extract_parties(detail_page)
        result["movimentacoes"] = await _extract_movements_paginated(detail_page)
        result["documentos"] = await _extract_and_download_documents(
            context, detail_page, numero, tag
        )

    except Exception as e:
        logger.error(f"{tag} detail_extraction_error numero={numero} error={e}")
    finally:
        await detail_page.close()

    return result


async def _extract_process_detail_with_doc_links(
    context: BrowserContext, list_page: Page, link, numero: str, tag: str
) -> dict:
    """Like _extract_process_detail, but returns doc LINKS instead of downloading.

    Used by Phase 2 (detalhar_processo_pje) so documents are NOT downloaded yet.
    """
    result = {
        "partes_detalhadas": [],
        "movimentacoes": [],
        "doc_links": [],
    }

    async with context.expect_page(timeout=30_000) as popup_info:
        await link.click()

    detail_page = await popup_info.value
    await detail_page.wait_for_load_state("domcontentloaded", timeout=30_000)

    try:
        logger.info(f"{tag} detail_with_links_opened numero={numero} url={detail_page.url}")
        await asyncio.sleep(2)

        result["partes_detalhadas"] = await _extract_parties(detail_page)
        result["movimentacoes"] = await _extract_movements_paginated(detail_page)

        # Extract doc links WITHOUT downloading
        doc_links_elements = await detail_page.query_selector_all(
            "a:has-text('Visualizar documentos'), "
            "a:has-text('Visualizar Documentos')"
        )

        for i, doc_link_el in enumerate(doc_links_elements):
            try:
                href = await doc_link_el.get_attribute("href")
                onclick = await doc_link_el.get_attribute("onclick")

                # Get description from the row
                row_text = await doc_link_el.evaluate("""el => {
                    const row = el.closest('tr');
                    if (row) return row.innerText.replace(/\\s+/g, ' ').trim();
                    const td = el.closest('td');
                    if (td) return td.innerText.replace(/\\s+/g, ' ').trim();
                    return el.parentElement?.innerText?.trim() || '';
                }""")
                description = re.sub(r"(?i)visualizar\s+documentos?", "", row_text).strip()[:200]

                # Try to extract the URL that would open the doc viewer
                # PJe doc links use openPopUp('...', 'https://...') or window.open('...')
                doc_url = href or ""
                if (not doc_url or doc_url == "#") and onclick:
                    # Match openPopUp('id', 'url') pattern (most common in PJe)
                    url_match = re.search(r"openPopUp\([^,]+,\s*['\"]([^'\"]+)", onclick)
                    if not url_match:
                        # Fallback: window.open('url')
                        url_match = re.search(r"window\.open\(['\"]([^'\"]+)", onclick)
                    if url_match:
                        doc_url = url_match.group(1).replace("&amp;", "&")

                # If we can't get the URL from href/onclick, we need to click and get from new tab
                if not doc_url or doc_url == "#":
                    try:
                        async with context.expect_page(timeout=10_000) as doc_page_info:
                            await doc_link_el.click()
                        doc_page = await doc_page_info.value
                        await doc_page.wait_for_load_state("domcontentloaded", timeout=10_000)
                        doc_url = doc_page.url
                        await doc_page.close()
                    except Exception:
                        continue

                id_match = re.search(r"idProcessoDoc=(\d+)", doc_url)
                doc_id = id_match.group(1) if id_match else None

                # Only keep actual document viewer URLs, not receipt/certidão links
                if doc_url and (
                    "documentoSemLoginHTML" in doc_url
                    or "idProcessoDoc" in doc_url
                ):
                    result["doc_links"].append({
                        "index": i,
                        "description": description or f"documento_{i}",
                        "url": doc_url,
                        "id_processo_doc": doc_id,
                    })
                else:
                    logger.debug(f"{tag} skipping_non_document_link url={doc_url[:100] if doc_url else 'none'}")
            except Exception as e:
                logger.warning(f"{tag} doc_link_extract_error index={i} error={e}")

        logger.info(f"{tag} detail_with_links numero={numero} doc_links={len(result['doc_links'])}")

    except Exception as e:
        logger.error(f"{tag} detail_with_links_error numero={numero} error={e}")
    finally:
        await detail_page.close()

    return result


async def _extract_parties(page: Page) -> list[dict]:
    """Extract parties (partes) from the detail page."""
    parties = []
    body_text = await page.inner_text("body")

    for polo_name, polo_label in [
        ("Polo ativo", "ATIVO"),
        ("Polo Passivo", "PASSIVO"),
        ("polo ativo", "ATIVO"),
        ("polo passivo", "PASSIVO"),
        ("Outros participantes", "OUTROS"),
    ]:
        idx = body_text.find(polo_name)
        if idx < 0:
            continue

        next_polo = len(body_text)
        for marker in ["Polo ativo", "Polo Passivo", "Outros participantes",
                        "polo ativo", "polo passivo", "Outros interessados",
                        "Movimentações", "Documentos juntados"]:
            found = body_text.find(marker, idx + len(polo_name))
            if found > 0:
                next_polo = min(next_polo, found)

        block = body_text[idx:next_polo]
        lines = [l.strip() for l in block.split("\n") if l.strip()]

        for line in lines[1:]:
            if not line or line == polo_name:
                continue
            if any(skip in line.lower() for skip in [
                "movimentações", "documentos", "polo ", "outros ",
                "data da distribuição", "classe judicial", "assunto",
                "participante", "situação", "advogado(a)",
            ]):
                if any(skip in line.lower() for skip in [
                    "movimentações", "documentos", "polo ", "outros ",
                    "data da distribuição", "classe judicial", "assunto",
                ]):
                    break
                continue

            oab_match = re.search(r"OAB\s*[:\s]*([A-Z]{2})\s*(\d+)", line)
            oab = f"{oab_match.group(1)}{oab_match.group(2)}" if oab_match else None

            cpf_match = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2})", line)
            cnpj_match = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", line)
            doc = cpf_match.group(1) if cpf_match else (cnpj_match.group(1) if cnpj_match else None)

            role_match = re.search(r"\(([^)]+)\)\s*$", line)
            papel = role_match.group(1) if role_match else None

            nome = line
            if role_match:
                nome = nome[:role_match.start()].strip()
            if oab_match:
                nome = nome[:oab_match.start()].strip()

            nome = nome.strip(" -,.")
            if len(nome) < 3:
                continue

            party = {"polo": polo_label, "nome": nome}
            if papel:
                party["papel"] = papel
            if oab:
                party["oab"] = oab
            if doc:
                party["documento"] = doc

            parties.append(party)

    return parties


async def _extract_movements_paginated(page: Page) -> list[dict]:
    """Extract movement history with pagination (15 items/page)."""
    all_movements = []
    page_num = 0

    while True:
        page_num += 1
        movements = await _extract_movements_current_page(page)
        all_movements.extend(movements)

        if len(movements) < 15:
            break

        next_btn = await page.query_selector(
            "a[title='Próxima página'], "
            "a:has(img[alt*='Próxima']), "
            "img[alt*='Próxima'], "
            "[id*='movimentacao'] a:has-text('»')"
        )
        if not next_btn:
            break

        await next_btn.click()
        await asyncio.sleep(1.5)

        if page_num >= 10:
            break

    return all_movements


async def _extract_movements_current_page(page: Page) -> list[dict]:
    """Extract movements from the current page of the movements table."""
    movements = []

    rows = await page.query_selector_all(
        "div:has(h3:has-text('Movimentações')) table tbody tr, "
        "[id*='movimentacoes'] table tbody tr, "
        "table[id*='Movimentacao'] tbody tr"
    )

    if rows:
        for row in rows:
            cells = await row.query_selector_all("td")
            if not cells:
                continue
            mov_text = (await cells[0].inner_text()).strip() if len(cells) > 0 else ""
            doc_text = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""

            doc_link = await cells[1].query_selector("a") if len(cells) > 1 else None

            if mov_text:
                movements.append({
                    "descricao": mov_text,
                    "documento_vinculado": doc_text if doc_text else None,
                    "tem_documento": doc_link is not None,
                })
        return movements

    # Fallback: text-based parsing
    body_text = await page.inner_text("body")
    pattern = r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)\s*[-–]\s*(.+?)(?:\n|$)"
    matches = re.findall(pattern, body_text)
    for date_str, desc in matches[:50]:
        movements.append({
            "descricao": f"{date_str} - {desc.strip()}",
            "documento_vinculado": None,
            "tem_documento": False,
        })

    return movements


# ──────────────────────────────────────────────────────────────────
# Document Extraction & Download
# ──────────────────────────────────────────────────────────────────


async def _extract_and_download_documents(
    context: BrowserContext, detail_page: Page, numero: str, tag: str
) -> list[dict]:
    """Extract documents from 'Documentos juntados ao processo' table."""
    documents = []

    doc_links = await detail_page.query_selector_all(
        "a:has-text('Visualizar documentos'), "
        "a:has-text('Visualizar Documentos')"
    )

    if not doc_links:
        logger.debug(f"{tag} no_doc_links numero={numero}")
        return documents

    logger.info(f"{tag} doc_links_found numero={numero} count={len(doc_links)}")

    for i, doc_link in enumerate(doc_links):
        try:
            doc_data = await _download_single_document(context, doc_link, numero, i, tag)
            if doc_data:
                documents.append(doc_data)
        except Exception as e:
            logger.warning(f"{tag} doc_error numero={numero} index={i} error={e}")

        await human_delay(1.5, 3.0)

    return documents


async def _download_single_document(
    context: BrowserContext, doc_link, numero: str, index: int, tag: str
) -> dict | None:
    """Open document viewer tab, download PDF, upload to S3."""

    row_text = await doc_link.evaluate("""el => {
        const row = el.closest('tr');
        if (row) return row.innerText.replace(/\\s+/g, ' ').trim();
        const td = el.closest('td');
        if (td) return td.innerText.replace(/\\s+/g, ' ').trim();
        return el.parentElement?.innerText?.trim() || '';
    }""")
    doc_description = re.sub(r"(?i)visualizar\s+documentos?", "", row_text).strip()[:200]
    if not doc_description:
        doc_description = f"documento_{index}"

    async with context.expect_page(timeout=30_000) as doc_page_info:
        await doc_link.click()

    doc_page = await doc_page_info.value
    await doc_page.wait_for_load_state("domcontentloaded", timeout=30_000)
    await asyncio.sleep(2)

    try:
        doc_url = doc_page.url
        logger.info(f"{tag} doc_viewer_opened url={doc_url} numero={numero}")

        id_match = re.search(r"idProcessoDoc=(\d+)", doc_url)
        doc_id = id_match.group(1) if id_match else f"unknown_{index}"

        pdf_bytes = await _download_pdf(doc_page, tag)

        if not pdf_bytes or len(pdf_bytes) < 100:
            logger.warning(f"{tag} pdf_empty doc_id={doc_id}")
            return None

        safe_numero = re.sub(r"[^\d\-.]", "", numero)
        s3_key = f"processos/{safe_numero}/documentos/{doc_id}.pdf"

        try:
            s3_url = upload_file(s3_key, pdf_bytes, "application/pdf")
            logger.info(f"{tag} doc_uploaded key={s3_key} size={len(pdf_bytes)}")

            return {
                "nome": doc_description,
                "tipo": _guess_document_type(doc_description),
                "s3_url": s3_url,
                "tamanho_bytes": len(pdf_bytes),
                "id_processo_doc": doc_id,
            }
        except Exception as e:
            logger.error(f"{tag} s3_upload_error key={s3_key} error={e}")
            return None

    finally:
        await doc_page.close()


async def _download_pdf(doc_page: Page, tag: str) -> bytes | None:
    """Download PDF from PJe document viewer page (documentoSemLoginHTML.seam).

    The page has a form (typically j_id43) with a 'Gerar PDF' link.
    The link's onclick calls jsfcljs() which submits the form with:
      - formId=formId (hidden input)
      - formId:downloadPDF=formId:downloadPDF (button param)
      - ca=<auth_token> (from URL/onclick)
      - idProcDocBin=<binary_doc_id> (from onclick)
      - javax.faces.ViewState=<viewstate>

    Strategies:
    1. Extract ca/idProcDocBin from 'Gerar PDF' onclick → POST directly
    2. Click 'Gerar PDF' and intercept download event
    3. Fallback: page.pdf() renders HTML as PDF
    """
    # Strategy 1: Extract params from 'Gerar PDF' onclick and POST directly
    try:
        pdf_bytes = await _download_pdf_via_jsf_form(doc_page, tag)
        if pdf_bytes and len(pdf_bytes) > 100:
            return pdf_bytes
    except Exception as e:
        logger.info(f"{tag} pdf_jsf_form_failed error={e}")

    # Strategy 2: Click 'Gerar PDF' button and capture download event
    try:
        pdf_btn = doc_page.locator(
            "a[id*='downloadPDF'], a:has-text('Gerar PDF'), "
            "button:has-text('Gerar PDF'), a:has-text('Download PDF')"
        )
        if await pdf_btn.count() > 0:
            async with doc_page.expect_download(timeout=60_000) as download_info:
                await pdf_btn.first.click()

            download = await download_info.value
            pdf_path = f"/tmp/pje_{download.suggested_filename or 'doc.pdf'}"
            await download.save_as(pdf_path)

            with open(pdf_path, "rb") as f:
                data = f.read()
                if data and len(data) > 100:
                    logger.info(f"{tag} pdf_downloaded_via_click size={len(data)}")
                    return data
    except Exception as e:
        logger.debug(f"{tag} pdf_download_click_failed error={e}")

    # Strategy 3: Render page as PDF (captures HTML content as-is)
    try:
        pdf_bytes = await doc_page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"},
        )
        if pdf_bytes and len(pdf_bytes) > 100:
            logger.info(f"{tag} pdf_rendered_via_page_pdf size={len(pdf_bytes)}")
            return pdf_bytes
    except Exception as e:
        logger.warning(f"{tag} pdf_page_render_failed error={e}")

    return None


async def _find_embedded_pdf(doc_page: Page, tag: str) -> bytes | None:
    """Try to find and download an embedded PDF from iframe/embed/object elements."""
    # Check for iframe with PDF src
    for selector in ["iframe[src*='.pdf']", "iframe[src*='pdf']", "embed[src*='pdf']", "object[data*='pdf']"]:
        try:
            el = doc_page.locator(selector)
            if await el.count() > 0:
                src = await el.first.get_attribute("src") or await el.first.get_attribute("data") or ""
                if src:
                    resp = await doc_page.context.request.get(src)
                    body = await resp.body()
                    if body and (body[:5] == b"%PDF-" or len(body) > 1000):
                        logger.info(f"{tag} pdf_from_embedded size={len(body)}")
                        return body
        except Exception:
            continue

    # Check for a direct PDF link (a[href*='.pdf'])
    try:
        pdf_link = doc_page.locator("a[href*='.pdf'], a[href*='download']")
        if await pdf_link.count() > 0:
            href = await pdf_link.first.get_attribute("href") or ""
            if href:
                resp = await doc_page.context.request.get(href)
                body = await resp.body()
                if body and (body[:5] == b"%PDF-" or len(body) > 1000):
                    logger.info(f"{tag} pdf_from_link size={len(body)}")
                    return body
    except Exception:
        pass

    return None


async def _download_pdf_via_jsf_form(doc_page: Page, tag: str) -> bytes | None:
    """Extract ca/idProcDocBin from 'Gerar PDF' link onclick and POST to get PDF.

    The PJe 'Gerar PDF' button calls jsfcljs(form, params, target) where params
    include 'ca' (auth token) and 'idProcDocBin' (binary document ID).
    Without these parameters, the POST returns empty/HTML instead of PDF.
    """
    try:
        # Extract all required params from the downloadPDF link's onclick
        params = await doc_page.evaluate("""() => {
            // Find the downloadPDF link by ID pattern or text
            let link = document.querySelector('a[id*="downloadPDF"]');
            if (!link) {
                // Fallback: find by text content
                const allLinks = document.querySelectorAll('a');
                for (const a of allLinks) {
                    if (a.textContent && a.textContent.includes('Gerar PDF')) {
                        link = a;
                        break;
                    }
                }
            }
            if (!link) return null;

            const onclick = link.getAttribute('onclick') || '';

            // Extract 'ca' value from onclick: 'ca':'<value>'
            const caMatch = onclick.match(/'ca'\s*:\s*'([^']+)'/);
            const ca = caMatch ? caMatch[1] : null;

            // Extract 'idProcDocBin' value: 'idProcDocBin':'<value>'
            const binMatch = onclick.match(/'idProcDocBin'\s*:\s*'([^']+)'/);
            const idProcDocBin = binMatch ? binMatch[1] : null;

            // Extract button ID: 'j_id43:downloadPDF':'j_id43:downloadPDF'
            const btnMatch = onclick.match(/'([^']*:downloadPDF)'\s*:\s*'([^']+)'/);
            const buttonId = btnMatch ? btnMatch[1] : null;

            // Get the form and its attributes
            const form = link.closest('form');
            const formId = form ? form.id : null;
            const formAction = form ? form.action : null;

            // Get ViewState
            const vs = document.querySelector('input[name="javax.faces.ViewState"]');
            const viewState = vs ? vs.value : null;

            // Also try to get 'ca' from the URL query params as fallback
            const urlParams = new URLSearchParams(window.location.search);
            const caFromUrl = urlParams.get('ca');

            return {
                ca: ca || caFromUrl,
                idProcDocBin,
                buttonId,
                formId,
                formAction,
                viewState,
                linkId: link.id,
            };
        }""")

        if not params:
            logger.debug(f"{tag} jsf_no_download_link_found")
            return None

        logger.info(f"{tag} jsf_form_params: formId={params.get('formId')} "
                    f"buttonId={params.get('buttonId')} "
                    f"has_ca={bool(params.get('ca'))} "
                    f"has_idProcDocBin={bool(params.get('idProcDocBin'))}")

        if not params.get("ca") or not params.get("idProcDocBin"):
            logger.debug(f"{tag} jsf_missing_critical_params ca={bool(params.get('ca'))} "
                         f"idProcDocBin={bool(params.get('idProcDocBin'))}")
            return None

        form_id = params["formId"] or "j_id43"
        button_id = params["buttonId"] or f"{form_id}:downloadPDF"
        view_state = params["viewState"] or "j_id4"
        form_action = params["formAction"] or doc_page.url

        # Build POST data exactly as jsfcljs() does:
        # form_id=form_id & buttonId=buttonId & ca=<token> & idProcDocBin=<id> & ViewState=<vs>
        from urllib.parse import urlencode
        post_data = urlencode({
            form_id: form_id,
            button_id: button_id,
            "ca": params["ca"],
            "idProcDocBin": params["idProcDocBin"],
            "javax.faces.ViewState": view_state,
        })

        logger.info(f"{tag} jsf_form_posting to={form_action} "
                    f"idProcDocBin={params['idProcDocBin']}")

        response = await doc_page.context.request.post(
            form_action,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": doc_page.url,
            },
            data=post_data,
        )

        if response.status == 200:
            body = await response.body()
            content_type = response.headers.get("content-type", "")
            is_pdf = (body and body[:5] == b"%PDF-") or "pdf" in content_type.lower()

            if is_pdf and len(body) > 100:
                logger.info(f"{tag} pdf_jsf_form_success size={len(body)} "
                            f"content_type={content_type}")
                return body
            else:
                logger.warning(f"{tag} pdf_jsf_form_not_pdf size={len(body)} "
                               f"content_type={content_type} starts={body[:20] if body else b''}")
        else:
            logger.warning(f"{tag} pdf_jsf_form_http_error status={response.status}")

    except Exception as e:
        logger.warning(f"{tag} pdf_jsf_form_error error={e}")

    return None


# ──────────────────────────────────────────────────────────────────
# Result List Parsing
# ──────────────────────────────────────────────────────────────────


async def _parse_results(page: Page, tag: str) -> list[dict]:
    """Parse the results table from PJe consultation page."""
    processos = []

    await page.wait_for_selector("tbody tr", state="attached", timeout=10_000)
    rows = await page.query_selector_all("tbody tr")

    for row in rows:
        try:
            cells = await row.query_selector_all("td")
            if len(cells) < 2:
                continue

            proc_text = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
            mov_text = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""

            num_match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", proc_text)
            if not num_match:
                continue

            numero = num_match.group(1)
            lines = [l.strip() for l in proc_text.split("\n") if l.strip()]

            classe = None
            assunto = None
            partes = None

            for line in lines:
                if not classe and re.match(r"^[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s]+$", line) and len(line) > 5:
                    classe = line
                    continue
                if numero in line and " - " in line:
                    parts = line.split(" - ", 1)
                    if len(parts) > 1:
                        assunto = parts[1].strip()
                    continue
                if " X " in line or " x " in line:
                    partes = line
                    continue

            ultima_mov = None
            data_mov = None
            date_match = re.search(
                r"\((\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)\)", mov_text
            )
            if date_match:
                data_mov = date_match.group(1)
                ultima_mov = mov_text[:date_match.start()].strip()
            elif mov_text:
                ultima_mov = mov_text

            processos.append({
                "numero": numero,
                "classe": classe,
                "assunto": assunto,
                "partes": partes,
                "ultima_movimentacao": ultima_mov,
                "data_ultima_movimentacao": data_mov,
                "partes_detalhadas": [],
                "movimentacoes": [],
                "documentos": [],
            })
        except Exception as e:
            logger.debug(f"{tag} parse_row_error error={e}")
            continue

    if not processos:
        processos = await _parse_results_from_text(page)

    return processos


async def _parse_results_from_text(page: Page) -> list[dict]:
    """Fallback: parse results from full page text when table selectors fail."""
    body_text = await page.inner_text("body")
    numeros = re.findall(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}", body_text)
    if not numeros:
        return []

    processos = []
    for numero in dict.fromkeys(numeros):
        idx = body_text.find(numero)
        if idx == -1:
            continue

        start = max(0, idx - 200)
        end = min(len(body_text), idx + 500)
        block = body_text[start:end]
        before = body_text[start:idx]

        classe = None
        assunto = None
        partes = None
        ultima_mov = None
        data_mov = None

        class_match = re.search(r"([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s]{10,})\s*$", before)
        if class_match:
            classe = class_match.group(1).strip()

        subject_match = re.search(re.escape(numero) + r"[^\n]*?-\s*(.+?)(?:\n|$)", block)
        if subject_match:
            assunto = subject_match.group(1).strip()

        after_num = block[block.find(numero) + len(numero):]
        party_match = re.search(r"([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s]+\s+X\s+[^\n]+)", after_num)
        if party_match:
            partes = party_match.group(1).strip()

        date_match = re.search(
            r"([^\n(]+?)\s*\((\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)\)", after_num
        )
        if date_match:
            ultima_mov = date_match.group(1).strip()
            data_mov = date_match.group(2)

        processos.append({
            "numero": numero,
            "classe": classe,
            "assunto": assunto,
            "partes": partes,
            "ultima_movimentacao": ultima_mov,
            "data_ultima_movimentacao": data_mov,
            "partes_detalhadas": [],
            "movimentacoes": [],
            "documentos": [],
        })

    return processos


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


def _error(msg: str) -> dict:
    return {"sucesso": False, "mensagem": msg, "processos": [], "total": 0}


def _guess_document_type(name: str) -> str:
    """Guess document type from its description."""
    name_lower = name.lower()
    if "sentença" in name_lower or "sentenca" in name_lower:
        return "SENTENCA"
    if "petição" in name_lower or "peticao" in name_lower:
        return "PETICAO"
    if "despacho" in name_lower:
        return "DESPACHO"
    if "decisão" in name_lower or "decisao" in name_lower:
        return "DECISAO"
    if "ato ordinatório" in name_lower or "ato ordinatorio" in name_lower:
        return "ATO_ORDINATORIO"
    if "procuração" in name_lower or "procuracao" in name_lower:
        return "PROCURACAO"
    if "certidão" in name_lower or "certidao" in name_lower:
        return "CERTIDAO"
    if "apelação" in name_lower or "apelacao" in name_lower:
        return "APELACAO"
    return "ANEXO"

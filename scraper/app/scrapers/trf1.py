"""TRF1 scraper — consulta publica PJe 1G.

Based on detailed analysis report (docs/webscraping-pje1g-trf1-relatorio.md).

Architecture: JBoss Seam + RichFaces (JSF)
- Forms via POST with javax.faces.ViewState
- Links via javascript:void() triggering JSF form submissions
- Session tokens (ca) generated per action
- Select2 dropdowns for UF
- Pagination on movements (15/page)

Flow:
1. GET listView.seam → search form
2. Fill OAB + Select2 UF + click Pesquisar → result list
3. Click "Ver detalhes" → new tab with DetalheProcesso (ca token)
4. Extract parties, movements (paginated), documents
5. Click "Visualizar documentos" → new tab → "Gerar PDF" → download → S3
"""

import asyncio
import logging
import re

from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeout

from app.s3_client import upload_file
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

TRF1_BASE_URL = "https://pje1g-consultapublica.trf1.jus.br"
TRF1_URL = f"{TRF1_BASE_URL}/consultapublica/ConsultaPublica/listView.seam"

# JSF form field IDs — verified stable across sessions (report section 3.5)
FORM_ID = "fPP"
OAB_INPUT_ID = f"{FORM_ID}:Decoration:numeroOAB"
OAB_UF_SELECT_ID = f"{FORM_ID}:Decoration:estadoComboOAB"
SEARCH_BUTTON_ID = f"{FORM_ID}:searchProcessos"

# PDF download form IDs — fixed across sessions (report section 3.5)
PDF_FORM_ID = "j_id43"
PDF_BUTTON_ID = f"{PDF_FORM_ID}:downloadPDF"

_scraper = BaseScraper()


async def consultar_oab_trf1(oab_numero: str, oab_uf: str) -> dict:
    """Scrape TRF1 public consultation: list processes, get details, download docs.

    Args:
        oab_numero: OAB registration number (e.g. "50784").
        oab_uf: State abbreviation (e.g. "CE").

    Returns:
        Dict matching ConsultarOABResponse schema.
    """
    oab_uf = oab_uf.upper().strip()
    oab_numero = oab_numero.strip()

    async with _scraper.create_session() as session:
        page = session.page
        context = session.context

        try:
            # ── PHASE 1: SEARCH ──
            logger.info(f"[TRF1] Navigating to {TRF1_URL} | OAB={oab_numero} UF={oab_uf}")
            await page.goto(TRF1_URL, wait_until="domcontentloaded", timeout=90_000)
            title = await page.title()
            logger.info(f"[TRF1] Page loaded: {title}")

            # Wait extra time for JS (A4J/RichFaces) to initialize
            # Don't use wait_for_load_state("load") — JSF pages may never fire that
            await asyncio.sleep(5)

            # Capture browser console messages for debugging
            console_msgs = []
            page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))

            # Check if A4J is available (critical for search button to work)
            a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")
            logger.info(f"[TRF1] A4J defined: {a4j_check}")

            if not a4j_check:
                # Wait more and retry — A4J may load late
                logger.warning("[TRF1] A4J not found, waiting 5s extra for JS load...")
                await asyncio.sleep(5)
                a4j_check = await page.evaluate("() => typeof A4J !== 'undefined'")
                logger.info(f"[TRF1] A4J after extra wait: {a4j_check}")

            # Check for captcha
            captcha = await page.query_selector(
                "[class*='h-captcha'], [class*='hcaptcha'], iframe[src*='hcaptcha']"
            )
            if captcha:
                logger.warning("[TRF1] CAPTCHA detected!")
                return _error("Captcha detectado no site do tribunal.")

            await _scraper.human_delay(0.3, 0.8)

            # Wait for OAB input to be ready
            oab_input = page.locator(f"[id='{OAB_INPUT_ID}']")
            await oab_input.wait_for(state="visible", timeout=10_000)

            # ── Fill OAB number ──
            await oab_input.fill(oab_numero)
            logger.info(f"[TRF1] OAB filled: {oab_numero}")
            await _scraper.human_delay(0.2, 0.5)

            # ── Select UF via Select2 dropdown ──
            await _select_uf_select2(page, oab_uf)
            logger.info(f"[TRF1] UF selected: {oab_uf}")
            await _scraper.human_delay(0.3, 0.6)

            # Verify OAB and UF values before clicking
            pre_oab = await page.evaluate(f"() => document.getElementById('{OAB_INPUT_ID}')?.value")
            pre_uf = await page.evaluate(f"() => document.getElementById('{OAB_UF_SELECT_ID}')?.value")
            logger.info(f"[TRF1] Pre-click values: OAB={pre_oab!r} UF={pre_uf!r}")

            # ── Click Pesquisar button ──
            pesquisar_btn = page.locator(f"[id='{SEARCH_BUTTON_ID}']")
            await pesquisar_btn.wait_for(state="visible", timeout=10_000)

            btn_onclick = await page.evaluate(
                f"() => document.getElementById('{SEARCH_BUTTON_ID}')?.getAttribute('onclick')"
            )
            logger.info(f"[TRF1] Button onclick attr: {btn_onclick}")

            if not a4j_check:
                logger.error("[TRF1] A4J not available — cannot submit search")
                return _error("A4J/RichFaces não inicializou. Verifique se stealth está desabilitado.")

            # Call executarPesquisa() directly — the button onclick has
            # "return executarReCaptcha();;A4J.AJAX.Submit(...)" which
            # exits before A4J.AJAX.Submit runs. executarPesquisa() calls
            # A4J.AJAX.Submit internally (captcha is disabled: if(false)).
            await page.evaluate("() => executarPesquisa()")
            logger.info("[TRF1] executarPesquisa() called")

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
                logger.info("[TRF1] AJAX response received — results found!")
            except PlaywrightTimeout:
                logger.warning(f"[TRF1] AJAX timeout after 30s. Console msgs: {console_msgs[:5]}")
            await asyncio.sleep(2)

            # Save screenshot for debugging
            try:
                await page.screenshot(path="/tmp/trf1_after_search.png", full_page=True)
                logger.info("[TRF1] Screenshot saved: /tmp/trf1_after_search.png")
            except Exception as e:
                logger.warning(f"[TRF1] Screenshot failed: {e}")

            # Log page body snippet
            body_snippet = await page.evaluate(
                "() => document.body.innerText.substring(0, 1500)"
            )
            logger.info(f"[TRF1] Post-search body (first 500 chars):\n{body_snippet[:500]}")

            # Check for "no results"
            body_text = await page.inner_text("body")
            total_match = re.search(r"(\d+)\s*resultados?\s*encontrados?", body_text)
            total = int(total_match.group(1)) if total_match else 0

            if total == 0:
                return {
                    "sucesso": True,
                    "mensagem": f"Nenhum processo encontrado para OAB {oab_numero}/{oab_uf} no TRF1.",
                    "processos": [],
                    "total": 0,
                }

            # ── PHASE 2: PARSE LIST ──
            processos = await _parse_results(page)
            logger.info("trf1_list_parsed", extra={"total": total, "parsed": len(processos)})

            # ── PHASE 3: DETAILS + DOCUMENTS FOR EACH PROCESS ──
            # Re-query "Ver detalhes" links after parsing
            detail_links = await page.query_selector_all("a[title='Ver detalhes do processo']")
            if not detail_links:
                detail_links = await page.query_selector_all("a:has-text('Ver detalhes')")

            for i, processo in enumerate(processos):
                if i >= len(detail_links):
                    break

                try:
                    detail_data = await _extract_process_detail(
                        context, page, detail_links[i], processo["numero"]
                    )
                    processo.update(detail_data)
                except Exception as e:
                    logger.warning(
                        "trf1_detail_error",
                        extra={"numero": processo.get("numero"), "error": str(e)},
                    )

                await _scraper.human_delay(2.0, 4.0)

            return {
                "sucesso": True,
                "mensagem": f"Encontrados {total} processo(s) para OAB {oab_numero}/{oab_uf} no TRF1.",
                "processos": processos,
                "total": total or len(processos),
            }

        except PlaywrightTimeout as e:
            logger.error("trf1_timeout", extra={"oab": oab_numero, "uf": oab_uf, "error": str(e)})
            return _error("Timeout ao acessar o site do TRF1. Tente novamente.")
        except Exception as e:
            logger.error("trf1_error", extra={"error": str(e), "oab": oab_numero})
            return _error(f"Erro ao consultar TRF1: {e}")


# ──────────────────────────────────────────────────────────────────
# Select2 UF dropdown
# ──────────────────────────────────────────────────────────────────


async def _select_uf_select2(page: Page, uf: str) -> None:
    """Select UF using Select2 dropdown.

    The UF dropdown on TRF1 uses Select2 over a native <select>.
    Tested via Playwright MCP: click the Select2 container to open,
    then click the matching option text.
    """
    # Strategy 1: Click the Select2 container to open dropdown, then pick option
    # NOTE: CSS selectors with ':' in IDs need escaping — use [id=...] attribute selector
    select2_container = await page.query_selector(
        f"[id='{OAB_UF_SELECT_ID}'] + .select2-container, "
        f"[id='{OAB_UF_SELECT_ID}'] ~ .select2-container, "
        f".select2-container[id*='estadoComboOAB']"
    )

    if select2_container:
        await select2_container.click()
        await asyncio.sleep(0.5)

        # Select2 opens a dropdown with results
        option = page.locator(f".select2-results__option:has-text('{uf}')")
        if await option.count() > 0:
            await option.first.click()
            await asyncio.sleep(0.3)
            return

    # Strategy 2: Use the combobox role selector (as confirmed by MCP Playwright snapshot)
    # The snapshot showed: combobox "UF" → tree → treeitem "CE"
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

    # Strategy 3: Set native <select> value via JavaScript and dispatch change event
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
    context: BrowserContext, list_page: Page, link, numero: str
) -> dict:
    """Click "Ver detalhes" → new tab → extract parties, movements, documents.

    The link triggers a JSF form submission that opens a new tab with
    DetalheProcessoConsultaPublica/listView.seam?ca={TOKEN}
    """
    result = {
        "partes_detalhadas": [],
        "movimentacoes": [],
        "documentos": [],
    }

    # Click opens a new tab via JSF form submission
    async with context.expect_page(timeout=30_000) as popup_info:
        await link.click()

    detail_page = await popup_info.value
    await detail_page.wait_for_load_state("domcontentloaded", timeout=30_000)
    await _scraper.apply_stealth(detail_page)

    try:
        logger.info("trf1_detail_opened", extra={"numero": numero, "url": detail_page.url})
        await asyncio.sleep(2)

        # Extract parties from detail page
        result["partes_detalhadas"] = await _extract_parties(detail_page)

        # Extract movements with pagination (15/page)
        result["movimentacoes"] = await _extract_movements_paginated(detail_page)

        # Extract and download documents
        result["documentos"] = await _extract_and_download_documents(
            context, detail_page, numero
        )

    except Exception as e:
        logger.error("trf1_detail_extraction_error", extra={"numero": numero, "error": str(e)})
    finally:
        await detail_page.close()

    return result


async def _extract_parties(page: Page) -> list[dict]:
    """Extract parties (partes) from the detail page.

    Looks for sections: Polo ativo, Polo Passivo, Outros participantes.
    Each party has: nome, papel (IMPETRANTE, ADVOGADO, etc.), CPF/CNPJ, OAB.
    """
    parties = []
    body_text = await page.inner_text("body")

    # Parse each polo section from the page text
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

        # Get text block for this polo (until next polo or end)
        next_polo = len(body_text)
        for marker in ["Polo ativo", "Polo Passivo", "Outros participantes",
                        "polo ativo", "polo passivo", "Outros interessados",
                        "Movimentações", "Documentos juntados"]:
            found = body_text.find(marker, idx + len(polo_name))
            if found > 0:
                next_polo = min(next_polo, found)

        block = body_text[idx:next_polo]

        # Extract individual entries — look for role indicators
        # Pattern: NAME (ROLE) or NAME - ROLE or just NAME on separate lines
        lines = [l.strip() for l in block.split("\n") if l.strip()]

        for line in lines[1:]:  # skip header
            if not line or line == polo_name:
                continue
            # Skip navigation/header lines and table headers
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

            # Extract OAB if present
            oab_match = re.search(r"OAB\s*[:\s]*([A-Z]{2})\s*(\d+)", line)
            oab = f"{oab_match.group(1)}{oab_match.group(2)}" if oab_match else None

            # Extract CPF/CNPJ if present
            cpf_match = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2})", line)
            cnpj_match = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", line)
            doc = cpf_match.group(1) if cpf_match else (cnpj_match.group(1) if cnpj_match else None)

            # Extract role in parentheses
            role_match = re.search(r"\(([^)]+)\)\s*$", line)
            papel = role_match.group(1) if role_match else None

            # Clean name (remove role, OAB, doc)
            nome = line
            if role_match:
                nome = nome[:role_match.start()].strip()
            if oab_match:
                nome = nome[:oab_match.start()].strip()

            # Skip empty or very short names
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
    """Extract movement history with pagination (15 items/page).

    Report section 4.3: Each row has date+description in first column,
    linked document in second column.
    """
    all_movements = []
    page_num = 0

    while True:
        page_num += 1
        movements = await _extract_movements_current_page(page)
        all_movements.extend(movements)

        logger.debug("trf1_movements_page", extra={"page": page_num, "count": len(movements)})

        if len(movements) < 15:
            break

        # Try to click "Next page" button
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

        if page_num >= 10:  # safety limit
            break

    return all_movements


async def _extract_movements_current_page(page: Page) -> list[dict]:
    """Extract movements from the current page of the movements table."""
    movements = []

    # Try structured table selectors first
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

            # Check if there's a document link
            doc_link = await cells[1].query_selector("a") if len(cells) > 1 else None

            if mov_text:
                movements.append({
                    "descricao": mov_text,
                    "documento_vinculado": doc_text if doc_text else None,
                    "tem_documento": doc_link is not None,
                })
        return movements

    # Fallback: parse from page text
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
    context: BrowserContext, detail_page: Page, numero: str
) -> list[dict]:
    """Extract documents from "Documentos juntados ao processo" table.

    Flow per document (report section 5.5):
    1. Click "Visualizar documentos" → opens new tab with HTML viewer
    2. Extract idProcessoDoc and ca from URL
    3. Click "Gerar PDF" → expect_download()
    4. Upload PDF to S3
    """
    documents = []

    # Find "Visualizar documentos" links
    doc_links = await detail_page.query_selector_all(
        "a:has-text('Visualizar documentos'), "
        "a:has-text('Visualizar Documentos')"
    )

    if not doc_links:
        logger.debug("trf1_no_doc_links", extra={"numero": numero})
        return documents

    logger.info("trf1_doc_links_found", extra={"numero": numero, "count": len(doc_links)})

    for i, doc_link in enumerate(doc_links):
        try:
            doc_data = await _download_single_document(context, doc_link, numero, i)
            if doc_data:
                documents.append(doc_data)
        except Exception as e:
            logger.warning("trf1_doc_error", extra={"numero": numero, "index": i, "error": str(e)})

        await _scraper.human_delay(1.5, 3.0)

    return documents


async def _download_single_document(
    context: BrowserContext, doc_link, numero: str, index: int
) -> dict | None:
    """Open document viewer tab, download PDF, upload to S3."""

    # Get description text from the table row containing the link
    row_text = await doc_link.evaluate("""el => {
        const row = el.closest('tr');
        if (row) return row.innerText.replace(/\\s+/g, ' ').trim();
        const td = el.closest('td');
        if (td) return td.innerText.replace(/\\s+/g, ' ').trim();
        return el.parentElement?.innerText?.trim() || '';
    }""")
    # Extract meaningful part: date + document type (skip "VISUALIZAR DOCUMENTOS" link text)
    doc_description = re.sub(r"(?i)visualizar\s+documentos?", "", row_text).strip()[:200]
    if not doc_description:
        doc_description = f"documento_{index}"

    # Click "Visualizar documentos" → opens new tab
    async with context.expect_page(timeout=30_000) as doc_page_info:
        await doc_link.click()

    doc_page = await doc_page_info.value
    await doc_page.wait_for_load_state("domcontentloaded", timeout=30_000)
    await _scraper.apply_stealth(doc_page)
    await asyncio.sleep(2)

    try:
        doc_url = doc_page.url
        logger.info("trf1_doc_viewer_opened", extra={"url": doc_url, "numero": numero})

        # Extract idProcessoDoc from URL
        id_match = re.search(r"idProcessoDoc=(\d+)", doc_url)
        doc_id = id_match.group(1) if id_match else f"unknown_{index}"

        # Try to download PDF via "Gerar PDF" button
        pdf_bytes = await _download_pdf(doc_page)

        if not pdf_bytes or len(pdf_bytes) < 100:
            logger.warning("trf1_pdf_empty", extra={"doc_id": doc_id})
            return None

        # Upload to S3
        safe_numero = re.sub(r"[^\d\-.]", "", numero)
        s3_key = f"processos/{safe_numero}/documentos/{doc_id}.pdf"

        try:
            s3_url = upload_file(s3_key, pdf_bytes, "application/pdf")
            logger.info("trf1_doc_uploaded", extra={"key": s3_key, "size": len(pdf_bytes)})

            return {
                "nome": doc_description,
                "tipo": _guess_document_type(doc_description),
                "s3_url": s3_url,
                "tamanho_bytes": len(pdf_bytes),
                "id_processo_doc": doc_id,
            }
        except Exception as e:
            logger.error("trf1_s3_upload_error", extra={"key": s3_key, "error": str(e)})
            return None

    finally:
        await doc_page.close()


async def _download_pdf(doc_page: Page) -> bytes | None:
    """Download PDF from document viewer page.

    Primary: click "Gerar PDF" and capture download.
    Fallback: POST with j_id43:downloadPDF form (report section 5.6).
    """
    # Try clicking "Gerar PDF" button with expect_download
    try:
        pdf_btn = doc_page.locator("a:has-text('Gerar PDF'), button:has-text('Gerar PDF')")
        if await pdf_btn.count() > 0:
            async with doc_page.expect_download(timeout=60_000) as download_info:
                await pdf_btn.first.click()

            download = await download_info.value
            pdf_path = f"/tmp/pje_{download.suggested_filename or 'doc.pdf'}"
            await download.save_as(pdf_path)

            with open(pdf_path, "rb") as f:
                return f.read()
    except Exception as e:
        logger.debug("trf1_pdf_download_button_failed", extra={"error": str(e)})

    # Fallback: POST with JSF form parameters
    return await _download_pdf_via_post(doc_page)


async def _download_pdf_via_post(doc_page: Page) -> bytes | None:
    """Fallback: POST to same URL with j_id43:downloadPDF form data.

    Report section 3.4: j_id43 and j_id43:downloadPDF are fixed across sessions.
    javax.faces.ViewState must be read from DOM.
    """
    try:
        doc_url = doc_page.url

        # Get ViewState from DOM (changes per session)
        view_state = await doc_page.evaluate(
            "() => document.querySelector('input[name=\"javax.faces.ViewState\"]')?.value"
        )
        if not view_state:
            logger.warning("trf1_no_viewstate")
            return None

        # Get cookies for the request
        cookies = await doc_page.context.cookies()
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

        # POST via Playwright's request context (maintains session)
        response = await doc_page.context.request.post(
            doc_url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": doc_url,
            },
            data=f"{PDF_FORM_ID}={PDF_FORM_ID}&{PDF_BUTTON_ID}={PDF_BUTTON_ID}&javax.faces.ViewState={view_state}",
        )

        if response.status == 200:
            body = await response.body()
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower() or (body[:5] == b"%PDF-"):
                return body

        logger.warning("trf1_pdf_post_failed", extra={"status": response.status})
    except Exception as e:
        logger.warning("trf1_pdf_post_error", extra={"error": str(e)})

    return None


# ──────────────────────────────────────────────────────────────────
# Result List Parsing
# ──────────────────────────────────────────────────────────────────


async def _parse_results(page: Page) -> list[dict]:
    """Parse the results table from TRF1 consultation page.

    Report section 4.1: table has columns: icon | Processo | Última movimentação
    """
    processos = []

    # Wait for table rows (use attached state — rows may not be "visible")
    await page.wait_for_selector("tbody tr", state="attached", timeout=10_000)
    rows = await page.query_selector_all("tbody tr")

    for row in rows:
        try:
            cells = await row.query_selector_all("td")
            if len(cells) < 2:
                continue

            # Column 1 (index 1): Process info (class, number-subject, parties)
            proc_text = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""

            # Column 2 (index 2): Last movement
            mov_text = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""

            # Extract CNJ number
            num_match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", proc_text)
            if not num_match:
                continue

            numero = num_match.group(1)
            lines = [l.strip() for l in proc_text.split("\n") if l.strip()]

            classe = None
            assunto = None
            partes = None

            for line in lines:
                # Classe judicial: all uppercase line before the number
                if not classe and re.match(r"^[A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s]+$", line) and len(line) > 5:
                    classe = line
                    continue
                # Assunto: part after " - " in the line with the number
                if numero in line and " - " in line:
                    parts = line.split(" - ", 1)
                    if len(parts) > 1:
                        assunto = parts[1].strip()
                    continue
                # Parties: line with "X" separator
                if " X " in line or " x " in line:
                    partes = line
                    continue

            # Parse last movement and date
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
            logger.debug("trf1_parse_row_error", extra={"error": str(e)})
            continue

    # Fallback: text-based parsing
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

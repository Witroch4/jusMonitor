"""Debug script para analisar o comportamento do TRF1 scraper."""
import asyncio
import sys

sys.path.insert(0, "/app")
from app.scrapers.base import BaseScraper
from app.scrapers.trf1 import TRF1_URL, OAB_INPUT_ID, OAB_UF_SELECT_ID


async def debug():
    scraper = BaseScraper()
    async with scraper.create_session() as session:
        page = session.page
        print("Navegando para TRF1...")
        await page.goto(TRF1_URL, wait_until="domcontentloaded", timeout=90000)
        print(f"URL: {page.url}")
        print(f"Título: {await page.title()}")
        await asyncio.sleep(2)

        # Ver opções do select
        opts = await page.evaluate("""() => {
            const sel = document.getElementById('fPP:Decoration:estadoComboOAB');
            if (!sel) return ['SELECT NAO ENCONTRADO'];
            return Array.from(sel.options).slice(0, 10).map(o => o.value + ' | ' + o.text.trim());
        }""")
        print("Opções UF (primeiras 10):", opts)

        # Verificar form e inputs
        form_info = await page.evaluate("""() => {
            const form = document.getElementById('fPP');
            const oabInput = document.getElementById('fPP:Decoration:numeroOAB');
            const sel = document.getElementById('fPP:Decoration:estadoComboOAB');
            return {
                formExists: !!form,
                formAction: form ? form.action : null,
                formMethod: form ? form.method : null,
                oabInputExists: !!oabInput,
                selectExists: !!sel,
                viewState: document.querySelector('input[name="javax.faces.ViewState"]')?.value?.substring(0, 30) || null
            };
        }""")
        print("Form info:", form_info)

        # Tentar submit
        print("\nSubmitando form...")
        oab_input = page.locator(f"[id='{OAB_INPUT_ID}']")
        await oab_input.wait_for(state="visible", timeout=10000)

        await page.evaluate("""([oabNum, oabUf, oabInputId, selectId]) => {
            const form = document.getElementById('fPP');
            if (!form) { console.error('FORM NAO ENCONTRADO'); return; }
            const numInput = document.getElementById(oabInputId);
            if (numInput) numInput.value = oabNum;
            const sel = document.getElementById(selectId);
            if (sel) {
                for (const opt of sel.options) {
                    if (opt.text.trim() === oabUf || opt.value === oabUf) {
                        sel.value = opt.value;
                        break;
                    }
                }
            }
            const inp = document.createElement('input');
            inp.type = 'hidden';
            inp.name = 'fPP:pesquisar';
            inp.value = 'fPP:pesquisar';
            form.appendChild(inp);
            console.log('Submitting form, action:', form.action);
            form.submit();
        }""", ["50784", "CE", OAB_INPUT_ID, OAB_UF_SELECT_ID])

        print("Aguardando resposta...")
        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        print(f"\nURL após submit: {page.url}")
        print(f"Título após submit: {await page.title()}")

        body_text = await page.inner_text("body")
        print(f"\nPrimeiros 500 chars do body:\n{body_text[:500]}")

        # Verificar se tem resultados
        import re
        total_match = re.search(r"(\d+)\s*resultados?\s*encontrados?", body_text)
        rows = await page.query_selector_all("tbody tr")
        print(f"\nResultados match: {total_match.group(0) if total_match else 'NENHUM'}")
        print(f"Rows tbody: {len(rows)}")


asyncio.run(debug())

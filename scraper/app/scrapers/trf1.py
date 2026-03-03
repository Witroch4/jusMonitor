"""TRF1 scraper — thin wrapper over the generic PJe scraper.

Kept for backward compatibility. All logic is now in pje_generic.py.
"""

from app.scrapers.pje_generic import consultar_oab_pje


async def consultar_oab_trf1(oab_numero: str, oab_uf: str) -> dict:
    """Scrape TRF1 public consultation (backward-compatible wrapper)."""
    return await consultar_oab_pje(oab_numero, oab_uf, "trf1")

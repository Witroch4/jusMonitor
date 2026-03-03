"""JusMonitorIA Scraper — isolated web scraping microservice."""

import logging

from fastapi import FastAPI, HTTPException

from app.schemas import ConsultarOABRequest, ConsultarOABResponse
from app.scrapers.trf1 import consultar_oab_trf1


class _HealthCheckFilter(logging.Filter):
    """Suppress noisy health-check access log lines from uvicorn."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        msg = record.getMessage()
        return "GET /health" not in msg


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
# Apply filter to uvicorn access logger so /health hits don't flood the console
logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())
logger = logging.getLogger(__name__)

app = FastAPI(
    title="JusMonitorIA Scraper",
    description="Isolated web scraping service for tribunal data extraction",
    docs_url=None,
    redoc_url=None,
)

# Registry of supported tribunal scrapers
TRIBUNAL_SCRAPERS = {
    "trf1": consultar_oab_trf1,
}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "scraper"}


@app.post("/scrape/consultar-oab", response_model=ConsultarOABResponse)
async def scrape_consultar_oab(data: ConsultarOABRequest):
    """Scrape tribunal public consultation for processes by OAB number."""
    tribunal = data.tribunal.lower().strip()
    scraper_fn = TRIBUNAL_SCRAPERS.get(tribunal)

    if not scraper_fn:
        supported = ", ".join(sorted(TRIBUNAL_SCRAPERS.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Tribunal '{tribunal}' nao suportado. Disponiveis: {supported}",
        )

    logger.info("scrape_request", extra={"tribunal": tribunal, "oab": data.oab_numero})
    result = await scraper_fn(data.oab_numero, data.oab_uf)
    return result

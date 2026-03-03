"""JusMonitorIA Scraper — isolated web scraping microservice."""

import logging
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI, HTTPException

from app.schemas import (
    ConsultarOABRequest, ConsultarOABResponse,
    ListarProcessosRequest, ListarProcessosResponse,
    DetalharProcessoRequest, DetalharProcessoResponse,
    BaixarDocumentoRequest, BaixarDocumentoResponse,
    ProtocolarPeticaoRequest, ProtocolarPeticaoResponse,
)
from app.scrapers.pje_generic import (
    consultar_oab_pje,
    listar_processos_pje,
    detalhar_processo_pje,
    baixar_documento_pje,
    PJE_TRIBUNALS,
)
from app.browser_pool import browser_pool


class _HealthCheckFilter(logging.Filter):
    """Suppress noisy health-check access log lines from uvicorn."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        msg = record.getMessage()
        return "GET /health" not in msg


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())
# Peticionamento módulo em DEBUG para logs minuciosos
logging.getLogger("app.scrapers.pje_peticionamento").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Lifespan — start/stop browser pool
# ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize browser pool. Shutdown: close it."""
    logger.info("Starting browser pool...")
    await browser_pool.initialize()
    logger.info("Browser pool ready")
    yield
    logger.info("Shutting down browser pool...")
    await browser_pool.shutdown()
    logger.info("Browser pool closed")


app = FastAPI(
    title="JusMonitorIA Scraper",
    description="Isolated web scraping service for tribunal data extraction",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


def _make_pje_scraper(tribunal_code: str):
    """Create a scraper function for a PJe tribunal."""
    async def _scraper(oab_numero: str, oab_uf: str) -> dict:
        return await consultar_oab_pje(oab_numero, oab_uf, tribunal_code)
    return _scraper


# Registry of supported tribunal scrapers
# PJe tribunals — all use the same generic scraper with different URLs
TRIBUNAL_SCRAPERS = {
    code: _make_pje_scraper(code) for code in PJE_TRIBUNALS
}

# Future: EPROC tribunals (TRF2, TRF4) will be added here
# TRIBUNAL_SCRAPERS["trf2"] = consultar_oab_eproc_trf2
# TRIBUNAL_SCRAPERS["trf4"] = consultar_oab_eproc_trf4


@app.get("/health")
async def health():
    pool_status = browser_pool.health()
    return {
        "status": "ok",
        "service": "scraper",
        "tribunais": list(TRIBUNAL_SCRAPERS.keys()),
        "browser_pool": pool_status,
    }


@app.post("/scrape/consultar-oab", response_model=ConsultarOABResponse)
async def scrape_consultar_oab(data: ConsultarOABRequest):
    """DEPRECATED: Monolithic scrape. Use granular pipeline endpoints instead."""
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


# ──────────────────────────────────────────────────────────────────
# Pipeline endpoints (granular — 1 operation per call)
# ──────────────────────────────────────────────────────────────────


@app.post("/scrape/listar-processos", response_model=ListarProcessosResponse)
async def scrape_listar_processos(data: ListarProcessosRequest):
    """Phase 1: Search tribunal by OAB → return list of processes (no details)."""
    tribunal = data.tribunal.lower().strip()
    if tribunal not in PJE_TRIBUNALS:
        supported = ", ".join(sorted(PJE_TRIBUNALS.keys()))
        raise HTTPException(400, f"Tribunal '{tribunal}' não suportado. Disponíveis: {supported}")

    logger.info(f"listar_processos tribunal={tribunal} oab={data.oab_numero}/{data.oab_uf}")
    result = await listar_processos_pje(data.oab_numero, data.oab_uf, tribunal)
    return result


@app.post("/scrape/detalhar-processo", response_model=DetalharProcessoResponse)
async def scrape_detalhar_processo(data: DetalharProcessoRequest):
    """Phase 2: Open one specific process → extract parties, movements, doc links."""
    tribunal = data.tribunal.lower().strip()
    if tribunal not in PJE_TRIBUNALS:
        supported = ", ".join(sorted(PJE_TRIBUNALS.keys()))
        raise HTTPException(400, f"Tribunal '{tribunal}' não suportado. Disponíveis: {supported}")

    logger.info(f"detalhar_processo tribunal={tribunal} numero={data.numero_processo}")
    result = await detalhar_processo_pje(
        tribunal, data.numero_processo, data.oab_numero, data.oab_uf
    )
    return result


@app.post("/scrape/baixar-documento", response_model=BaixarDocumentoResponse)
async def scrape_baixar_documento(data: BaixarDocumentoRequest):
    """Phase 3: Download one document from its viewer URL → upload to S3."""
    tribunal = data.tribunal.lower().strip()
    if tribunal not in PJE_TRIBUNALS:
        supported = ", ".join(sorted(PJE_TRIBUNALS.keys()))
        raise HTTPException(400, f"Tribunal '{tribunal}' não suportado. Disponíveis: {supported}")

    logger.info(f"baixar_documento tribunal={tribunal} numero={data.numero_processo} url={data.doc_url[:80]}")
    result = await baixar_documento_pje(
        tribunal, data.numero_processo, data.doc_url,
        doc_index=data.doc_index, doc_description=data.doc_description,
    )
    return result


# ──────────────────────────────────────────────────────────────────
# Peticionamento via Playwright (RPA) — para tribunais sem MNI
# ──────────────────────────────────────────────────────────────────


@app.post("/scrape/protocolar-peticao", response_model=ProtocolarPeticaoResponse)
async def scrape_protocolar_peticao(data: ProtocolarPeticaoRequest):
    """Protocolar petição via Playwright (RPA) — usado quando MNI SOAP está bloqueado.

    Este endpoint NÃO usa o browser pool (precisa de mTLS dedicado).
    Lança browser dedicado com client_certificates do certificado A1.
    """
    from app.scrapers.pje_peticionamento import protocolar_peticao_pje

    tribunal = data.tribunal.lower().strip()
    logger.info(
        "protocolar_peticao_request tribunal=%s processo=%s tipo=%s desc=%s",
        tribunal, data.numero_processo, data.tipo_documento, data.descricao[:50],
    )

    result = await protocolar_peticao_pje(
        tribunal_code=tribunal,
        numero_processo=data.numero_processo,
        pfx_base64=data.pfx_base64,
        pfx_password=data.pfx_password,
        pdf_base64=data.pdf_base64,
        tipo_documento=data.tipo_documento,
        descricao=data.descricao,
        totp_secret=data.totp_secret,
    )

    logger.info(
        "protocolar_peticao_result tribunal=%s sucesso=%s protocolo=%s msg=%s",
        tribunal, result.sucesso, result.numero_protocolo, result.mensagem[:100],
    )

    return result.to_dict()

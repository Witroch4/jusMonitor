"""JusMonitorIA Scraper — isolated web scraping microservice."""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

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
from app.config import settings
from app.scrapers.coletar_comarcas import main_coletar, OUTPUT_JSON, ColetaComarcasResult


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

# ── Estado global do scheduler de comarcas ──────────────────────
_comarcas_scheduler_task: Optional[asyncio.Task] = None
_comarcas_is_running: bool = False  # Evita execuções concorrentes


async def _scheduler_comarcas() -> None:
    """Background task: coleta comarcas na inicialização e a cada N horas."""
    global _comarcas_is_running
    interval_h = settings.comarcas_refresh_interval_hours
    if interval_h <= 0:
        logger.info("[COMARCAS-SCHEDULER] Desabilitado (COMARCAS_REFRESH_INTERVAL_HOURS=0)")
        return

    # Aguardar o browser pool estar pronto antes do primeiro run
    await asyncio.sleep(15)

    while True:
        if not _comarcas_is_running:
            _comarcas_is_running = True
            try:
                logger.info("[COMARCAS-SCHEDULER] Iniciando coleta de comarcas...")
                result = await main_coletar(
                    pfx_path=settings.pje_pfx_path,
                    pfx_password=settings.pje_pfx_password,
                    totp_secret=settings.pje_totp_secret or None,
                    coletar_classes=True,
                )
                if result.sucesso:
                    logger.info(
                        "[COMARCAS-SCHEDULER] ✓ Coleta OK: %d jurisdições. Próxima em %d h.",
                        result.total_jurisdicoes, interval_h,
                    )
                else:
                    logger.error(
                        "[COMARCAS-SCHEDULER] Coleta falhou: %s. Retry em %d h.",
                        result.erro, interval_h,
                    )
            except Exception as e:
                logger.exception("[COMARCAS-SCHEDULER] Erro não tratado: %s", e)
            finally:
                _comarcas_is_running = False
        else:
            logger.info("[COMARCAS-SCHEDULER] Coleta em andamento, skip desta rodada.")

        # Aguardar próxima execução
        await asyncio.sleep(interval_h * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize browser pool + comarca scheduler. Shutdown: cancel tasks."""
    global _comarcas_scheduler_task

    logger.info("Starting browser pool...")
    await browser_pool.initialize()
    logger.info("Browser pool ready")

    # Iniciar scheduler de coleta de comarcas em background
    _comarcas_scheduler_task = asyncio.create_task(_scheduler_comarcas())
    logger.info(
        "[COMARCAS-SCHEDULER] Agendado — intervalo=%d h.",
        settings.comarcas_refresh_interval_hours,
    )

    yield

    logger.info("Shutting down browser pool...")
    await browser_pool.shutdown()
    logger.info("Browser pool closed")

    if _comarcas_scheduler_task and not _comarcas_scheduler_task.done():
        _comarcas_scheduler_task.cancel()
        try:
            await _comarcas_scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("[COMARCAS-SCHEDULER] Cancelado.")


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


# ──────────────────────────────────────────────────────────────────
# Comarcas / Jurisdições — coleta e consulta
# ──────────────────────────────────────────────────────────────────


class ColetarComarcasRequest(BaseModel):
    """Parâmetros opcionais para acionar a coleta de comarcas manualmente."""
    pfx_path: Optional[str] = None       # Se None, usa settings.pje_pfx_path
    pfx_password: Optional[str] = None  # Se None, usa settings.pje_pfx_password
    totp_secret: Optional[str] = None   # Se None, usa settings.pje_totp_secret
    coletar_classes: bool = True         # Se True, coleta também as Classes Judiciais


@app.post("/comarcas/coletar")
async def coletar_comarcas(
    data: ColetarComarcasRequest = ColetarComarcasRequest(),
    background_tasks: BackgroundTasks = None,
):
    """Aciona a coleta de Jurisdições (Comarcas) e Classes Judiciais do PJe TRF1.

    A coleta é feita em background (não bloqueia a resposta).
    Use GET /comarcas/trf1 para ler os dados após a coleta.
    """
    global _comarcas_is_running

    if _comarcas_is_running:
        return {
            "status": "em_andamento",
            "mensagem": "Coleta já está em andamento. Aguarde a conclusão.",
        }

    async def _run():
        global _comarcas_is_running
        _comarcas_is_running = True
        try:
            result = await main_coletar(
                pfx_path=data.pfx_path or settings.pje_pfx_path,
                pfx_password=data.pfx_password or settings.pje_pfx_password,
                totp_secret=data.totp_secret or settings.pje_totp_secret or None,
                coletar_classes=data.coletar_classes,
            )
            if result.sucesso:
                logger.info(
                    "[POST /comarcas/coletar] ✓ %d jurisdições coletadas.",
                    result.total_jurisdicoes,
                )
            else:
                logger.error("[POST /comarcas/coletar] Falhou: %s", result.erro)
        finally:
            _comarcas_is_running = False

    asyncio.create_task(_run())

    return {
        "status": "iniciado",
        "mensagem": (
            "Coleta de comarcas TRF1 iniciada em background. "
            "Use GET /comarcas/trf1 para acompanhar o resultado após conclusão."
        ),
        "pfx_path": data.pfx_path or settings.pje_pfx_path,
        "coletar_classes": data.coletar_classes,
    }


@app.get("/comarcas/trf1")
async def get_comarcas_trf1():
    """Retorna os dados de Jurisdições e Classes do TRF1 coletados em disco.

    - `colhido_em`: ISO8601 da última coleta bem-sucedida
    - `jurisdicoes`: lista de {value, text}
    - `classes_por_jurisdicao`: dict value_jurisdicao → [{value, text}]
    """
    if not OUTPUT_JSON.exists():
        return {
            "status": "sem_dados",
            "mensagem": (
                "Ainda não há dados coletados. "
                "Acione POST /comarcas/coletar para iniciar a coleta."
            ),
            "is_running": _comarcas_is_running,
        }

    import json
    data = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    data["status"] = "ok"
    data["is_running"] = _comarcas_is_running
    return data


@app.get("/comarcas/status")
async def get_comarcas_status():
    """Retorna o status atual do processo de coleta de comarcas."""
    return {
        "is_running": _comarcas_is_running,
        "scheduler_interval_hours": settings.comarcas_refresh_interval_hours,
        "json_exists": OUTPUT_JSON.exists(),
        "json_path": str(OUTPUT_JSON),
        "json_size_bytes": OUTPUT_JSON.stat().st_size if OUTPUT_JSON.exists() else 0,
    }


@app.post("/scrape/protocolar-peticao", response_model=ProtocolarPeticaoResponse)
async def scrape_protocolar_peticao(data: ProtocolarPeticaoRequest):
    """Protocolar petição via Playwright (RPA) — usado quando MNI SOAP está bloqueado.

    Este endpoint NÃO usa o browser pool (precisa de mTLS dedicado).
    Lança browser dedicado com client_certificates do certificado A1.
    """
    from app.scrapers.pje_peticionamento import protocolar_peticao_pje, tribunal_from_processo

    if data.tribunal:
        tribunal = data.tribunal.lower().strip()
    else:
        tribunal = tribunal_from_processo(data.numero_processo)
        if not tribunal:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Não foi possível inferir o tribunal do número '{data.numero_processo}'. "
                    "Forneça o campo 'tribunal' explicitamente."
                ),
            )
        logger.info(
            "protocolar_peticao_request tribunal inferido automaticamente: %s (processo=%s)",
            tribunal, data.numero_processo,
        )

    logger.info(
        "protocolar_peticao_request tribunal=%s processo=%s tipo=%s desc=%s",
        tribunal, data.numero_processo, data.tipo_documento, data.descricao[:50],
    )

    # Converter documentos_extras para lista de dicts
    docs_extras = None
    if data.documentos_extras:
        docs_extras = [d.model_dump() for d in data.documentos_extras]

    result = await protocolar_peticao_pje(
        tribunal_code=tribunal,
        numero_processo=data.numero_processo,
        pfx_base64=data.pfx_base64,
        pfx_password=data.pfx_password,
        pdf_base64=data.pdf_base64,
        tipo_documento=data.tipo_documento,
        descricao=data.descricao,
        totp_secret=data.totp_secret,
        totp_algorithm=data.totp_algorithm,
        totp_digits=data.totp_digits,
        totp_period=data.totp_period,
        tipo_peticao=data.tipo_peticao,
        dados_basicos=data.dados_basicos,
        documentos_extras=docs_extras,
    )

    logger.info(
        "protocolar_peticao_result tribunal=%s sucesso=%s protocolo=%s msg=%s",
        tribunal, result.sucesso, result.numero_protocolo, result.mensagem[:100],
    )

    return result.to_dict()

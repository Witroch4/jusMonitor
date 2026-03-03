"""Service for OAB-scraped case management.

Supports two modes:
1. Pipeline (new) — 3-phase granular scraping via Taskiq tasks
2. Legacy        — monolithic scrape via oab_finder_service (deprecated)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.oab_finder_service import consultar_oab  # legacy
from app.db.repositories.caso_oab import CasoOABRepository, OABSyncConfigRepository

logger = logging.getLogger(__name__)

# Cooldown between manual syncs (minutes)
MANUAL_SYNC_COOLDOWN_MINUTES = 5


async def _do_oab_sync(
    session: AsyncSession,
    sync_config_id: UUID,
    sync_repo: OABSyncConfigRepository,
    caso_repo: CasoOABRepository,
    oab_numero: str,
    oab_uf: str,
    user_id: Optional[UUID] = None,
) -> dict:
    """Execute the actual scraping + upsert.  Assumes status is already 'running'."""
    result = await consultar_oab(oab_numero, oab_uf)

    if not result.get("sucesso"):
        erro = result.get("mensagem", "Erro desconhecido")
        await sync_repo.update(sync_config_id, status="error", erro_mensagem=erro)
        await session.commit()
        return {
            "sucesso": False,
            "mensagem": erro,
            "total": 0,
            "novos_processos": 0,
            "novas_movimentacoes": 0,
        }

    processos = result.get("processos", [])
    novos_processos = 0
    total_novas_mov = 0

    for proc in processos:
        numero = proc.get("numero", "")
        if not numero:
            continue

        caso_existia = await caso_repo.get_by_numero(numero) is not None
        _, novas_mov = await caso_repo.upsert_from_scraper(
            numero=numero,
            processo_data=proc,
            oab_numero=oab_numero,
            oab_uf=oab_uf,
            criado_por=user_id,
        )

        if not caso_existia:
            novos_processos += 1
        total_novas_mov += novas_mov

    await sync_repo.update(
        sync_config_id,
        status="idle",
        ultimo_sync=datetime.now(timezone.utc),
        total_processos=len(processos),
        erro_mensagem=None,
    )
    await session.commit()

    logger.info("oab_sync_completed", extra={
        "oab": f"{oab_uf}{oab_numero}",
        "total": len(processos),
        "novos_processos": novos_processos,
        "novas_movimentacoes": total_novas_mov,
    })

    return {
        "sucesso": True,
        "mensagem": f"{len(processos)} processos sincronizados.",
        "total": len(processos),
        "novos_processos": novos_processos,
        "novas_movimentacoes": total_novas_mov,
    }


async def sync_oab(
    session: AsyncSession,
    tenant_id: UUID,
    oab_numero: str,
    oab_uf: str,
    user_id: Optional[UUID] = None,
) -> dict:
    """Synchronous (blocking) OAB sync — used by scheduled workers.

    Returns dict with stats: {sucesso, total, novos_processos, novas_movimentacoes, mensagem}.
    """
    caso_repo = CasoOABRepository(session, tenant_id)
    sync_repo = OABSyncConfigRepository(session, tenant_id)

    sync_config = await sync_repo.get_or_create(oab_numero, oab_uf)

    # Skip cooldown for scheduled jobs (only manual triggers enforce it)
    await sync_repo.update(sync_config.id, status="running", erro_mensagem=None)
    await session.flush()

    logger.info("oab_sync_starting", extra={
        "tenant_id": str(tenant_id), "oab": f"{oab_uf}{oab_numero}",
    })

    return await _do_oab_sync(
        session, sync_config.id, sync_repo, caso_repo, oab_numero, oab_uf, user_id
    )


async def enqueue_sync_oab(
    session: AsyncSession,
    tenant_id: UUID,
    oab_numero: str,
    oab_uf: str,
    user_id: Optional[UUID] = None,
) -> dict:
    """Enqueue OAB sync as a background task — returns immediately.

    Returns dict: {sucesso, mensagem, queued}.
    """
    sync_repo = OABSyncConfigRepository(session, tenant_id)
    sync_config = await sync_repo.get_or_create(oab_numero, oab_uf)

    # Already running — don't queue again
    if sync_config.status == "running":
        return {
            "sucesso": True,
            "mensagem": "Sincronização já está em andamento.",
            "queued": False,
            "total": sync_config.total_processos,
            "novos_processos": 0,
            "novas_movimentacoes": 0,
        }

    # Cooldown for manual triggers
    if sync_config.ultimo_sync:
        elapsed = datetime.now(timezone.utc) - sync_config.ultimo_sync
        if elapsed < timedelta(minutes=MANUAL_SYNC_COOLDOWN_MINUTES):
            remaining = MANUAL_SYNC_COOLDOWN_MINUTES - int(elapsed.total_seconds() / 60)
            return {
                "sucesso": False,
                "mensagem": f"Aguarde {remaining} minuto(s) antes de sincronizar novamente.",
                "queued": False,
                "total": sync_config.total_processos,
                "novos_processos": 0,
                "novas_movimentacoes": 0,
            }

    # Mark running and commit so the worker sees the updated state
    await sync_repo.update(sync_config.id, status="running", erro_mensagem=None)
    await session.commit()

    # Dispatch to Taskiq worker (fire-and-forget) — use the new pipeline
    from app.workers.tasks.scrape_pipeline import task_orquestrar_pipeline  # local import avoids circular
    await task_orquestrar_pipeline.kiq(
        tenant_id_str=str(tenant_id),
        sync_config_id_str=str(sync_config.id),
        oab_numero=oab_numero,
        oab_uf=oab_uf,
        user_id_str=str(user_id) if user_id else None,
    )

    logger.info("oab_sync_enqueued", extra={
        "tenant_id": str(tenant_id), "oab": f"{oab_uf}{oab_numero}",
    })

    return {
        "sucesso": True,
        "mensagem": "Sincronização iniciada em segundo plano.",
        "queued": True,
        "total": sync_config.total_processos,
        "novos_processos": 0,
        "novas_movimentacoes": 0,
    }


async def get_sync_status(
    session: AsyncSession,
    tenant_id: UUID,
    oab_numero: str,
    oab_uf: str,
) -> dict:
    """Get sync status for an OAB number."""
    sync_repo = OABSyncConfigRepository(session, tenant_id)
    config = await sync_repo.get_by_oab(oab_numero, oab_uf)

    if not config:
        return {
            "ultimo_sync": None,
            "status": "idle",
            "total_processos": 0,
            "oab_numero": oab_numero,
            "oab_uf": oab_uf,
        }

    return {
        "ultimo_sync": config.ultimo_sync,
        "status": config.status,
        "total_processos": config.total_processos,
        "oab_numero": config.oab_numero,
        "oab_uf": config.oab_uf,
        "progresso_detalhado": config.progresso_detalhado,
    }

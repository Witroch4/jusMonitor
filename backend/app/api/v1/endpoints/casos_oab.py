"""API endpoints for OAB-scraped cases."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_tenant_id, get_current_user
from app.core.services.caso_oab_service import enqueue_sync_oab, get_sync_status
from app.db.engine import get_db
from app.db.models.user import User
from app.db.repositories.caso_oab import CasoOABRepository
from app.schemas.caso_oab import (
    CasoOABCreate,
    CasoOABDetail,
    CasoOABListItem,
    CasoOABListResponse,
    SyncStatusResponse,
    SyncTriggerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/casos-oab", tags=["casos-oab"])


@router.get("", response_model=CasoOABListResponse)
async def list_casos(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CasoOABListResponse:
    """List all OAB-scraped cases for the current tenant."""
    repo = CasoOABRepository(session, tenant_id)
    items, total = await repo.list_all(skip=skip, limit=limit)
    return CasoOABListResponse(
        items=[CasoOABListItem.model_validate(p) for p in items],
        total=total,
    )


@router.get("/sync-status", response_model=SyncStatusResponse)
async def get_sync_status_endpoint(
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SyncStatusResponse:
    """Get the sync status for the current user's OAB."""
    if not current_user.oab_number or not current_user.oab_state:
        return SyncStatusResponse(
            status="no_oab",
            oab_numero=None,
            oab_uf=None,
        )

    result = await get_sync_status(
        session, tenant_id, current_user.oab_number, current_user.oab_state,
    )
    return SyncStatusResponse(**result)


@router.get("/{caso_id}", response_model=CasoOABDetail)
async def get_caso_detail(
    caso_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CasoOABDetail:
    """Get full case detail with partes, movimentacoes, and documentos."""
    repo = CasoOABRepository(session, tenant_id)
    caso = await repo.get(caso_id)
    if not caso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado")
    return CasoOABDetail.model_validate(caso)


@router.post("", response_model=CasoOABListItem, status_code=status.HTTP_201_CREATED)
async def create_caso(
    data: CasoOABCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CasoOABListItem:
    """Manually add a process by CNJ number."""
    repo = CasoOABRepository(session, tenant_id)

    numero_clean = data.numero.replace(".", "").replace("-", "").replace(" ", "")

    existing = await repo.get_by_numero(numero_clean)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Processo {data.numero} já existe nos seus casos",
        )

    oab_numero = current_user.oab_number or ""
    oab_uf = current_user.oab_state or ""

    caso = await repo.create(
        numero=numero_clean,
        oab_numero=oab_numero,
        oab_uf=oab_uf,
        tribunal="trf1",
        criado_por=current_user.id,
    )
    await session.commit()
    return CasoOABListItem.model_validate(caso)


@router.delete("/{caso_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_caso(
    caso_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a case."""
    repo = CasoOABRepository(session, tenant_id)
    deleted = await repo.delete(caso_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado")
    await session.commit()


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_sync(
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SyncTriggerResponse:
    """Trigger manual OAB sync using the current user's OAB from their profile."""
    if not current_user.oab_number or not current_user.oab_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure seu número OAB no perfil antes de sincronizar.",
        )

    result = await enqueue_sync_oab(
        session=session,
        tenant_id=tenant_id,
        oab_numero=current_user.oab_number,
        oab_uf=current_user.oab_state,
        user_id=current_user.id,
    )
    return SyncTriggerResponse(**result)


@router.post("/{caso_id}/visto", response_model=CasoOABListItem)
async def marcar_visto(
    caso_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CasoOABListItem:
    """Mark all new movements as seen."""
    repo = CasoOABRepository(session, tenant_id)
    caso = await repo.marcar_visto(caso_id)
    if not caso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso não encontrado")
    await session.commit()
    return CasoOABListItem.model_validate(caso)

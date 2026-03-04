"""API endpoints for petition management and electronic filing."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth.dependencies import get_current_tenant_id, get_current_user
from app.core.services.certificados.crypto import CertificateCryptoService
from app.core.services.peticoes.peticao_service import PeticaoService
from app.data.tipos_documento_pje import get_tipos_documento
from app.db.engine import get_db
from app.db.models.peticao import PeticaoStatus, TipoDocumento
from app.db.models.tpu import TpuDocumento
from app.db.models.user import User
from app.db.repositories.peticao import (
    PeticaoDocumentoRepository,
    PeticaoEventoRepository,
    PeticaoRepository,
)
from app.schemas.peticao import (
    ConsultarProcessoRequest,
    PeticaoCreate,
    PeticaoDocumentoResponse,
    PeticaoEventoResponse,
    PeticaoListItemResponse,
    PeticaoListResponse,
    PeticaoResponse,
    PeticaoUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/peticoes", tags=["peticoes"])

_service = PeticaoService()





def _get_crypto_service() -> CertificateCryptoService:
    return CertificateCryptoService(settings.encrypt_key)


# --- Static reference data ---


@router.get("/tipos-documento")
async def get_tipos_documento_por_tribunal(
    tribunal_id: str = Query(..., min_length=1, max_length=20),
    _tenant_id: UUID = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict:
    """Retorna os tipos de documento dispóniveis no PJe para o tribunal.

    Retorna a lista exata dos labels do select `cbTDDecoration:cbTD`
    capturada via RPA. Usar como valor no campo tipoPeticaoPje do formulário.
    """
    tipos = get_tipos_documento(tribunal_id)
    return {"tribunal_id": tribunal_id, "tipos": tipos, "total": len(tipos)}


@router.get("/tipos-documento-tpu")
async def get_tipos_documento_tpu(
    tribunal_id: str = Query(..., min_length=1, max_length=20),
    _tenant_id: UUID = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna tipos de documento da Tabela Processual Unificada (CNJ).

    Lê da tabela local `tpu_documentos` (populada e revalidada semanalmente
    pelo worker tpu_sync). Cada item: cod_item (int), nome (str), descricao (str).
    """
    result = await session.execute(
        select(TpuDocumento)
        .where(TpuDocumento.cod_item_pai.isnot(None))
        .order_by(TpuDocumento.nome)
    )
    docs = result.scalars().all()

    if not docs:
        raise HTTPException(
            status_code=503,
            detail="Tabela TPU de documentos ainda não sincronizada. Aguarde o sync automático ou acione manualmente.",
        )

    tipos = [
        {
            "cod_item": d.codigo,
            "nome": d.nome,
            "descricao": d.glossario or "",
        }
        for d in docs
    ]
    return {"tribunal_id": tribunal_id, "tipos": tipos, "total": len(tipos)}


# --- List ---


@router.get("", response_model=PeticaoListResponse)
async def list_peticoes(
    search: str | None = Query(None, max_length=200),
    status_filter: PeticaoStatus | None = Query(None, alias="status"),
    tribunal_id: str | None = Query(None, max_length=20),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PeticaoListResponse:
    """List petitions with optional filters and pagination."""
    repo = PeticaoRepository(session, tenant_id)
    items, total = await repo.list_filtered(
        search=search,
        status=status_filter,
        tribunal_id=tribunal_id,
        skip=skip,
        limit=limit,
    )

    list_items = []
    for pet in items:
        item = PeticaoListItemResponse.model_validate(pet)
        item.quantidade_documentos = len(pet.documentos) if pet.documentos else 0
        list_items.append(item)

    return PeticaoListResponse(items=list_items, total=total)


# --- Create ---


@router.post("", response_model=PeticaoResponse, status_code=status.HTTP_201_CREATED)
async def create_peticao(
    data: PeticaoCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PeticaoResponse:
    """Create a new petition in rascunho status."""
    pet = await _service.create(session, tenant_id, current_user.id, data)
    await session.commit()

    # Re-fetch to load relationships
    repo = PeticaoRepository(session, tenant_id)
    pet = await repo.get(pet.id)

    logger.info(
        "Petition created",
        extra={"peticao_id": str(pet.id), "tenant_id": str(tenant_id)},
    )
    return PeticaoResponse.model_validate(pet)


# --- Detail ---


@router.get("/{peticao_id}", response_model=PeticaoResponse)
async def get_peticao(
    peticao_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PeticaoResponse:
    """Get petition detail with documents and events."""
    repo = PeticaoRepository(session, tenant_id)
    pet = await repo.get(peticao_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petição não encontrada",
        )
    return PeticaoResponse.model_validate(pet)


# --- Update ---


@router.patch("/{peticao_id}", response_model=PeticaoResponse)
async def update_peticao(
    peticao_id: UUID,
    data: PeticaoUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PeticaoResponse:
    """Update petition metadata. Only allowed when status is rascunho."""
    repo = PeticaoRepository(session, tenant_id)
    pet = await repo.get(peticao_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petição não encontrada",
        )
    if pet.status == PeticaoStatus.REJEITADA:
        # Auto-transition REJEITADA → RASCUNHO when editing
        await _service.transition_status(
            session, tenant_id, peticao_id,
            PeticaoStatus.RASCUNHO,
            "Petição reaberta para correção e reenvio",
        )
    elif pet.status != PeticaoStatus.RASCUNHO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas petições em rascunho podem ser editadas",
        )

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return PeticaoResponse.model_validate(pet)

    # Serialize dados_basicos Pydantic model to JSON dict for JSONB column
    if "dados_basicos" in update_data and update_data["dados_basicos"] is not None:
        update_data["dados_basicos_json"] = update_data.pop("dados_basicos")
        if hasattr(update_data["dados_basicos_json"], "model_dump"):
            update_data["dados_basicos_json"] = update_data["dados_basicos_json"].model_dump(mode="json")
    elif "dados_basicos" in update_data:
        update_data.pop("dados_basicos")

    updated = await repo.update(peticao_id, **update_data)
    await session.commit()

    # Re-fetch to load relationships
    pet = await repo.get(peticao_id)
    return PeticaoResponse.model_validate(pet)


# --- Delete ---


@router.delete("/{peticao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_peticao(
    peticao_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a petition. Only allowed when status is rascunho."""
    repo = PeticaoRepository(session, tenant_id)
    pet = await repo.get(peticao_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petição não encontrada",
        )
    if pet.status != PeticaoStatus.RASCUNHO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas petições em rascunho podem ser deletadas",
        )

    await repo.delete(peticao_id)
    await session.commit()

    logger.info(
        "Petition deleted",
        extra={"peticao_id": str(peticao_id), "tenant_id": str(tenant_id)},
    )


# --- Documents ---


@router.post(
    "/{peticao_id}/documentos",
    response_model=PeticaoDocumentoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_documento(
    peticao_id: UUID,
    arquivo: UploadFile = File(..., description="Arquivo PDF"),
    tipo_documento: TipoDocumento = Form(...),
    ordem: int = Form(1, ge=1),
    sigiloso: bool = Form(False),
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PeticaoDocumentoResponse:
    """Upload a PDF document to a petition."""
    # Verify petition exists and is editable
    repo = PeticaoRepository(session, tenant_id)
    pet = await repo.get(peticao_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petição não encontrada",
        )
    if pet.status != PeticaoStatus.RASCUNHO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documentos só podem ser adicionados em petições com status rascunho",
        )

    # Validate file
    if arquivo.filename and not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos PDF são aceitos",
        )

    pdf_bytes = await arquivo.read()
    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio",
        )

    max_size = settings.mni_max_file_size_mb * 1024 * 1024
    if len(pdf_bytes) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede limite de {settings.mni_max_file_size_mb}MB",
        )

    crypto = _get_crypto_service()
    try:
        doc = await _service.add_documento(
            session, tenant_id, peticao_id,
            pdf_bytes=pdf_bytes,
            nome_original=arquivo.filename or "documento.pdf",
            tipo_documento=tipo_documento,
            ordem=ordem,
            crypto=crypto,
            sigiloso=sigiloso,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await session.commit()

    logger.info(
        "Document uploaded",
        extra={
            "peticao_id": str(peticao_id),
            "doc_id": str(doc.id),
            "size_bytes": len(pdf_bytes),
        },
    )
    return PeticaoDocumentoResponse.model_validate(doc)


@router.delete(
    "/{peticao_id}/documentos/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_documento(
    peticao_id: UUID,
    doc_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a document from a petition."""
    # Verify petition
    pet_repo = PeticaoRepository(session, tenant_id)
    pet = await pet_repo.get(peticao_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petição não encontrada",
        )
    if pet.status != PeticaoStatus.RASCUNHO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documentos só podem ser removidos de petições em rascunho",
        )

    # Verify document belongs to petition
    doc_repo = PeticaoDocumentoRepository(session, tenant_id)
    doc = await doc_repo.get(doc_id)
    if doc is None or doc.peticao_id != peticao_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado",
        )

    await doc_repo.delete(doc_id)
    await session.commit()


# --- Events ---


@router.get("/{peticao_id}/eventos", response_model=list[PeticaoEventoResponse])
async def list_eventos(
    peticao_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[PeticaoEventoResponse]:
    """List petition status events (timeline)."""
    # Verify petition exists
    pet_repo = PeticaoRepository(session, tenant_id)
    pet = await pet_repo.get(peticao_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petição não encontrada",
        )

    evento_repo = PeticaoEventoRepository(session, tenant_id)
    eventos = await evento_repo.list_by_peticao(peticao_id)
    return [PeticaoEventoResponse.model_validate(e) for e in eventos]


# --- Consultar Processo (MNI read-only) ---


@router.post("/consultar-processo")
async def consultar_processo(
    data: ConsultarProcessoRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Consult a process via MNI 2.2.2 consultarProcesso.

    This is a READ-ONLY operation — no petition is filed, no data is modified.
    Returns process header, parties (polos), movements, and judging body.
    Requires a valid A1 certificate with mTLS.
    """
    import asyncio

    from app.api.v1.endpoints.tribunais import get_tribunal_config
    from app.core.services.peticoes.mni_client import MniSoapClient
    from app.db.repositories.certificado_digital import CertificadoDigitalRepository

    # Load certificate
    cert_repo = CertificadoDigitalRepository(session, tenant_id)
    cert = await cert_repo.get(data.certificado_id)
    if cert is None or cert.revogado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado não encontrado ou revogado",
        )

    # Resolve tribunal WSDL
    tribunal = get_tribunal_config(data.tribunal_id)
    if tribunal is None or not tribunal.get("wsdlEndpoint"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tribunal '{data.tribunal_id}' sem endpoint WSDL configurado",
        )

    crypto = _get_crypto_service()
    mni = MniSoapClient(crypto)

    cpf = cert.titular_cpf_cnpj.replace(".", "").replace("-", "").replace("/", "")

    result = await asyncio.to_thread(
        mni.consultar_processo,
        wsdl_url=tribunal["wsdlEndpoint"],
        pfx_encrypted=cert.pfx_encrypted,
        pfx_password_encrypted=cert.pfx_password_encrypted,
        numero_processo=data.numero_processo,
        id_consultante=cpf,
    )

    logger.info(
        "consultarProcesso called",
        extra={
            "processo": data.numero_processo,
            "tribunal": data.tribunal_id,
            "sucesso": result.get("sucesso"),
        },
    )

    return result


# --- Filing (Phase 2C) ---


@router.post("/{peticao_id}/protocolar", status_code=status.HTTP_202_ACCEPTED)
async def protocolar_peticao(
    peticao_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Initiate MNI electronic filing pipeline.

    Validates the petition is ready, transitions to VALIDANDO,
    and enqueues the filing worker task.
    """
    # Validate readiness
    errors = await _service.validate_for_filing(session, tenant_id, peticao_id)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Petição não está pronta para protocolar", "errors": errors},
        )

    # Transition rascunho → validando
    try:
        await _service.transition_status(
            session, tenant_id, peticao_id,
            PeticaoStatus.VALIDANDO,
            "Iniciando validação para protocolo",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await session.commit()

    # Enqueue filing worker
    try:
        from app.workers.tasks.peticao_protocolar import protocolar_peticao_task
        await protocolar_peticao_task.kiq(
            peticao_id=str(peticao_id),
            tenant_id=str(tenant_id),
        )
    except Exception as e:
        logger.error(
            "Failed to enqueue filing task",
            extra={"peticao_id": str(peticao_id), "error": str(e)},
        )
        # Revert status
        await _service.transition_status(
            session, tenant_id, peticao_id,
            PeticaoStatus.RASCUNHO,
            "Falha ao enfileirar tarefa de protocolo",
            detalhes=str(e),
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao iniciar protocolo. Tente novamente.",
        )

    return {"message": "Protocolo iniciado", "peticaoId": str(peticao_id)}


# --- Validation ---


@router.post("/{peticao_id}/analise-ia", status_code=status.HTTP_202_ACCEPTED)
async def analise_ia(
    peticao_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Request AI analysis of petition documents. Stores result in analise_ia JSONB field."""
    repo = PeticaoRepository(session, tenant_id)
    pet = await repo.get(peticao_id)
    if pet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petição não encontrada",
        )

    # TODO: Integrate with LangGraph AI agent for real analysis
    # For now, store a placeholder analysis
    analise = {
        "status": "pendente",
        "mensagem": "Análise IA será implementada na próxima fase",
    }
    await repo.update(peticao_id, analise_ia=analise)
    await session.commit()

    return {"message": "Análise solicitada", "peticaoId": str(peticao_id)}


@router.get("/{peticao_id}/validar")
async def validar_peticao(
    peticao_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Check if petition is ready for filing. Returns validation errors."""
    errors = await _service.validate_for_filing(session, tenant_id, peticao_id)
    return {
        "pronta": len(errors) == 0,
        "errors": errors,
    }

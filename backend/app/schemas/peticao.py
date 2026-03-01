"""Pydantic schemas for Petition API.

All response schemas use alias_generator=to_camel for frontend compatibility
with TypeScript types in frontend/types/peticoes.ts.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.alias_generators import to_camel

from app.db.models.peticao import (
    DocumentoStatus,
    PeticaoStatus,
    TipoDocumento,
    TipoPeticao,
)


# --- Request schemas ---


class PeticaoCreate(BaseModel):
    """POST /peticoes request body."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    processo_numero: str = Field(..., min_length=1, max_length=50)
    tribunal_id: str = Field(..., min_length=1, max_length=20)
    tipo_peticao: TipoPeticao
    assunto: str = Field(..., min_length=1, max_length=500)
    descricao: Optional[str] = None
    certificado_id: Optional[UUID] = None


class PeticaoUpdate(BaseModel):
    """PATCH /peticoes/{id} request body. Only allowed on status=rascunho."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    assunto: Optional[str] = Field(None, max_length=500)
    descricao: Optional[str] = None
    certificado_id: Optional[UUID] = None
    tribunal_id: Optional[str] = Field(None, max_length=20)
    processo_numero: Optional[str] = Field(None, max_length=50)
    tipo_peticao: Optional[TipoPeticao] = None


# --- Response schemas ---


class PeticaoDocumentoResponse(BaseModel):
    """Response for a single petition document."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: UUID
    nome_original: str
    tamanho_bytes: int
    tipo_documento: TipoDocumento
    ordem: int
    uploaded_at: datetime = Field(validation_alias="created_at")
    status: DocumentoStatus
    erro_validacao: Optional[str] = None


class PeticaoEventoResponse(BaseModel):
    """Response for a petition status event."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: UUID
    peticao_id: UUID
    status: PeticaoStatus
    descricao: str
    detalhes: Optional[str] = None
    criado_em: datetime = Field(validation_alias="created_at")


class PeticaoResponse(BaseModel):
    """Full petition response matching TypeScript Peticao interface."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: UUID
    tenant_id: UUID
    numero_protocolo: Optional[str] = None
    processo_numero: str
    tribunal_id: str
    tipo_peticao: TipoPeticao
    assunto: str
    descricao: Optional[str] = None
    status: PeticaoStatus
    documentos: list[PeticaoDocumentoResponse] = []
    certificado_id: Optional[UUID] = None
    analise_ia: Optional[dict] = None
    protocolado_em: Optional[datetime] = None
    protocolo_recibo: Optional[str] = None
    motivo_rejeicao: Optional[str] = None
    criado_por: Optional[UUID] = None
    criado_em: datetime = Field(validation_alias="created_at")
    atualizado_em: datetime = Field(validation_alias="updated_at")


class PeticaoListItemResponse(BaseModel):
    """Lightweight list item matching TypeScript PeticaoListItem."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    id: UUID
    numero_protocolo: Optional[str] = None
    processo_numero: str
    tribunal_id: str
    tipo_peticao: TipoPeticao
    assunto: str
    status: PeticaoStatus
    protocolado_em: Optional[datetime] = None
    criado_em: datetime = Field(validation_alias="created_at")

    # Computed from selectin-loaded documentos relationship
    quantidade_documentos: int = 0


class PeticaoListResponse(BaseModel):
    """Paginated petition list response."""

    items: list[PeticaoListItemResponse]
    total: int

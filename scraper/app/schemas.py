"""Request/response schemas for the scraper service."""

from pydantic import BaseModel, Field


class ConsultarOABRequest(BaseModel):
    oab_numero: str = Field(..., min_length=1, max_length=20)
    oab_uf: str = Field(..., min_length=2, max_length=2)
    tribunal: str = Field(default="trf1")


class DocumentoAnexo(BaseModel):
    nome: str
    tipo: str | None = None
    s3_url: str
    tamanho_bytes: int | None = None


class ProcessoResumo(BaseModel):
    numero: str
    classe: str | None = None
    assunto: str | None = None
    partes: str | None = None
    ultima_movimentacao: str | None = None
    data_ultima_movimentacao: str | None = None
    partes_detalhadas: list[dict] | None = None
    movimentacoes: list[dict] | None = None
    documentos: list[DocumentoAnexo] = []


class ConsultarOABResponse(BaseModel):
    sucesso: bool
    mensagem: str = ""
    processos: list[ProcessoResumo] = []
    total: int = 0

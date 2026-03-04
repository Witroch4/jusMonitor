"""Request/response schemas for the scraper service."""

from pydantic import BaseModel, Field


# ── Legacy endpoint (deprecated, kept for backward compat) ──

class ConsultarOABRequest(BaseModel):
    oab_numero: str = Field(..., min_length=1, max_length=20)
    oab_uf: str = Field(..., min_length=2, max_length=2)
    tribunal: str = Field(default="trf1")


class DocumentoAnexo(BaseModel):
    nome: str
    tipo: str | None = None
    s3_url: str
    tamanho_bytes: int | None = None
    id_processo_doc: str | None = None


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


# ── Phase 1: Listing (search tribunal → get process list) ──

class ListarProcessosRequest(BaseModel):
    """Request to search a tribunal by OAB and return the list of processes."""
    oab_numero: str = Field(..., min_length=1, max_length=20)
    oab_uf: str = Field(..., min_length=2, max_length=2)
    tribunal: str = Field(..., min_length=2, max_length=20)


class ProcessoBasico(BaseModel):
    """Basic process info from the search results (no details/docs)."""
    numero: str
    classe: str | None = None
    assunto: str | None = None
    partes: str | None = None
    ultima_movimentacao: str | None = None
    data_ultima_movimentacao: str | None = None


class ListarProcessosResponse(BaseModel):
    sucesso: bool
    mensagem: str = ""
    processos: list[ProcessoBasico] = []
    total: int = 0
    tribunal: str = ""


# ── Phase 2: Detail (open one process → extract parties + movements) ──

class DetalharProcessoRequest(BaseModel):
    """Request to extract details for a single process."""
    tribunal: str = Field(..., min_length=2, max_length=20)
    numero_processo: str = Field(..., min_length=20, max_length=30)
    oab_numero: str = Field(..., min_length=1, max_length=20)
    oab_uf: str = Field(..., min_length=2, max_length=2)


class DocLink(BaseModel):
    """A document link found in the process detail page."""
    index: int
    description: str = ""
    url: str = ""
    id_processo_doc: str | None = None


class DetalharProcessoResponse(BaseModel):
    sucesso: bool
    mensagem: str = ""
    numero: str = ""
    partes_detalhadas: list[dict] = []
    movimentacoes: list[dict] = []
    doc_links: list[DocLink] = []


# ── Phase 3: Document (download one doc → S3) ──

class BaixarDocumentoRequest(BaseModel):
    """Request to download a single document and upload to S3."""
    tribunal: str = Field(..., min_length=2, max_length=20)
    numero_processo: str = Field(..., min_length=20, max_length=30)
    doc_url: str = Field(..., description="URL of the document viewer page")
    doc_index: int = Field(0, description="Index of the document in the list")
    doc_description: str = Field("", description="Description/name of the document")


class BaixarDocumentoResponse(BaseModel):
    sucesso: bool
    mensagem: str = ""
    numero: str = ""
    doc_id: str | None = None
    s3_url: str | None = None
    tamanho_bytes: int | None = None
    nome: str = ""
    tipo: str = ""


# ── Peticionamento via Playwright (RPA) ──

class ProtocolarPeticaoRequest(BaseModel):
    """Request para protocolar petição via Playwright (RPA)."""
    tribunal: str | None = Field(default=None, min_length=2, max_length=20, description="Código do tribunal (ex: trf1). Se omitido, será inferido automaticamente do número CNJ do processo.")
    numero_processo: str = Field(..., description="Número formatado do processo")
    pfx_base64: str = Field(..., description="Certificado A1 (PFX) em base64")
    pfx_password: str = Field(..., description="Senha do certificado PFX")
    pdf_base64: str = Field(..., description="PDF da petição em base64")
    tipo_documento: str = Field(default="Petição", description="Tipo do documento no PJe")
    descricao: str = Field(default="", description="Descrição do documento")
    totp_secret: str | None = Field(default=None, description="Segredo TOTP base32 para 2FA do SSO PJe")
    totp_algorithm: str | None = Field(default=None, description="Algoritmo TOTP (SHA1, SHA256, SHA512)")
    totp_digits: int | None = Field(default=None, description="Número de dígitos TOTP (6 ou 8)")
    totp_period: int | None = Field(default=None, description="Período TOTP em segundos (30 ou 60)")


class ProtocolarPeticaoResponse(BaseModel):
    """Response do peticionamento via Playwright."""
    sucesso: bool
    mensagem: str = ""
    numero_protocolo: str | None = None
    screenshots: list[str] = []

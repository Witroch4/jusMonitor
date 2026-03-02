"""Petition business logic and state machine."""

import hashlib
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.certificados.crypto import CertificateCryptoService
from app.db.models.peticao import (
    DocumentoStatus,
    Peticao,
    PeticaoDocumento,
    PeticaoStatus,
    TipoDocumento,
    TipoPeticao,
)
from app.db.repositories.peticao import (
    PeticaoDocumentoRepository,
    PeticaoEventoRepository,
    PeticaoRepository,
)
from app.schemas.peticao import PeticaoCreate

logger = logging.getLogger(__name__)


# Valid status transitions (directed acyclic graph with rejeitada→rascunho loop)
TRANSITIONS: dict[PeticaoStatus, set[PeticaoStatus]] = {
    PeticaoStatus.RASCUNHO: {PeticaoStatus.VALIDANDO},
    PeticaoStatus.VALIDANDO: {PeticaoStatus.ASSINANDO, PeticaoStatus.RASCUNHO},
    PeticaoStatus.ASSINANDO: {PeticaoStatus.PROTOCOLANDO, PeticaoStatus.VALIDANDO},
    PeticaoStatus.PROTOCOLANDO: {PeticaoStatus.PROTOCOLADA, PeticaoStatus.REJEITADA},
    PeticaoStatus.PROTOCOLADA: {PeticaoStatus.ACEITA, PeticaoStatus.REJEITADA},
    PeticaoStatus.ACEITA: set(),
    PeticaoStatus.REJEITADA: {PeticaoStatus.RASCUNHO},
}


class PeticaoService:
    """Petition business logic with status state machine."""

    async def create(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        criado_por: UUID,
        data: PeticaoCreate,
    ) -> Peticao:
        """Create a new petition in rascunho status with initial event."""
        # For petição inicial, use 20 zeros as per MNI 2.2.2
        processo_numero = data.processo_numero
        if data.tipo_peticao == TipoPeticao.PETICAO_INICIAL and not processo_numero:
            processo_numero = "00000000000000000000"

        # Serialize dados_basicos to JSON if provided
        dados_basicos_json = None
        if data.dados_basicos:
            dados_basicos_json = data.dados_basicos.model_dump(mode="json")

        repo = PeticaoRepository(session, tenant_id)
        pet = await repo.create(
            processo_numero=processo_numero,
            tribunal_id=data.tribunal_id,
            tipo_peticao=data.tipo_peticao,
            assunto=data.assunto,
            descricao=data.descricao,
            certificado_id=data.certificado_id,
            criado_por=criado_por,
            status=PeticaoStatus.RASCUNHO,
            dados_basicos_json=dados_basicos_json,
        )
        await self._record_evento(
            session, tenant_id, pet.id,
            PeticaoStatus.RASCUNHO, "Petição criada como rascunho",
        )
        return pet

    async def add_documento(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        peticao_id: UUID,
        pdf_bytes: bytes,
        nome_original: str,
        tipo_documento: TipoDocumento,
        ordem: int,
        crypto: CertificateCryptoService,
        sigiloso: bool = False,
    ) -> PeticaoDocumento:
        """Validate PDF, compute hash, encrypt, and store document."""
        # Validate PDF header
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("Arquivo não é um PDF válido")

        # Compute SHA-256 hash
        hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        # Encrypt with Fernet
        encrypted = crypto.encrypt(pdf_bytes)

        doc_repo = PeticaoDocumentoRepository(session, tenant_id)
        doc = await doc_repo.create(
            peticao_id=peticao_id,
            nome_original=nome_original,
            tamanho_bytes=len(pdf_bytes),
            tipo_documento=tipo_documento,
            ordem=ordem,
            conteudo_encrypted=encrypted,
            hash_sha256=hash_sha256,
            status=DocumentoStatus.UPLOADED,
            sigiloso=sigiloso,
        )
        return doc

    async def transition_status(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        peticao_id: UUID,
        new_status: PeticaoStatus,
        descricao: str,
        detalhes: str | None = None,
    ) -> Peticao:
        """Transition petition status with validation and event recording."""
        repo = PeticaoRepository(session, tenant_id)
        pet = await repo.get(peticao_id)

        if pet is None:
            raise ValueError("Petição não encontrada")

        valid_targets = TRANSITIONS.get(pet.status, set())
        if new_status not in valid_targets:
            raise ValueError(
                f"Transição inválida: {pet.status.value} → {new_status.value}. "
                f"Transições permitidas: {[s.value for s in valid_targets]}"
            )

        updated = await repo.update(peticao_id, status=new_status)
        await self._record_evento(
            session, tenant_id, peticao_id,
            new_status, descricao, detalhes,
        )
        return updated

    async def validate_for_filing(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        peticao_id: UUID,
    ) -> list[str]:
        """Return list of validation errors. Empty list = ready to file."""
        errors = []

        pet_repo = PeticaoRepository(session, tenant_id)
        pet = await pet_repo.get(peticao_id)
        if pet is None:
            return ["Petição não encontrada"]

        if pet.status != PeticaoStatus.RASCUNHO:
            errors.append(f"Petição deve estar em rascunho, está em: {pet.status.value}")

        # Check documents
        doc_repo = PeticaoDocumentoRepository(session, tenant_id)
        docs = await doc_repo.list_by_peticao(peticao_id)
        if not docs:
            errors.append("Nenhum documento anexado")

        has_principal = any(
            d.tipo_documento == TipoDocumento.PETICAO_PRINCIPAL for d in docs
        )
        if not has_principal:
            errors.append("Faltando documento do tipo 'Petição Principal'")

        # Check certificate
        if pet.certificado_id is None:
            errors.append("Nenhum certificado digital selecionado")
        else:
            from app.db.repositories.certificado_digital import CertificadoDigitalRepository
            from datetime import datetime, timezone

            cert_repo = CertificadoDigitalRepository(session, tenant_id)
            cert = await cert_repo.get(pet.certificado_id)
            if cert is None or cert.revogado:
                errors.append("Certificado não encontrado ou revogado")
            elif cert.valido_ate < datetime.now(timezone.utc):
                errors.append("Certificado expirado")

        return errors

    async def _record_evento(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        peticao_id: UUID,
        status: PeticaoStatus,
        descricao: str,
        detalhes: str | None = None,
    ) -> None:
        """Record a status change event in the petition timeline."""
        evento_repo = PeticaoEventoRepository(session, tenant_id)
        await evento_repo.create(
            peticao_id=peticao_id,
            status=status,
            descricao=descricao,
            detalhes=detalhes,
        )

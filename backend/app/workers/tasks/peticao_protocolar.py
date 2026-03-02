"""Taskiq worker for MNI 2.2.2 electronic petition filing pipeline.

Pipeline:
  1. Load petition + documents + certificate
  2. Validate each PDF
  3. Sign each PDF with A1 certificate (pyhanko PKCS#7)
  4. Call entregarManifestacaoProcessual via zeep + mTLS
  5. Update status (protocolada or rejeitada)
  6. Record timeline events
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.config import settings
from app.core.services.certificados.crypto import CertificateCryptoService
from app.core.services.peticoes.mni_client import MniSoapClient
from app.core.services.peticoes.pdf_signer import PdfSignerService
from app.core.services.peticoes.pdf_validator import PdfValidatorService
from app.core.services.peticoes.peticao_service import PeticaoService
from app.db.engine import AsyncSessionLocal
from app.db.models.peticao import PeticaoStatus
from app.db.repositories.certificado_digital import CertificadoDigitalRepository
from app.db.repositories.peticao import PeticaoDocumentoRepository, PeticaoRepository
from app.workers.broker import broker
from app.workers.tasks.base import with_retry, with_timeout

logger = logging.getLogger(__name__)


@broker.task
@with_retry(max_retries=2, initial_delay=30.0, backoff_factor=2.0, max_delay=120.0)
@with_timeout(300.0)
async def protocolar_peticao_task(peticao_id: str, tenant_id: str) -> dict:
    """Full MNI filing pipeline."""
    pet_uuid = UUID(peticao_id)
    tenant_uuid = UUID(tenant_id)

    crypto = CertificateCryptoService(settings.encrypt_key)
    validator = PdfValidatorService(settings.mni_max_file_size_mb)
    signer = PdfSignerService()
    service = PeticaoService()

    async with AsyncSessionLocal() as session:
        # --- Load petition ---
        pet_repo = PeticaoRepository(session, tenant_uuid)
        pet = await pet_repo.get(pet_uuid)
        if pet is None:
            logger.error("Petition not found: %s", peticao_id)
            return {"erro": "Petição não encontrada"}

        if pet.status not in (PeticaoStatus.VALIDANDO, PeticaoStatus.ASSINANDO, PeticaoStatus.PROTOCOLANDO):
            logger.warning("Unexpected petition status: %s", pet.status)
            return {"erro": f"Status inesperado: {pet.status.value}"}

        # --- Load certificate ---
        if pet.certificado_id is None:
            await _reject(service, session, tenant_uuid, pet_uuid, "Nenhum certificado selecionado")
            return {"erro": "Certificado não selecionado"}

        cert_repo = CertificadoDigitalRepository(session, tenant_uuid)
        cert = await cert_repo.get(pet.certificado_id)
        if cert is None or cert.revogado:
            await _reject(service, session, tenant_uuid, pet_uuid, "Certificado não encontrado ou revogado")
            return {"erro": "Certificado inválido"}

        # Check expiry
        if cert.valido_ate < datetime.now(timezone.utc):
            await _reject(service, session, tenant_uuid, pet_uuid, "Certificado expirado")
            return {"erro": "Certificado expirado"}

        # --- Load documents ---
        doc_repo = PeticaoDocumentoRepository(session, tenant_uuid)
        docs = await doc_repo.list_by_peticao(pet_uuid)
        if not docs:
            await _reject(service, session, tenant_uuid, pet_uuid, "Nenhum documento para protocolar")
            return {"erro": "Sem documentos"}

        # --- Transition to ASSINANDO ---
        try:
            await service.transition_status(
                session, tenant_uuid, pet_uuid,
                PeticaoStatus.ASSINANDO,
                "Validando e assinando documentos",
            )
            await session.commit()
        except ValueError:
            pass  # Already in a valid state

        # --- Validate + Sign each document ---
        documentos_para_mni = []
        for doc in docs:
            # Decrypt
            pdf_bytes = crypto.decrypt(doc.conteudo_encrypted)

            # Validate
            result = validator.validate(pdf_bytes, doc.nome_original)
            if not result.valid:
                await _reject(
                    service, session, tenant_uuid, pet_uuid,
                    f"Documento inválido: {doc.nome_original}",
                    detalhes=result.error,
                )
                return {"erro": result.error}

            # Sign with A1 certificate (run in thread — pyhanko internals conflict with async loop)
            try:
                signed_bytes = await asyncio.to_thread(
                    signer.sign_in_memory,
                    pdf_bytes, cert.pfx_encrypted, cert.pfx_password_encrypted, crypto,
                )
            except Exception as e:
                await _reject(
                    service, session, tenant_uuid, pet_uuid,
                    f"Falha ao assinar {doc.nome_original}",
                    detalhes=str(e),
                )
                return {"erro": f"Erro de assinatura: {e}"}

            documentos_para_mni.append({
                "conteudo": signed_bytes,
                "nome": doc.nome_original,
                "tipo_documento": doc.tipo_documento.value,
            })

        # --- Transition to PROTOCOLANDO ---
        try:
            await service.transition_status(
                session, tenant_uuid, pet_uuid,
                PeticaoStatus.PROTOCOLANDO,
                "Enviando ao tribunal via MNI/SOAP",
            )
            await session.commit()
        except ValueError:
            pass

        # --- Get tribunal config ---
        from app.api.v1.endpoints.tribunais import get_tribunal_config
        tribunal = get_tribunal_config(pet.tribunal_id)
        if tribunal is None or not tribunal.get("suportaMNI"):
            await _reject(
                service, session, tenant_uuid, pet_uuid,
                f"Tribunal {pet.tribunal_id} não suporta MNI",
            )
            return {"erro": "Tribunal sem suporte MNI"}

        wsdl_url = tribunal.get("wsdlEndpoint")
        if not wsdl_url:
            await _reject(
                service, session, tenant_uuid, pet_uuid,
                f"Tribunal {pet.tribunal_id} sem endpoint WSDL configurado",
            )
            return {"erro": "Sem WSDL endpoint"}

        # --- Call MNI SOAP (sync zeep — run in thread) ---
        mni = MniSoapClient(crypto)
        filing_result = await asyncio.to_thread(
            mni.entregar_manifestacao_processual,
            wsdl_url=wsdl_url,
            pfx_encrypted=cert.pfx_encrypted,
            pfx_password_encrypted=cert.pfx_password_encrypted,
            id_manifestante=cert.titular_cpf_cnpj.replace(".", "").replace("-", "").replace("/", ""),
            numero_processo=pet.processo_numero,
            documentos=documentos_para_mni,
            dados_basicos_json=pet.dados_basicos_json,
        )

        # --- Handle result ---
        if filing_result.sucesso:
            await pet_repo.update(
                pet_uuid,
                status=PeticaoStatus.PROTOCOLADA,
                numero_protocolo=filing_result.numero_protocolo,
                protocolado_em=datetime.now(timezone.utc),
                protocolo_recibo=filing_result.recibo_base64,
            )
            await service._record_evento(
                session, tenant_uuid, pet_uuid,
                PeticaoStatus.PROTOCOLADA,
                f"Protocolo {filing_result.numero_protocolo} recebido pelo tribunal",
                detalhes=filing_result.mensagem,
            )
            await session.commit()

            # --- Auto-create monitored process ---
            try:
                from app.db.repositories.processo_monitorado import ProcessoMonitoradoRepository
                pm_repo = ProcessoMonitoradoRepository(session, tenant_uuid)
                numero_clean = pet.processo_numero.replace(".", "").replace("-", "").replace(" ", "")
                existing = await pm_repo.get_by_numero(numero_clean)
                if not existing:
                    await pm_repo.create(
                        numero=numero_clean,
                        apelido=pet.assunto,
                        criado_por=pet.criado_por,
                        peticao_id=pet_uuid,
                    )
                    await session.commit()
                    logger.info("Auto-created monitored process for %s", numero_clean)
            except Exception as e:
                logger.warning("Failed to auto-create monitored process: %s", e)

            logger.info(
                "Petition filed successfully",
                extra={
                    "peticao_id": peticao_id,
                    "protocolo": filing_result.numero_protocolo,
                    "tribunal": pet.tribunal_id,
                },
            )
            return {
                "sucesso": True,
                "protocolo": filing_result.numero_protocolo,
                "mensagem": filing_result.mensagem,
            }
        else:
            await _reject(
                service, session, tenant_uuid, pet_uuid,
                "Tribunal rejeitou a petição",
                detalhes=filing_result.mensagem,
            )
            return {"sucesso": False, "erro": filing_result.mensagem}


async def _reject(
    service: PeticaoService,
    session,
    tenant_id: UUID,
    peticao_id: UUID,
    descricao: str,
    detalhes: str | None = None,
) -> None:
    """Helper to transition petition to REJEITADA status."""
    try:
        pet_repo = PeticaoRepository(session, tenant_id)
        pet = await pet_repo.get(peticao_id)
        if pet and pet.status != PeticaoStatus.REJEITADA:
            await pet_repo.update(peticao_id, status=PeticaoStatus.REJEITADA, motivo_rejeicao=descricao)
            await service._record_evento(
                session, tenant_id, peticao_id,
                PeticaoStatus.REJEITADA, descricao, detalhes,
            )
        await session.commit()
    except Exception as e:
        logger.error("Failed to reject petition: %s", e)

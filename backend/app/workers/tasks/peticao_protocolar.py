"""Taskiq worker for electronic petition filing pipeline.

Pipeline:
  1. Load petition + documents + certificate
  2. Validate each PDF
  3. Sign each PDF with A1 certificate (pyhanko PKCS#7)
  4. Try MNI SOAP first (entregarManifestacaoProcessual via zeep + mTLS)
  5. If MNI fails (403/timeout/blocked), fallback to Playwright RPA via scraper
  6. Update status (protocolada or rejeitada)
  7. Record timeline events

Debug logging habilitado em cada etapa para diagnóstico.
"""

import asyncio
import base64
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

# Mapeamento de tribunal_id (backend) → tribunal_code (scraper)
# Os IDs do backend são "TRF1-1G", "TRF5-JFCE" etc.
# O scraper espera "trf1", "trf5" etc.
TRIBUNAL_SCRAPER_CODES = {
    "TRF1-1G": "trf1",
    "TRF1-2G": "trf1",
    "TRF3-1G": "trf3",
    "TRF3-2G": "trf3",
    "TRF5-JFCE": "trf5",
    "TRF5-REG": "trf5",
    "TRF6-1G": "trf6",
    "TJCE-1G": "tjce",
}

# Tribunais onde o MNI é bloqueado e devemos ir direto para Playwright
MNI_BLOCKED_TRIBUNALS = {"TRF1-1G", "TRF1-2G"}


@broker.task
@with_retry(max_retries=2, initial_delay=30.0, backoff_factor=2.0, max_delay=120.0)
@with_timeout(600.0)  # 10 min — Playwright pode ser lento
async def protocolar_peticao_task(peticao_id: str, tenant_id: str) -> dict:
    """Full filing pipeline: MNI SOAP → fallback Playwright RPA."""
    pet_uuid = UUID(peticao_id)
    tenant_uuid = UUID(tenant_id)

    crypto = CertificateCryptoService(settings.encrypt_key)
    validator = PdfValidatorService(settings.mni_max_file_size_mb)
    signer = PdfSignerService()
    service = PeticaoService()

    logger.info(
        "═══ PROTOCOLAR PETIÇÃO START ═══ peticao_id=%s tenant_id=%s",
        peticao_id, tenant_id,
    )

    async with AsyncSessionLocal() as session:
        # --- Load petition ---
        pet_repo = PeticaoRepository(session, tenant_uuid)
        pet = await pet_repo.get(pet_uuid)
        if pet is None:
            logger.error("[WORKER] Petição não encontrada: %s", peticao_id)
            return {"erro": "Petição não encontrada"}

        logger.info(
            "[WORKER] Petição carregada: status=%s tribunal=%s processo=%s assunto=%s",
            pet.status.value, pet.tribunal_id, pet.processo_numero, pet.assunto,
        )

        if pet.status not in (PeticaoStatus.VALIDANDO, PeticaoStatus.ASSINANDO, PeticaoStatus.PROTOCOLANDO):
            logger.warning("[WORKER] Status inesperado: %s", pet.status)
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

        logger.info(
            "[WORKER] Certificado carregado: titular=%s cpf=%s valido_ate=%s",
            cert.titular_nome, cert.titular_cpf_cnpj, cert.valido_ate,
        )

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

        logger.info("[WORKER] Documentos carregados: %d arquivo(s)", len(docs))
        for i, doc in enumerate(docs):
            logger.info(
                "[WORKER]   Doc[%d]: nome=%s tipo=%s tamanho_encrypted=%d",
                i, doc.nome_original, doc.tipo_documento.value,
                len(doc.conteudo_encrypted) if doc.conteudo_encrypted else 0,
            )

        # --- Transition to ASSINANDO ---
        try:
            await service.transition_status(
                session, tenant_uuid, pet_uuid,
                PeticaoStatus.ASSINANDO,
                "Validando e assinando documentos",
            )
            await session.commit()
            logger.info("[WORKER] Status → ASSINANDO")
        except ValueError:
            pass  # Already in a valid state

        # --- Validate + Sign each document ---
        documentos_para_mni = []
        documentos_pdf_raw = []  # Para Playwright (PDF sem assinar)

        for doc in docs:
            # Decrypt
            pdf_bytes = crypto.decrypt(doc.conteudo_encrypted)
            logger.info(
                "[WORKER] PDF decriptado: %s → %d bytes (%.1f KB)",
                doc.nome_original, len(pdf_bytes), len(pdf_bytes) / 1024,
            )

            # Validate
            result = validator.validate(pdf_bytes, doc.nome_original)
            if not result.valid:
                logger.error("[WORKER] PDF inválido: %s → %s", doc.nome_original, result.error)
                await _reject(
                    service, session, tenant_uuid, pet_uuid,
                    f"Documento inválido: {doc.nome_original}",
                    detalhes=result.error,
                )
                return {"erro": result.error}
            logger.info("[WORKER] PDF validado OK: %s", doc.nome_original)

            # Guardar PDF raw para Playwright (não precisa de assinatura pyhanko)
            documentos_pdf_raw.append({
                "conteudo": pdf_bytes,
                "nome": doc.nome_original,
                "tipo_documento": doc.tipo_documento.value,
            })

            # Sign with A1 certificate (run in thread — pyhanko internals)
            try:
                signed_bytes = await asyncio.to_thread(
                    signer.sign_in_memory,
                    pdf_bytes, cert.pfx_encrypted, cert.pfx_password_encrypted, crypto,
                )
                logger.info(
                    "[WORKER] PDF assinado: %s → %d bytes",
                    doc.nome_original, len(signed_bytes),
                )
            except Exception as e:
                logger.warning(
                    "[WORKER] Falha ao assinar %s: %s (prosseguindo para Playwright sem assinatura)",
                    doc.nome_original, e,
                )
                signed_bytes = pdf_bytes  # Fallback: usar PDF sem assinatura pyhanko

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
                "Enviando ao tribunal",
            )
            await session.commit()
            logger.info("[WORKER] Status → PROTOCOLANDO")
        except ValueError:
            pass

        # --- Get tribunal config ---
        from app.api.v1.endpoints.tribunais import get_tribunal_config
        tribunal = get_tribunal_config(pet.tribunal_id)

        # --- Decidir estratégia: MNI ou Playwright ---
        use_playwright = pet.tribunal_id in MNI_BLOCKED_TRIBUNALS
        mni_failed = False

        if not use_playwright and tribunal and tribunal.get("suportaMNI") and tribunal.get("wsdlEndpoint"):
            # --- Tentar MNI SOAP primeiro ---
            logger.info(
                "[WORKER] ═══ TENTANDO MNI SOAP ═══ tribunal=%s wsdl=%s",
                pet.tribunal_id, tribunal["wsdlEndpoint"],
            )

            try:
                mni = MniSoapClient(crypto)
                filing_result = await asyncio.to_thread(
                    mni.entregar_manifestacao_processual,
                    wsdl_url=tribunal["wsdlEndpoint"],
                    pfx_encrypted=cert.pfx_encrypted,
                    pfx_password_encrypted=cert.pfx_password_encrypted,
                    id_manifestante=cert.titular_cpf_cnpj.replace(".", "").replace("-", "").replace("/", ""),
                    numero_processo=pet.processo_numero,
                    documentos=documentos_para_mni,
                    dados_basicos_json=pet.dados_basicos_json,
                )

                if filing_result.sucesso:
                    logger.info(
                        "[WORKER] MNI SUCESSO! protocolo=%s msg=%s",
                        filing_result.numero_protocolo, filing_result.mensagem,
                    )
                    return await _handle_success(
                        pet_repo, service, session, tenant_uuid, pet_uuid, pet,
                        filing_result.numero_protocolo,
                        filing_result.recibo_base64,
                        filing_result.mensagem,
                        peticao_id,
                        "MNI/SOAP",
                    )
                else:
                    logger.warning(
                        "[WORKER] MNI REJEITOU: %s", filing_result.mensagem,
                    )
                    # Se MNI rejeitou com mensagem de negócio, não fazer fallback
                    if _is_business_rejection(filing_result.mensagem):
                        await _reject(
                            service, session, tenant_uuid, pet_uuid,
                            "Tribunal rejeitou a petição via MNI",
                            detalhes=filing_result.mensagem,
                        )
                        return {"sucesso": False, "erro": filing_result.mensagem}
                    # Senão, pode ser erro de infra → tentar Playwright
                    mni_failed = True

            except Exception as e:
                logger.warning(
                    "[WORKER] MNI FALHOU com exceção: %s — tentando Playwright",
                    str(e),
                )
                mni_failed = True
        else:
            logger.info(
                "[WORKER] MNI pulado (tribunal=%s bloqueado=%s suportaMNI=%s wsdl=%s) → Playwright",
                pet.tribunal_id,
                pet.tribunal_id in MNI_BLOCKED_TRIBUNALS,
                tribunal.get("suportaMNI") if tribunal else "N/A",
                tribunal.get("wsdlEndpoint") if tribunal else "N/A",
            )
            use_playwright = True

        # --- Fallback: Playwright RPA ---
        if use_playwright or mni_failed:
            scraper_code = TRIBUNAL_SCRAPER_CODES.get(pet.tribunal_id)
            if not scraper_code:
                logger.error(
                    "[WORKER] Tribunal %s não tem código scraper configurado", pet.tribunal_id,
                )
                await _reject(
                    service, session, tenant_uuid, pet_uuid,
                    f"Tribunal {pet.tribunal_id} não suportado para peticionamento Playwright",
                )
                return {"erro": f"Tribunal {pet.tribunal_id} sem suporte Playwright"}

            logger.info(
                "[WORKER] ═══ TENTANDO PLAYWRIGHT RPA ═══ tribunal=%s → scraper_code=%s %s",
                pet.tribunal_id, scraper_code,
                "(fallback após MNI falhar)" if mni_failed else "(direto, MNI bloqueado)",
            )

            try:
                await service.transition_status(
                    session, tenant_uuid, pet_uuid,
                    PeticaoStatus.PROTOCOLANDO,
                    f"Enviando ao tribunal via Playwright {'(fallback)' if mni_failed else ''}",
                )
                await session.commit()
            except ValueError:
                pass

            # Preparar dados: PFX em base64, PDF em base64
            pfx_raw = crypto.decrypt(cert.pfx_encrypted)
            pfx_password_raw = crypto.decrypt(cert.pfx_password_encrypted).decode("utf-8")
            pfx_b64 = base64.b64encode(pfx_raw).decode("ascii")

            # Extrair segredo TOTP se configurado no certificado
            totp_secret_raw = None
            if cert.totp_secret_encrypted:
                try:
                    totp_secret_raw = crypto.decrypt(cert.totp_secret_encrypted).decode("utf-8")
                    logger.info("[WORKER] TOTP secret extraído do certificado (%d chars)", len(totp_secret_raw))
                except Exception as e:
                    logger.warning("[WORKER] Falha ao descriptografar totp_secret: %s", e)

            # Usar o primeiro documento (principal)
            principal_doc = documentos_pdf_raw[0]
            pdf_b64 = base64.b64encode(principal_doc["conteudo"]).decode("ascii")

            logger.info(
                "[WORKER] Chamando scraper: pfx=%d bytes, pdf=%d bytes, tipo=%s, desc=%s",
                len(pfx_raw), len(principal_doc["conteudo"]),
                principal_doc["tipo_documento"], pet.assunto[:50] if pet.assunto else "",
            )

            from app.core.services.scraper_client import protocolar_via_scraper

            scraper_result = await protocolar_via_scraper(
                tribunal=scraper_code,
                numero_processo=pet.processo_numero,
                pfx_base64=pfx_b64,
                pfx_password=pfx_password_raw,
                pdf_base64=pdf_b64,
                tipo_documento=principal_doc["tipo_documento"],
                descricao=pet.assunto or principal_doc["nome"],
                totp_secret=totp_secret_raw,
            )

            logger.info(
                "[WORKER] Playwright result: sucesso=%s protocolo=%s msg=%s screenshots=%s",
                scraper_result.get("sucesso"),
                scraper_result.get("numero_protocolo"),
                scraper_result.get("mensagem", "")[:200],
                scraper_result.get("screenshots", []),
            )

            if scraper_result.get("sucesso"):
                return await _handle_success(
                    pet_repo, service, session, tenant_uuid, pet_uuid, pet,
                    scraper_result.get("numero_protocolo"),
                    None,  # Playwright não gera recibo
                    scraper_result.get("mensagem", ""),
                    peticao_id,
                    "Playwright/RPA",
                )
            else:
                await _reject(
                    service, session, tenant_uuid, pet_uuid,
                    "Peticionamento falhou via Playwright",
                    detalhes=scraper_result.get("mensagem", ""),
                )
                return {"sucesso": False, "erro": scraper_result.get("mensagem")}

        # Se chegou aqui, algo deu errado
        await _reject(service, session, tenant_uuid, pet_uuid, "Nenhuma estratégia de envio disponível")
        return {"erro": "Nenhuma estratégia de envio disponível"}


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


def _is_business_rejection(mensagem: str) -> bool:
    """Verifica se a rejeição é regra de negócio (não retry) ou infra (pode retry/fallback)."""
    if not mensagem:
        return False
    msg_lower = mensagem.lower()
    # Rejeições de negócio — não fazer fallback
    business_keywords = [
        "processo não encontrado",
        "processo não ativo",
        "prazo expirado",
        "documento duplicado",
        "tipo de documento inválido",
        "assinatura inválida",
        "certificado não autorizado",
    ]
    return any(kw in msg_lower for kw in business_keywords)


async def _handle_success(
    pet_repo, service, session, tenant_uuid, pet_uuid, pet,
    numero_protocolo, recibo_base64, mensagem, peticao_id, via,
) -> dict:
    """Atualiza a petição como PROTOCOLADA e cria processo monitorado."""
    logger.info(
        "[WORKER] ═══ PETIÇÃO PROTOCOLADA via %s ═══ protocolo=%s",
        via, numero_protocolo,
    )

    await pet_repo.update(
        pet_uuid,
        status=PeticaoStatus.PROTOCOLADA,
        numero_protocolo=numero_protocolo,
        protocolado_em=datetime.now(timezone.utc),
        protocolo_recibo=recibo_base64,
    )
    await service._record_evento(
        session, tenant_uuid, pet_uuid,
        PeticaoStatus.PROTOCOLADA,
        f"Protocolo {numero_protocolo} recebido pelo tribunal (via {via})",
        detalhes=mensagem,
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
            logger.info("[WORKER] Auto-created monitored process for %s", numero_clean)
    except Exception as e:
        logger.warning("[WORKER] Failed to auto-create monitored process: %s", e)

    logger.info(
        "[WORKER] Petition filed successfully via %s",
        via,
        extra={
            "peticao_id": peticao_id,
            "protocolo": numero_protocolo,
            "tribunal": pet.tribunal_id,
            "via": via,
        },
    )
    return {
        "sucesso": True,
        "protocolo": numero_protocolo,
        "mensagem": mensagem,
        "via": via,
    }


async def _reject(
    service: PeticaoService,
    session,
    tenant_id: UUID,
    peticao_id: UUID,
    descricao: str,
    detalhes: str | None = None,
) -> None:
    """Helper to transition petition to REJEITADA status."""
    logger.info(
        "[WORKER] REJEITANDO petição %s: %s | detalhes=%s",
        peticao_id, descricao, detalhes[:200] if detalhes else "N/A",
    )
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
        logger.error("[WORKER] Failed to reject petition: %s", e)

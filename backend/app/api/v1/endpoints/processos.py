"""API endpoints for real-time process consultation via MNI 2.2.2 and DataJud."""

import asyncio
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_tenant_id, get_current_user
from app.core.services.certificados.crypto import CertificateCryptoService
from app.db.engine import get_db
from app.db.models.user import User
from app.db.repositories.certificado_digital import CertificadoDigitalRepository
from app.schemas.processo import (
    ConsultarOABRequest,
    ConsultarOABResponse,
    ConsultarProcessoRequest,
    ProcessoConsultaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/processos")


class ConsultarDatajudRequest(BaseModel):
    """POST /processos/consultar-datajud request body."""

    numero_processo: str
    tribunal_id: Optional[str] = None  # Optional: auto-detected from number if omitted


def _get_crypto_service() -> CertificateCryptoService:
    from app.config import settings
    return CertificateCryptoService(settings.encrypt_key)


@router.post("/consultar", response_model=ProcessoConsultaResponse)
async def consultar_processo(
    data: ConsultarProcessoRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Consult a process in real-time via MNI 2.2.2 consultarProcesso.

    Returns structured process data: cabecalho, polos (parties), assuntos,
    orgaoJulgador, movimentos, documentos metadata, and raw response for audit.
    Requires a valid A1 ICP-Brasil certificate with mTLS.
    """
    from app.api.v1.endpoints.tribunais import get_tribunal_config
    from app.core.services.peticoes.mni_client import MniSoapClient

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

    # Call MNI in thread pool (zeep is synchronous)
    raw_result = await asyncio.to_thread(
        mni.consultar_processo,
        wsdl_url=tribunal["wsdlEndpoint"],
        pfx_encrypted=cert.pfx_encrypted,
        pfx_password_encrypted=cert.pfx_password_encrypted,
        numero_processo=data.numero_processo,
        id_consultante=cpf,
    )

    # Parse raw zeep response into structured fields
    parsed = MniSoapClient.parse_consulta_response(raw_result)

    logger.info(
        "consultarProcesso via /processos",
        extra={
            "processo": data.numero_processo,
            "tribunal": data.tribunal_id,
            "sucesso": parsed.get("sucesso"),
            "polos_count": len(parsed.get("polos", [])),
            "movimentos_count": len(parsed.get("movimentos", [])),
        },
    )

    return parsed


@router.post("/consultar-datajud")
async def consultar_datajud(
    data: ConsultarDatajudRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Consult a process via DataJud public CNJ API (no certificate required).

    Auto-detects the tribunal from the process number if tribunal_id is omitted.
    Returns structured metadata: classe, orgaoJulgador, assuntos, movimentos.
    NOTE: DataJud does NOT return parties (partes) — use MNI for full party data.
    """
    from app.core.services.datajud_service import consultar_datajud as _consultar

    result = await _consultar(
        numero_processo=data.numero_processo,
        tribunal_id=data.tribunal_id,
    )

    logger.info(
        "DataJud query via /processos/consultar-datajud",
        extra={
            "processo": data.numero_processo,
            "tribunal": data.tribunal_id,
            "sucesso": result.get("sucesso"),
            "total": result.get("total"),
        },
    )

    return result


@router.post("/consultar-oab", response_model=ConsultarOABResponse)
async def consultar_oab(
    data: ConsultarOABRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Search processes by OAB number via web scraping of TRF1 public consultation.

    No certificate required — uses the public consultation page.
    May take 5-15 seconds as it accesses the tribunal website in real-time.
    """
    from app.core.services.oab_finder_service import consultar_oab as _consultar_oab

    result = await _consultar_oab(
        oab_numero=data.oab_numero,
        oab_uf=data.oab_uf,
    )

    logger.info(
        "OAB Finder query via /processos/consultar-oab",
        extra={
            "oab": data.oab_numero,
            "uf": data.oab_uf,
            "sucesso": result.get("sucesso"),
            "total": result.get("total"),
        },
    )

    return result

"""API endpoints for digital certificate management (A1 ICP-Brasil)."""

import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth.dependencies import get_current_tenant_id, get_current_user
from app.core.services.certificados.crypto import CertificateCryptoService
from app.db.engine import get_db
from app.db.models.user import User
from app.db.repositories.certificado_digital import CertificadoDigitalRepository
from app.schemas.certificado import (
    CertificadoListResponse,
    CertificadoResponse,
    CertificadoTesteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificados", tags=["certificados"])


def _get_crypto_service() -> CertificateCryptoService:
    """Create crypto service with configured encryption key."""
    return CertificateCryptoService(settings.encrypt_key)


@router.get("", response_model=CertificadoListResponse)
async def list_certificados(
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CertificadoListResponse:
    """List all active (non-revoked) certificates for the tenant."""
    repo = CertificadoDigitalRepository(session, tenant_id)
    certs = await repo.get_active()

    return CertificadoListResponse(
        items=[CertificadoResponse.model_validate(c) for c in certs],
        total=len(certs),
    )


@router.get("/{cert_id}", response_model=CertificadoResponse)
async def get_certificado(
    cert_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CertificadoResponse:
    """Get a single certificate by ID."""
    repo = CertificadoDigitalRepository(session, tenant_id)
    cert = await repo.get(cert_id)

    if cert is None or cert.revogado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado não encontrado",
        )

    return CertificadoResponse.model_validate(cert)


@router.post("", response_model=CertificadoResponse, status_code=status.HTTP_201_CREATED)
async def upload_certificado(
    arquivo: UploadFile = File(..., description="Arquivo PFX/P12"),
    nome: str = Form(..., min_length=1, max_length=255, description="Nome amigável"),
    senha_pfx: str = Form(..., min_length=1, description="Senha do arquivo PFX"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CertificadoResponse:
    """
    Upload and store a new A1 digital certificate.

    Accepts a PFX/P12 file, validates it with the provided password,
    extracts metadata, encrypts the blob with Fernet, and stores it.
    The password is also encrypted and stored for future mTLS operations.
    """
    # Validate file extension
    if arquivo.filename and not arquivo.filename.lower().endswith((".pfx", ".p12")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser .pfx ou .p12",
        )

    # Read file content
    pfx_bytes = await arquivo.read()
    if not pfx_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio",
        )

    # Validate and extract metadata
    crypto = _get_crypto_service()
    try:
        metadata = crypto.extract_metadata(pfx_bytes, senha_pfx)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Check for duplicate serial number
    repo = CertificadoDigitalRepository(session, tenant_id)
    existing = await repo.get_by_serial(metadata.serial_number)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificado com serial {metadata.serial_number} já cadastrado",
        )

    # Encrypt PFX blob and password
    pfx_encrypted = crypto.encrypt(pfx_bytes)
    password_encrypted = crypto.encrypt_password(senha_pfx)

    # Create record
    cert = await repo.create(
        nome=nome,
        titular_nome=metadata.titular_nome,
        titular_cpf_cnpj=metadata.titular_cpf_cnpj,
        emissora=metadata.emissora,
        serial_number=metadata.serial_number,
        valido_de=metadata.valido_de,
        valido_ate=metadata.valido_ate,
        pfx_encrypted=pfx_encrypted,
        pfx_password_encrypted=password_encrypted,
    )
    await session.commit()

    logger.info(
        "Certificate uploaded",
        extra={
            "cert_id": str(cert.id),
            "tenant_id": str(tenant_id),
            "titular": metadata.titular_nome,
            "serial": metadata.serial_number,
        },
    )

    return CertificadoResponse.model_validate(cert)


@router.post("/{cert_id}/testar", response_model=CertificadoTesteResponse)
async def testar_certificado(
    cert_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CertificadoTesteResponse:
    """
    Test mTLS handshake with a tribunal endpoint using this certificate.

    Attempts an HTTPS connection to a PJe MNI endpoint using the
    decrypted certificate for mutual TLS authentication.
    """
    repo = CertificadoDigitalRepository(session, tenant_id)
    cert = await repo.get(cert_id)

    if cert is None or cert.revogado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado não encontrado",
        )

    crypto = _get_crypto_service()

    # Default test endpoint: TRF5-JFCE (known stable PJe MNI endpoint)
    test_url = "https://pje.jfce.jus.br/pje/intercomunicacao?wsdl"

    sucesso = False
    mensagem = ""

    try:
        with crypto.mtls_tempfiles(cert.pfx_encrypted, cert.pfx_password_encrypted) as (
            cert_path,
            key_path,
        ):
            # Attempt mTLS handshake
            async with httpx.AsyncClient(
                cert=(cert_path, key_path),
                verify=True,
                timeout=httpx.Timeout(15.0),
            ) as client:
                response = await client.get(test_url)
                if response.status_code == 200:
                    sucesso = True
                    mensagem = (
                        f"Handshake mTLS bem-sucedido com {test_url} "
                        f"(HTTP {response.status_code})"
                    )
                else:
                    mensagem = (
                        f"Conexão estabelecida mas retornou HTTP {response.status_code}"
                    )
                    # Still consider it a success if we got past TLS
                    sucesso = response.status_code < 500

    except httpx.ConnectError as e:
        mensagem = f"Falha na conexão mTLS: {e}"
    except httpx.TimeoutException:
        mensagem = "Timeout na conexão com o tribunal (15s)"
    except ValueError as e:
        mensagem = f"Erro ao descriptografar certificado: {e}"
    except Exception as e:
        mensagem = f"Erro inesperado: {type(e).__name__}: {e}"
        logger.exception("Certificate test failed", extra={"cert_id": str(cert_id)})

    # Update test result in DB
    from datetime import datetime, timezone

    await repo.update(
        cert_id,
        ultimo_teste_em=datetime.now(timezone.utc),
        ultimo_teste_resultado="sucesso" if sucesso else "falha",
        ultimo_teste_mensagem=mensagem,
    )
    await session.commit()

    return CertificadoTesteResponse(sucesso=sucesso, mensagem=mensagem)


@router.delete("/{cert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_certificado(
    cert_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete (revoke) a certificate."""
    repo = CertificadoDigitalRepository(session, tenant_id)
    cert = await repo.get(cert_id)

    if cert is None or cert.revogado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado não encontrado",
        )

    await repo.update(cert_id, revogado=True)
    await session.commit()

    logger.info(
        "Certificate revoked",
        extra={"cert_id": str(cert_id), "tenant_id": str(tenant_id)},
    )

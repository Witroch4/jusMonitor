"""User profile self-service endpoints."""

import logging
import os
import uuid as uuid_mod
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import CurrentUser
from app.core.auth.password import hash_password, verify_password
from app.db.engine import get_session
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.profile import (
    ChangePasswordRequest,
    ProfileResponse,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["profile"])


def _build_profile_response(user: User) -> ProfileResponse:
    """Build a ProfileResponse from a User model instance."""
    oab_formatted = None
    if user.oab_number and user.oab_state:
        num = user.oab_number
        if len(num) > 3:
            num = f"{num[:-3]}.{num[-3:]}"
        oab_formatted = f"OAB/{user.oab_state} {num}"

    cpf_formatted = None
    if user.cpf:
        d = user.cpf
        if len(d) == 11:
            cpf_formatted = f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

    return ProfileResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        tenant_id=str(user.tenant_id),
        phone=user.phone,
        avatar_url=user.avatar_url,
        oab_number=user.oab_number,
        oab_state=user.oab_state,
        oab_formatted=oab_formatted,
        cpf=user.cpf,
        cpf_formatted=cpf_formatted,
    )


@router.get("", response_model=ProfileResponse)
async def get_profile(user: CurrentUser) -> ProfileResponse:
    """Get current user's full profile."""
    return _build_profile_response(user)


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    data: UpdateProfileRequest,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileResponse:
    """Update current user's profile fields."""
    user_repo = UserRepository(session, user.tenant_id)
    update_data = data.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar",
        )

    updated = await user_repo.update(user.id, **update_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    # Auto-create OABSyncConfig when user sets OAB number
    oab_number = update_data.get("oab_number") or updated.oab_number
    oab_state = update_data.get("oab_state") or updated.oab_state
    if oab_number and oab_state:
        from app.db.repositories.caso_oab import OABSyncConfigRepository

        sync_repo = OABSyncConfigRepository(session, user.tenant_id)
        await sync_repo.get_or_create(oab_number, oab_state)

    await session.commit()
    return _build_profile_response(updated)


@router.post("/avatar", response_model=ProfileResponse)
async def upload_avatar(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
) -> ProfileResponse:
    """Upload a new avatar image. Accepts JPEG, PNG, WEBP. Max 2MB."""
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_SIZE = 2 * 1024 * 1024  # 2MB

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de arquivo inválido. Use JPEG, PNG ou WEBP.",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo muito grande. Máximo 2MB.",
        )

    ext = file.content_type.split("/")[-1]
    if ext == "jpeg":
        ext = "jpg"
    filename = f"avatars/{user.id}_{uuid_mod.uuid4().hex[:8]}.{ext}"

    os.makedirs("static/avatars", exist_ok=True)
    filepath = f"static/{filename}"
    with open(filepath, "wb") as f:
        f.write(contents)

    avatar_url = f"/static/{filename}"
    user_repo = UserRepository(session, user.tenant_id)
    updated = await user_repo.update(user.id, avatar_url=avatar_url)
    await session.commit()

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    return _build_profile_response(updated)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Change current user's password."""
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )

    new_hash = hash_password(data.new_password)
    user_repo = UserRepository(session, user.tenant_id)
    await user_repo.update(user.id, password_hash=new_hash)
    await session.commit()

    logger.info(
        "User changed password",
        extra={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
    )

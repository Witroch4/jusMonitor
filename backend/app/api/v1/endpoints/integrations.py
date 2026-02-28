"""Integration management endpoints."""

import base64
import logging
import secrets
import uuid as uuid_mod
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import CurrentUser
from app.core.services.instagram_oauth import (
    encrypt_token,
    exchange_code_for_token,
    fetch_instagram_profile,
    get_authorization_url,
)
from app.db.engine import get_session
from app.db.repositories.user_integration_repository import UserIntegrationRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/instagram/authorize")
async def instagram_authorize(user: CurrentUser) -> RedirectResponse:
    """
    Initiate Instagram OAuth flow.

    Generates a CSRF state token encoding user_id:tenant_id:random
    and redirects to Instagram authorization page.
    """
    random_part = secrets.token_urlsafe(16)
    state_plain = f"{user.id}:{user.tenant_id}:{random_part}"
    state = base64.urlsafe_b64encode(state_plain.encode()).decode()

    auth_url = get_authorization_url(state=state)
    logger.info(
        "Instagram OAuth initiated",
        extra={"user_id": str(user.id), "tenant_id": str(user.tenant_id)},
    )
    return RedirectResponse(url=auth_url)


@router.get("/instagram/callback")
async def instagram_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Handle Instagram OAuth callback.

    Called by the frontend page after Instagram redirects back.
    Decodes user context from the state parameter.
    """
    # Decode state to get user_id and tenant_id
    try:
        decoded = base64.urlsafe_b64decode(state.encode()).decode()
        parts = decoded.split(":")
        user_id = uuid_mod.UUID(parts[0])
        tenant_id = uuid_mod.UUID(parts[1])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado OAuth inválido",
        )

    # Exchange code for token
    try:
        token_data = await exchange_code_for_token(code)
    except Exception as e:
        logger.error("instagram_token_exchange_failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao trocar código pelo token do Instagram",
        )

    # Fetch Instagram profile
    access_token = token_data["access_token"]
    try:
        ig_profile = await fetch_instagram_profile(access_token)
    except Exception as e:
        logger.error("instagram_profile_fetch_failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao buscar perfil do Instagram",
        )

    # Encrypt and store the token
    encrypted_token = encrypt_token(access_token)
    expires_in = token_data.get("expires_in", 5184000)  # Default 60 days
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    integration_repo = UserIntegrationRepository(session, tenant_id)
    existing = await integration_repo.get_by_user_and_type(user_id, "instagram")

    if existing:
        await integration_repo.update(
            existing.id,
            access_token_encrypted=encrypted_token,
            token_expires_at=expires_at,
            external_user_id=ig_profile.get("id"),
            external_username=ig_profile.get("username"),
            external_profile_picture_url=ig_profile.get("profile_picture_url"),
            is_active=True,
        )
    else:
        await integration_repo.create(
            user_id=user_id,
            integration_type="instagram",
            access_token_encrypted=encrypted_token,
            token_expires_at=expires_at,
            external_user_id=ig_profile.get("id"),
            external_username=ig_profile.get("username"),
            external_profile_picture_url=ig_profile.get("profile_picture_url"),
            is_active=True,
        )

    await session.commit()

    logger.info(
        "Instagram connected",
        extra={
            "user_id": str(user_id),
            "ig_username": ig_profile.get("username"),
        },
    )

    return {
        "status": "connected",
        "username": ig_profile.get("username"),
        "profile_picture_url": ig_profile.get("profile_picture_url"),
    }


@router.get("/instagram")
async def get_instagram_integration(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Get current user's Instagram integration status."""
    integration_repo = UserIntegrationRepository(session, user.tenant_id)
    integration = await integration_repo.get_by_user_and_type(user.id, "instagram")

    if not integration or not integration.is_active:
        return {"connected": False}

    return {
        "connected": True,
        "username": integration.external_username,
        "profile_picture_url": integration.external_profile_picture_url,
        "token_expires_at": (
            integration.token_expires_at.isoformat()
            if integration.token_expires_at
            else None
        ),
    }


@router.delete("/instagram", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_instagram(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Disconnect Instagram integration."""
    integration_repo = UserIntegrationRepository(session, user.tenant_id)
    integration = await integration_repo.get_by_user_and_type(user.id, "instagram")

    if integration:
        await integration_repo.update(
            integration.id,
            is_active=False,
            access_token_encrypted=None,
        )
        await session.commit()

        logger.info(
            "Instagram disconnected",
            extra={"user_id": str(user.id)},
        )

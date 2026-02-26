"""Pydantic schemas package."""

from app.schemas.auth import LoginRequest, TokenResponse, RefreshTokenRequest, UserInfo
from app.schemas.chatwit import ChatwitWebhookPayload
from app.schemas.client import (
    ClientAutomationConfig,
    ClientAutomationResponse,
    ClientCreate,
    ClientHealthResponse,
    ClientListResponse,
    ClientNoteCreate,
    ClientNoteResponse,
    ClientResponse,
    ClientUpdate,
)
from app.schemas.lead import (
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    LeadScoreUpdate,
    LeadStageUpdate,
    LeadUpdate,
)

__all__ = [
    # Auth
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserInfo",
    # Chatwit
    "ChatwitWebhookPayload",
    # Client
    "ClientCreate",
    "ClientUpdate",
    "ClientResponse",
    "ClientListResponse",
    "ClientHealthResponse",
    "ClientNoteCreate",
    "ClientNoteResponse",
    "ClientAutomationConfig",
    "ClientAutomationResponse",
    # Lead
    "LeadCreate",
    "LeadUpdate",
    "LeadResponse",
    "LeadListResponse",
    "LeadStageUpdate",
    "LeadScoreUpdate",
]

"""Pydantic schemas for authentication endpoints."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request payload."""
    
    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User password",
    )
    tenant_id: UUID = Field(
        ...,
        description="Tenant ID (law firm identifier)",
    )


class TokenResponse(BaseModel):
    """Token response payload."""
    
    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""
    
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
    )


class UserInfo(BaseModel):
    """User information in token response."""
    
    user_id: UUID
    email: str
    full_name: str
    role: str
    tenant_id: UUID
    
    class Config:
        from_attributes = True

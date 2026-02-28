"""Pydantic schemas for user profile self-service operations."""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


BRAZILIAN_STATES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


class UpdateProfileRequest(BaseModel):
    """Request body for updating user profile."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    oab_number: Optional[str] = Field(
        None, max_length=20, description="OAB number digits only"
    )
    oab_state: Optional[str] = Field(None, max_length=2)

    @field_validator("oab_state")
    @classmethod
    def validate_oab_state(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in BRAZILIAN_STATES:
            raise ValueError(f"Estado OAB inválido: {v}")
        return v.upper() if v else v

    @field_validator("oab_number")
    @classmethod
    def validate_oab_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^\d{1,7}$", v):
            raise ValueError("Número OAB deve conter apenas dígitos (máx. 7)")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            digits = re.sub(r"\D", "", v)
            if len(digits) < 10 or len(digits) > 11:
                raise ValueError("Telefone inválido")
        return v


class ChangePasswordRequest(BaseModel):
    """Request body for changing password."""

    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Senhas não conferem")
        return v


class ProfileResponse(BaseModel):
    """Full profile response including all fields."""

    user_id: str
    email: str
    full_name: str
    role: str
    tenant_id: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    oab_number: Optional[str] = None
    oab_state: Optional[str] = None
    oab_formatted: Optional[str] = None

    model_config = {"from_attributes": True}


class UpdatePreferencesRequest(BaseModel):
    """Request body for updating notification preferences."""

    movimentacoes: Optional[bool] = None
    prazos: Optional[bool] = None
    leads_novos: Optional[bool] = None
    atualizacoes_sistema: Optional[bool] = None

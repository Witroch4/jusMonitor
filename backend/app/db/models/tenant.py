"""Tenant model for multi-tenant isolation."""

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class Tenant(BaseModel):
    """
    Tenant model representing a law firm/office.
    
    All other entities in the system are associated with a tenant
    to ensure complete data isolation between different law firms.
    """
    
    __tablename__ = "tenants"
    
    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Law firm name",
    )
    
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-friendly identifier",
    )
    
    # Plan and status
    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="basic",
        comment="Subscription plan (basic, professional, enterprise)",
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether tenant is active",
    )
    
    # Configuration
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Tenant-specific settings and preferences",
    )
    
    # Relationships
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, slug={self.slug}, name={self.name})>"

"""User model for authentication and authorization."""

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TenantBaseModel


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    
    ADMIN = "admin"
    LAWYER = "lawyer"
    ASSISTANT = "assistant"
    VIEWER = "viewer"


class User(TenantBaseModel):
    """
    User model for authentication and authorization.
    
    Users belong to a tenant (law firm) and have specific roles
    that determine their permissions within the system.
    """
    
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    
    # Foreign keys
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User email address (unique per tenant)",
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )
    
    # Profile
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User full name",
    )
    
    # Authorization
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.LAWYER,
        index=True,
        comment="User role for RBAC",
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether user account is active",
    )
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login timestamp",
    )
    
    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        foreign_keys=[tenant_id],
        lazy="selectin",
    )
    
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def has_role(self, *roles: UserRole) -> bool:
        """Check if user has any of the specified roles."""
        return self.role in roles
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN

"""SQLAlchemy declarative base and common mixins."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    
    # Type annotation map for common types
    type_annotation_map = {
        UUID: PGUUID(as_uuid=True),
    }


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )


class TenantMixin:
    """Mixin for multi-tenant isolation."""
    
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )


# Convenience base classes
class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID primary key and timestamps."""
    
    __abstract__ = True
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TenantBaseModel(BaseModel, TenantMixin):
    """Base model with tenant isolation, UUID primary key, and timestamps."""
    
    __abstract__ = True

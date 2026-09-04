"""Unified Base model for all database entities across services - SQLAlchemy 2.x Style"""
from typing import Any
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, registry


class Base(DeclarativeBase):
    """Unified base class for all SQLAlchemy models in DT-Lite V4.0
    
    Both Identity and Core services must use this single Base
    to ensure metadata is consolidated in one Alembic migration.
    Uses SQLAlchemy 2.x Typed ORM (Mapped[] + mapped_column).
    """
    pass


class TimestampMixin:
    """Mixing providing created_at and updated_at columns."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class SoftDeleteMixin:
    """Mixing providing soft delete support via deleted_at column."""
    
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None
    )
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark this instance as deleted (soft delete)."""
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restore a soft-deleted instance."""
        self.deleted_at = None

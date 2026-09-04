"""Persistent TwinEntity — Database-backed twin instance.

This is the PERSISTENT representation of a twin entity.
It is distinct from the runtime TwinEntity dataclass in services/twin/models.py.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.core.models.base import Base, SoftDeleteMixin
from services.twin.models.definition import TwinDefinition


class PersistentTwinEntity(Base, SoftDeleteMixin):
    """Persistent twin entity instance.

    Represents an actual running twin instance that corresponds to
    a TwinDefinition type.

    Example:
        Definition: "hvac_unit"
        Instance:   "AHU-001" (the actual HVAC unit in Building A)

    Key difference from runtime TwinEntity:
        - This model has database persistence (PostgreSQL)
        - Runtime state is kept in memory (TwinEntityRegistry)
        - This model provides identity and lifecycle management
    """
    __tablename__ = "twin_entities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_definitions.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(
        String(256), nullable=False,
        doc="External identifier (e.g., device serial number)"
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False,
        doc="Human-readable name"
    )
    meta_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        name="metadata",  # Database column is "metadata" for consistency
        doc="Runtime metadata (NOT state — state is in registry)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships - using backref instead of back_populates to avoid circular issues
    definition: Mapped["TwinDefinition"] = relationship(
        "TwinDefinition", back_populates="entities"
    )

    __table_args__ = (
        Index("ix_twin_ent_tenant_external", "tenant_id", "external_id"),
        Index("ix_twin_ent_definition", "definition_id"),
    )

    def __repr__(self) -> str:
        return f"<PersistentTwinEntity(id={self.id}, name={self.name!r})>"

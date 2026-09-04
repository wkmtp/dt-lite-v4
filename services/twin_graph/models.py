"""TwinRelationship — Semantic connection between PersistentTwinEntities."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from services.core.models.base import Base, SoftDeleteMixin


class TwinRelationship(Base, SoftDeleteMixin):
    """Semantic relationship between two twin entities.

    Represents directed edges in the twin graph:
        Source TwinEntity --[relationship_type]--> Target TwinEntity

    Examples:
        Building-A --contains--> Floor-1
        Floor-1   --contains--> Room-101
        Room-101  --hosts-->     Sensor-001

    Relationship types are data-driven strings — never hardcoded.
    """
    __tablename__ = "twin_relationships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    source_twin_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_twin_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        doc="Semantic type (e.g., 'contains', 'located_in', 'controls')"
    )
    meta_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        name="metadata",
        server_default=text("'{}'::jsonb"),
        doc="Additional relationship metadata"
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

    __table_args__ = (
        CheckConstraint(
            "source_twin_id != target_twin_id",
            name="ck_no_self_reference",
        ),
        Index("ix_twin_rel_source", "source_twin_id"),
        Index("ix_twin_rel_target", "target_twin_id"),
        Index("ix_twin_rel_type", "relationship_type"),
        Index("ix_twin_rel_all", "tenant_id", "source_twin_id", "target_twin_id", "relationship_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<TwinRelationship(id={self.id}, "
            f"{self.source_twin_id}--[{self.relationship_type}]-->{self.target_twin_id})>"
        )

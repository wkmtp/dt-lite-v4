"""TwinBinding — Decoupled binding between Device and TwinEntity.

This binding connects physical devices to their digital twin representations
without creating a tight coupling in the domain models.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from services.core.models.base import Base


class TwinBinding(Base):
    """Binding between a Device and a TwinEntity instance.

    This model creates a decoupled relationship:
        Device (physical) <-> TwinBinding <-> TwinEntity (digital)

    Key points:
        - Not stored on Device model (Task 5 remains frozen)
        - Not stored on TwinEntity runtime model (Task 8 remains frozen)
        - Separate table allows multiple mappings (one device -> many twins)
    """
    __tablename__ = "twin_bindings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    twin_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    binding_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="mirror",
        server_default=text("'mirror'"),
        doc="Type: mirror, aggregate, proxy"
    )
    meta_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        name="metadata",  # Database column is "metadata" for consistency
        server_default=text("'{}'::jsonb"),
        doc="Additional metadata for the binding"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_twin_bind_device", "device_id"),
        Index("ix_twin_bind_entity", "twin_entity_id"),
        Index("ix_twin_bind_tenant_device", "tenant_id", "device_id"),
    )

    def __repr__(self) -> str:
        return f"<TwinBinding(id={self.id}, device={self.device_id}, entity={self.twin_entity_id})>"

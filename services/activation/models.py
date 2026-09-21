"""Activation layer domain models — SQLAlchemy 2.x Typed ORM Style."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from services.core.models.base import Base, SoftDeleteMixin


class TwinActivationLog(Base, SoftDeleteMixin):
    """Tracks the activation state of a PersistentTwinEntity in the runtime registry.

    This model provides persistent state for the activation lifecycle:
      CREATED (entity provisioned but not yet activated)
      BOUND   (device binding established)
      ACTIVE  (entity registered in TwinEntityRegistry)
      INACTIVE (entity removed from registry)
      ERROR   (activation failed)

    Key design:
      - One row per (tenant_id, twin_entity_id) — enforced by unique constraint
      - Does NOT modify PersistentTwinEntity or TwinBinding models
      - Activation state is separate from entity definition state
    """
    __tablename__ = "twin_activation_logs"

    __table_args__ = (
        Index("ix_activation_entity", "twin_entity_id"),
        Index("ix_activation_tenant_entity", "tenant_id", "twin_entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True,
    )
    twin_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created",
        server_default=text("'created'"),
    )
    # States: created | bound | active | inactive | error

    binding_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("twin_bindings.id", ondelete="SET NULL"),
        nullable=True,
    )
    # References existing TwinBinding (Task 9) when binding is established

    error_message: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
    )

    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class TwinCommand(Base, SoftDeleteMixin):
    """Command intent from Twin to physical device via Adapter contract.

    Tracks the command lifecycle without implementing adapter communication.
    The actual write to the device is handled by the Adapter layer (future).

    Lifecycle:
      CREATED  →  SENT  →  ACKNOWLEDGED  →  (terminal)
                                   ↘ FAILED  →  (terminal)
    """
    __tablename__ = "twin_commands"

    __table_args__ = (
        Index("ix_command_binding", "twin_binding_id"),
        Index("ix_command_device", "target_device_id"),
        Index("ix_command_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True,
    )
    twin_binding_id: Mapped[UUID] = mapped_column(
        ForeignKey("twin_bindings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    command_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
    )
    # Types: write | trigger | configure

    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        server_default=text("'{}'::jsonb"),
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="created",
        server_default=text("'created'"),
    )
    # States: created | sent | acknowledged | failed

    error_message: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

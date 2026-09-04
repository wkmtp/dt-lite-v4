"""TwinDefinition — Persistent type definition for twin entities.

Defines the schema and structure for a class of twin entities.
For example: "HVACUnit", "Room", "Pump" are definitions.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from services.twin.models.entity import PersistentTwinEntity

from services.core.models.base import Base, SoftDeleteMixin


class TwinDefinition(Base, SoftDeleteMixin):
    """Persistent type definition for twin entities.

    A TwinDefinition describes WHAT type of object a twin represents.
    It defines the schema, properties, and structure.

    Example:
        code="hvac_unit"
        name="HVAC Unit"
        schema = {
            "properties": [
                {"name": "temperature", "type": "FLOAT", "unit": "degC"},
                {"name": "status", "type": "STRING"}
            ]
        }

    NOT to be confused with:
        - TwinEntity (Instance): The actual running twin
        - Device (Task 5): The physical asset
    """
    __tablename__ = "twin_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
        doc="Machine-readable code (e.g., 'hvac_unit', 'room')"
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False,
        doc="Human-readable name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, default=None
    )
    schema: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        doc="JSON schema defining properties and structure"
    )
    meta_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        name="metadata",  # Database column is "metadata" for consistency
        doc="Additional metadata"
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

    # Relationships
    # Relationships - note: back_populates creates a circular reference, use backref instead
    entities: Mapped[list["PersistentTwinEntity"]] = relationship(  # type: ignore[name-defined]
        back_populates="definition",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_twin_def_tenant_code", "tenant_id", "code"),
    )

    def __repr__(self) -> str:
        return f"<TwinDefinition(id={self.id}, code={self.code!r}, name={self.name!r})>"

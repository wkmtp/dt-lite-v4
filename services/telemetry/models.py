"""Telemetry Model - Time-series data points table.

Historical telemetry data. No soft delete — time-series data is append-only.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from services.core.models.base import Base


class TelemetryPoint(Base):
    """Time-series telemetry data point.

    This table stores raw normalized telemetry values from protocol adapters.
    It is append-only: no updates, no deletes, no soft delete.

    Foreign Keys:
        tenant_id → tenants.id
        device_id → devices.id (ondelete=CASCADE)
        datapoint_id → data_points.id (ondelete=CASCADE)
    """
    __tablename__ = "telemetry_points"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    datapoint_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_points.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        doc="Device measurement timestamp (from adapter)",
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        doc="System receive timestamp (UTC)",
    )

    value: Mapped[object] = mapped_column(JSONB, nullable=False, doc="Serialized measurement value")
    data_type: Mapped[str] = mapped_column(String(32), nullable=False, doc="BOOLEAN/INTEGER/FLOAT/STRING/JSON")
    unit: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, doc="Physical unit (e.g., degC, percent)")
    quality: Mapped[str] = mapped_column(String(32), nullable=False, default="GOOD", server_default=text("'GOOD'"),
                                        doc="DataQuality: GOOD/BAD/UNCERTAIN/UNKNOWN")
    meta_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'"),
        name="metadata",  # Database column is "metadata" for consistency
        doc="Additional metadata from adapter",
    )

    __table_args__ = (
        # Composite index for time-range queries per tenant+device
        Index("ix_telemetry_tenant_device_time", "tenant_id", "device_id", "event_time"),
        # Index for datapoint lookups
        Index("ix_telemetry_datapoint_time", "datapoint_id", "event_time"),
        # Index for tenant time-range scans
        Index("ix_telemetry_tenant_time", "tenant_id", "event_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<TelemetryPoint(id={self.id}, tenant_id={self.tenant_id}, "
            f"device_id={self.device_id}, datapoint_id={self.datapoint_id}, "
            f"event_time={self.event_time}, value={self.value!r})>"
        )

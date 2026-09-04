"""Data Acquisition Domain Models - SQLAlchemy 2.x Typed ORM Style."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.core.models.base import Base, SoftDeleteMixin


class DataSource(Base, SoftDeleteMixin):
    """DataSource represents an external data source definition."""
    __tablename__ = "data_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512), default=None)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="inactive", server_default=text("'inactive'")
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_datasource_tenant_name"),
        Index("ix_datasource_tenant_status", "tenant_id", "status"),
    )

    connections: Mapped[list["Connection"]] = relationship(
        "Connection", back_populates="data_source", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="data_source", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active" and not self.is_deleted


class Connection(Base, SoftDeleteMixin):
    """Connection represents a specific connection instance to a DataSource."""
    __tablename__ = "connections"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    credentials_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    timeout: Mapped[int] = mapped_column(default=30)
    retry_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="disconnected")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_connection_tenant_name"),
        Index("ix_connection_datasource", "data_source_id"),
    )

    data_source: Mapped["DataSource"] = relationship("DataSource", back_populates="connections")
    devices: Mapped[list["Device"]] = relationship(
        "Device", back_populates="connection", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "connected" and not self.is_deleted


class Device(Base, SoftDeleteMixin):
    """Device represents a physical or logical device."""
    __tablename__ = "devices"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    data_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    connection_id: Mapped[UUID] = mapped_column(
        ForeignKey("connections.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="offline", server_default=text("'offline'")
    )
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_device_tenant_external"),
        Index("ix_device_datasource", "data_source_id"),
        Index("ix_device_connection", "connection_id"),
    )

    data_source: Mapped["DataSource"] = relationship("DataSource", back_populates="devices")
    connection: Mapped["Connection"] = relationship("Connection", back_populates="devices")
    data_points: Mapped[list["DataPoint"]] = relationship(
        "DataPoint", back_populates="device", cascade="all, delete-orphan"
    )
    bindings: Mapped[list["DeviceEntityBinding"]] = relationship(
        "DeviceEntityBinding", back_populates="device", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "online" and not self.is_deleted


class DataPoint(Base, SoftDeleteMixin):
    """DataPoint represents a readable/writable monitored data point."""
    __tablename__ = "data_points"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    access_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    sampling_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "device_id", "key", name="uq_datapoint_tenant_device_key"
        ),
        Index("ix_datapoint_external", "external_id"),
    )

    device: Mapped["Device"] = relationship("Device", back_populates="data_points")


class DeviceEntityBinding(Base, SoftDeleteMixin):
    """DeviceEntityBinding links a Device to a Core Entity (Digital Twin)."""
    __tablename__ = "device_entity_bindings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    binding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc), server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("device_id", "entity_id", name="uq_binding_device_entity"),
    )

    device: Mapped["Device"] = relationship("Device", back_populates="bindings")

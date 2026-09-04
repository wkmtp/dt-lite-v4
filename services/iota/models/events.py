"""Data Acquisition Domain Events."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DataSourceCreated:
    data_source_id: UUID
    tenant_id: UUID
    name: str
    dt: datetime


@dataclass(frozen=True)
class ConnectionCreated:
    connection_id: UUID
    tenant_id: UUID
    data_source_id: UUID
    dt: datetime


@dataclass(frozen=True)
class DeviceCreated:
    device_id: UUID
    tenant_id: UUID
    data_source_id: UUID | None
    dt: datetime


@dataclass(frozen=True)
class DataPointCreated:
    datapoint_id: UUID
    tenant_id: UUID
    device_id: UUID
    key: str
    dt: datetime


@dataclass(frozen=True)
class DeviceEntityBindingCreated:
    binding_id: UUID
    tenant_id: UUID
    device_id: UUID
    entity_id: UUID
    dt: datetime


@dataclass(frozen=True)
class TelemetryIngested:
    tenant_id: UUID
    device_id: UUID
    datapoint_id: UUID
    event_time: datetime
    ingested_at: datetime
    value: object
    data_type: str
    unit: str | None
    quality: str
    dt: datetime

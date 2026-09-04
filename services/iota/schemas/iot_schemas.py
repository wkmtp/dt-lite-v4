"""Data Acquisition Schemas - Pydantic DTOs."""
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    type: str = Field(..., min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)


class DataSourceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    type: str
    status: str
    config: dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ConnectionCreate(BaseModel):
    data_source_id: UUID
    name: str = Field(..., min_length=1, max_length=128)
    endpoint: str = Field(..., min_length=1, max_length=512)
    credentials_ref: str = Field(..., min_length=1, max_length=256)
    timeout: int = Field(default=30, ge=1)
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectionResponse(BaseModel):
    id: UUID
    data_source_id: UUID
    name: str
    endpoint: str = Field(..., description="Connection endpoint (redacted in responses)")
    credentials_ref: str
    timeout: int
    retry_policy: dict[str, Any]
    status: str
    config: dict[str, Any]
    created_at: str
    updated_at: str

    @field_validator('endpoint', mode='before')
    @classmethod
    def redact_endpoint(cls, v: Any) -> str:
        """Redact endpoint value in API responses for security."""
        if v and v != '<REDACTED>':
            return '<REDACTED>'
        return v or ''

    class Config:
        from_attributes = True


class DeviceCreate(BaseModel):
    data_source_id: Optional[UUID] = None
    connection_id: Optional[UUID] = None
    external_id: str = Field(..., min_length=1, max_length=256)
    name: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., min_length=1, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    data_source_id: Optional[UUID]
    connection_id: Optional[UUID]
    external_id: str
    name: str
    device_type: str
    status: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DataPointCreate(BaseModel):
    device_id: UUID
    external_id: str = Field(..., min_length=1, max_length=256)
    key: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    data_type: str = Field(..., pattern="^(BOOLEAN|INTEGER|FLOAT|STRING|JSON)$")
    unit: Optional[str] = Field(None, max_length=32)
    access_mode: str = Field(..., pattern="^(READ|WRITE|READ_WRITE)$")
    sampling_mode: str = Field(..., pattern="^(POLL|SUBSCRIBE|ON_CHANGE|MANUAL)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataPointResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    device_id: UUID
    external_id: str
    key: str
    name: str
    data_type: str
    unit: Optional[str]
    access_mode: str
    sampling_mode: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DeviceEntityBindingCreate(BaseModel):
    device_id: UUID
    entity_id: UUID
    binding_type: str = Field(..., min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceEntityBindingResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    device_id: UUID
    entity_id: UUID
    binding_type: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TelemetryIngestRequest(BaseModel):
    device_id: UUID
    datapoint_id: UUID
    event_time: str  # ISO format datetime
    value: Any
    data_type: str = Field(..., pattern="^(BOOLEAN|INTEGER|FLOAT|STRING|JSON)$")
    unit: Optional[str] = Field(None, max_length=32)
    quality: str = Field(default="GOOD", pattern="^(GOOD|BAD|UNCERTAIN|UNKNOWN)$")
    metadata: dict[str, Any] = Field(default_factory=dict)

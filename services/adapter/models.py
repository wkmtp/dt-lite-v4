"""Adapter models — Configuration and mapping schemas."""
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AdapterConfig(BaseModel):
    """Configuration for an adapter instance."""
    adapter_type: str = Field(..., description="Protocol type: bacnet, modbus, mqtt, opcua")
    endpoint: str = Field(..., description="Device endpoint (IP:port, URL, etc.)")
    credentials_ref: str = Field(..., description="Reference to credentials in SecretProvider")
    config: dict[str, Any] = Field(default_factory=dict, description="Protocol-specific configuration")
    description: Optional[str] = Field(None, max_length=512)


class DeviceMapping(BaseModel):
    """Mapping between a DataPoint and a protocol-specific address."""
    datapoint_key: str = Field(..., description="DataPoint.key from iota")
    protocol_address: str = Field(..., description="Protocol-specific address")
    protocol_config: dict[str, Any] = Field(default_factory=dict)
    direction: str = Field(default="read", pattern="^(read|write|read_write)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityMatch(BaseModel):
    """Result of matching a CapabilityDefinition to an Adapter type."""
    adapter_type: str = Field(..., description="Adapter type that supports this capability")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence score")
    mapping_template: Optional[dict[str, Any]] = Field(None, description="Suggested mapping template")
    required_capabilities: list[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None)


class AdapterRegistryEntry(BaseModel):
    """Entry in the adapter registry (in-memory)."""
    adapter_id: UUID
    tenant_id: UUID
    adapter_type: str
    endpoint: str
    connected: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    health_status: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)

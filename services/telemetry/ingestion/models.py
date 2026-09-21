"""Telemetry Point — Standard payload for all adapters."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Quality(str, Enum):
    """Data quality indicator per ISA-95 / OPC-UA standards."""
    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"
    UNKNOWN = "UNKNOWN"


class TelemetryPoint(BaseModel):
    """Standard telemetry point produced by all protocol adapters.

    This is the contract between Adapter Layer and Telemetry Pipeline.
    All 4 protocols (BACnet, Modbus, MQTT, OPC-UA) produce this payload.
    """
    asset_id: UUID = Field(..., description="Device/Asset UUID")
    property_code: str = Field(..., description="DataPoint.key (e.g., 'temperature')")
    timestamp: datetime = Field(..., description="Device measurement timestamp (UTC)")
    value: Any = Field(..., description="Measurement value")
    data_type: str = Field("FLOAT", description="BOOLEAN/INTEGER/FLOAT/STRING/JSON")
    unit: Optional[str] = Field(None, description="Physical unit (e.g., 'degC', 'kPa')")
    quality: Quality = Field(Quality.GOOD, description="Data quality: GOOD/UNCERTAIN/BAD/UNKNOWN")
    source_adapter: str = Field(..., description="Adapter type: bacnet/modbus/mqtt/opcua")
    metadata: dict = Field(default_factory=dict, description="Extra metadata from adapter")

    def validate(self) -> list[str]:
        """Validate required fields and return list of errors (empty = valid)."""
        errors = []
        if not self.asset_id:
            errors.append("asset_id required")
        if not self.property_code:
            errors.append("property_code required")
        if not self.timestamp:
            errors.append("timestamp required")
        if self.data_type not in {"BOOLEAN", "INTEGER", "FLOAT", "STRING", "JSON"}:
            errors.append(f"invalid data_type: {self.data_type}")
        if self.quality not in {q.value for q in Quality}:
            errors.append(f"invalid quality: {self.quality}")
        return errors

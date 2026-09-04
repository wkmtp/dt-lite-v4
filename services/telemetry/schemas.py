"""Telemetry Layer Schemas - Pydantic DTOs for API I/O."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TelemetryPointCreate(BaseModel):
    """Request schema for ingesting a single telemetry point.

    Note: tenant_id is NOT accepted from client — it comes from TenantContext.
    """
    device_id: UUID = Field(..., description="Device that generated this measurement")
    datapoint_id: UUID = Field(..., description="DataPoint being measured")
    event_time: datetime = Field(..., description="Device measurement timestamp (UTC)")
    ingested_at: datetime = Field(..., description="System receive timestamp (UTC)")
    value: Any = Field(..., description="Measurement value")
    data_type: str = Field(..., description="BOOLEAN/INTEGER/FLOAT/STRING/JSON")
    unit: Optional[str] = Field(None, description="Physical unit of measurement")
    quality: str = Field(default="GOOD", description="Data quality indicator")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str) -> str:
        valid = {"BOOLEAN", "INTEGER", "FLOAT", "STRING", "JSON"}
        if v.upper() not in valid:
            raise ValueError(f"data_type must be one of {valid}, got '{v}'")
        return v.upper()

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: str) -> str:
        valid = {"GOOD", "BAD", "UNCERTAIN", "UNKNOWN"}
        if v.upper() not in valid:
            raise ValueError(f"quality must be one of {valid}, got '{v}'")
        return v.upper()

    @field_validator("event_time", "ingested_at")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")
        return v


class TelemetryPointResponse(BaseModel):
    """Response schema for a single telemetry point."""
    id: UUID
    device_id: UUID
    datapoint_id: UUID
    event_time: datetime
    ingested_at: datetime
    value: Any
    data_type: str
    unit: Optional[str]
    quality: str
    metadata: dict[str, Any]

    model_config = {"from_attributes": True}


class TelemetryBatchCreate(BaseModel):
    """Request schema for batch ingestion."""
    points: list[TelemetryPointCreate] = Field(
        ..., min_length=1, max_length=1000,
        description="List of telemetry points to ingest (max 1000)"
    )


class TelemetryQueryResponse(BaseModel):
    """Response wrapper for query results."""
    total: int
    device_id: Optional[UUID] = None
    datapoint_id: Optional[UUID] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    points: list[TelemetryPointResponse] = Field(default_factory=list)

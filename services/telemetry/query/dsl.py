"""Telemetry Query DSL — Unified query interface for all time-series queries."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Aggregate(str, Enum):
    """Aggregation level for queries."""
    RAW = "raw"
    MINUTE = "1m"
    HOUR = "1h"
    DAY = "1d"


class TimeRange(BaseModel):
    """Time range for queries."""
    start: datetime
    end: datetime

    def validate(self) -> list[str]:
        errors = []
        if self.start > self.end:
            errors.append("start must be before end")
        if (self.end - self.start).total_seconds() > 365 * 86400:
            errors.append("time range cannot exceed 1 year")
        return errors


class TelemetryQuery(BaseModel):
    """Unified query DSL for telemetry data.

    Supports:
      - Time-range queries
      - Asset/property filtering
      - Aggregation (raw, 1m, 1h, 1d)
      - Quality filtering
      - Pagination
    """
    asset_ids: list[UUID] = Field(default_factory=list, description="Filter by asset IDs")
    property_codes: list[str] = Field(default_factory=list, description="Filter by property codes")
    timerange: TimeRange = Field(..., description="Time range for query")
    aggregate: Aggregate = Field(Aggregate.RAW, description="Aggregation level")
    limit: int = Field(10000, ge=1, le=100000, description="Max results")
    offset: int = Field(0, ge=0, description="Pagination offset")
    quality_filter: Optional[str] = Field(None, description="Filter by quality: GOOD, UNCERTAIN, BAD")

    def validate(self) -> list[str]:
        errors = []
        errors.extend(self.timerange.validate())
        if self.aggregate == Aggregate.RAW and self.limit > 10000:
            errors.append("RAW queries limited to 10000 points")
        if self.quality_filter and self.quality_filter not in {"GOOD", "UNCERTAIN", "BAD"}:
            errors.append(f"Invalid quality_filter: {self.quality_filter}")
        return errors

    def get_target_table(self) -> str:
        """Get the target table name based on aggregation level."""
        tables = {
            Aggregate.RAW: "telemetry_points",
            Aggregate.MINUTE: "telemetry_agg_1m",
            Aggregate.HOUR: "telemetry_agg_1h",
            Aggregate.DAY: "telemetry_agg_1d",
        }
        return tables[self.aggregate]

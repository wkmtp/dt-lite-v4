"""Telemetry Query API — FastAPI routes for time-series queries."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth.dependencies import require_permission
from services.telemetry.query.dsl import Aggregate, TelemetryQuery, TimeRange

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.get("/query", dependencies=[Depends(require_permission("telemetry:read"))])
async def query_telemetry(
    asset_ids: Optional[str] = Query(None, description="Comma-separated asset IDs"),
    property_codes: Optional[str] = Query(None, description="Comma-separated property codes"),
    start_time: datetime = Query(..., description="Start time (ISO 8601)"),
    end_time: datetime = Query(..., description="End time (ISO 8601)"),
    aggregate: str = Query("raw", description="Aggregation level: raw, 1m, 1h, 1d"),
    limit: int = Query(1000, ge=1, le=100000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    quality_filter: Optional[str] = Query(None, description="Filter by quality: GOOD, UNCERTAIN, BAD"),
):
    """Query telemetry data with unified DSL."""
    # Parse inputs
    assets = [UUID(aid) for aid in asset_ids.split(",")] if asset_ids else []
    props = property_codes.split(",") if property_codes else []
    agg = Aggregate(aggregate)
    timerange = TimeRange(start=start_time, end=end_time)

    query = TelemetryQuery(
        asset_ids=assets,
        property_codes=props,
        timerange=timerange,
        aggregate=agg,
        limit=limit,
        offset=offset,
        quality_filter=quality_filter,
    )

    errors = query.validate()
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Execute query (stub for now)
    return {
        "data": [],
        "total": 0,
        "aggregate": agg.value,
        "timerange": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        },
    }


@router.get("/query/health", dependencies=[Depends(require_permission("telemetry:read"))])
async def health_check():
    """Health check for telemetry query service."""
    return {"status": "ok", "service": "telemetry-query"}

"""Quality Report API — Endpoints for quality scoring and reporting."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.telemetry.quality.engine import QualityEngine, QualityScore
from services.telemetry.quality.markers import QualityMarker
from services.telemetry.quality.rules import QualityRuleEngine

router = APIRouter(prefix="/api/v1/telemetry/quality", tags=["Telemetry Quality"])


class QualityScoreResponse(BaseModel):
    asset_id: UUID
    property_code: str
    score: QualityScore
    timestamp: datetime = Field(default_factory=lambda: datetime.now())


class QualityReportResponse(BaseModel):
    asset_id: UUID
    property_code: str
    time_range_start: datetime
    time_range_end: datetime
    avg_score: float
    good_count: int
    uncertain_count: int
    bad_count: int
    total_points: int
    top_triggered_rules: list[str]


class HealthResponse(BaseModel):
    engine_status: str
    total_scores: int
    bad_ratio: float


# Module-level instances (will be injected in production)
_engine = QualityEngine()
_markers = QualityMarker(QualityRuleEngine())


@router.post("/score", response_model=QualityScoreResponse)
async def score_point(
    asset_id: UUID,
    property_code: str,
    value: float,
    timestamp: datetime,
    expected_min: Optional[float] = None,
    expected_max: Optional[float] = None,
    historical_values: Optional[list[float]] = None,
):
    """Score a single telemetry point."""
    score = _engine.score(
        property_code=property_code,
        value=value,
        timestamp=timestamp,
        expected_min=expected_min,
        expected_max=expected_max,
        historical_values=historical_values,
    )
    return QualityScoreResponse(asset_id=asset_id, property_code=property_code, score=score)


@router.get("/report", response_model=QualityReportResponse)
async def get_quality_report(
    asset_id: UUID,
    property_code: str,
    start_time: datetime = Query(..., description="Start of time range"),
    end_time: datetime = Query(..., description="End of time range"),
):
    """Get quality report for a time range."""
    # In production, query the telemetry repository for historical data
    return QualityReportResponse(
        asset_id=asset_id,
        property_code=property_code,
        time_range_start=start_time,
        time_range_end=end_time,
        avg_score=95.0,
        good_count=1000,
        uncertain_count=10,
        bad_count=2,
        total_points=1012,
        top_triggered_rules=["temp_range"],
    )


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Get quality engine health status."""
    bad_markers = _markers.get_bad_markers()
    total = len(_markers._markers)
    return HealthResponse(
        engine_status="healthy" if total > 0 else "idle",
        total_scores=total,
        bad_ratio=len(bad_markers) / total if total > 0 else 0.0,
    )

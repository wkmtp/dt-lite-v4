"""Point Service — Semantic definition, UCUM/QUDT units, aggregation."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# UCUM-compatible unit validation pattern
UCUM_PATTERN = re.compile(
    r"^[a-zA-Z]+(?:[a-zA-Z0-9/°⋅-]+)?$",
    re.UNICODE,
)
# Special case: % is valid UCUM
VALID_UCUM_UNITS = {
    "kW", "degC", "m3/h", "Pa", "A", "V", "Hz", "s", "%", "l/s", "m3",
    "W", "C", "K", "bar", "kPa", "MPa", "mmH2O", "mmHg",
    "rpm", "Ω", "m", "mm", "cm", "km", "m2", "m3",
    "l", "ml", "kg", "g", "t", "ton",
    "dB", "lx", "lux", "cd",
    "bit", "Byte", "kB", "MB", "GB",
}

# Forbidden protocol fields in Point
FORBIDDEN_POINT_FIELDS = {
    "protocol", "address", "register", "slave_id", "function_code",
    "topic", "url", "endpoint", "device_id", "object_id",
}

VALID_AGGREGATIONS = {"latest", "min", "max", "avg", "sum", "count", "delta", "rate"}


@dataclass
class Point:
    """Point entity matching Universal Contract v1.0 — ZERO protocol fields."""
    id: str
    code: str
    semantic_type: str
    unit: str
    aggregation: list[str]
    tags: list[str]
    asset_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def quality(self) -> str:
        return self.metadata.get("quality", "GOOD")

    def set_quality(self, quality: str) -> None:
        if quality not in ("GOOD", "UNCERTAIN", "BAD"):
            raise ValueError(f"Invalid quality: {quality}")
        self.metadata["quality"] = quality

    def validate(self) -> list[str]:
        """Validate Point constraints. Returns list of errors (empty = valid)."""
        errors = []
        if self.unit not in VALID_UCUM_UNITS and not UCUM_PATTERN.match(self.unit):
            errors.append(f"Invalid unit format: {self.unit}")
        if not VALID_AGGREGATIONS.issuperset(self.aggregation):
            invalid = set(self.aggregation) - VALID_AGGREGATIONS
            errors.append(f"Invalid aggregation functions: {invalid}")
        if not self.semantic_type:
            errors.append("semantic_type is required")
        if not self.code:
            errors.append("code is required")
        return errors


class PointService:
    """
    Point Service: semantic definition, validation, aggregation config.
    NO protocol logic — protocol lives in MappingProfile.
    """

    def __init__(self) -> None:
        self._points: dict[str, Point] = {}

    def create(self, data: dict[str, Any], tenant_id: str) -> Point:
        """Create a Point with semantic validation."""
        for key in ["id", "code", "semantic_type", "unit", "aggregation", "tags", "asset_id"]:
            if key not in data:
                raise ValueError(f"Point missing required field: {key}")

        # SL-04: Reject protocol fields in Point
        forbidden = FORBIDDEN_POINT_FIELDS & set(data.keys())
        if forbidden:
            raise ValueError(f"Protocol fields not allowed in Point: {forbidden}")

        point = Point(
            id=data["id"],
            code=data["code"],
            semantic_type=data["semantic_type"],
            unit=data["unit"],
            aggregation=data["aggregation"],
            tags=data["tags"],
            asset_id=data["asset_id"],
            metadata={
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "quality": "GOOD",
                **data.get("metadata", {}),
            },
        )
        errors = point.validate()
        if errors:
            raise ValueError(f"Point validation failed: {errors}")

        self._points[point.id] = point
        logger.info("Created point: %s (%s)", point.id, point.code)
        return point

    def get(self, point_id: str) -> Optional[Point]:
        """Get point by ID."""
        return self._points.get(point_id)

    def list_by_asset(self, asset_id: str, tenant_id: str) -> list[Point]:
        """List all points for an asset."""
        return [
            p for p in self._points.values()
            if p.asset_id == asset_id and p.metadata.get("tenant_id") == tenant_id
        ]

    def all(self, tenant_id: str) -> list[Point]:
        """List all points for a tenant."""
        return [
            p for p in self._points.values()
            if p.metadata.get("tenant_id") == tenant_id
        ]

    def update(self, point_id: str, updates: dict[str, Any]) -> Optional[Point]:
        """Update point metadata."""
        point = self._points.get(point_id)
        if not point:
            return None
        if "metadata" in updates:
            point.metadata.update(updates["metadata"])
        return point

    def delete(self, point_id: str) -> bool:
        """Remove point."""
        if point_id not in self._points:
            return False
        del self._points[point_id]
        logger.info("Deleted point: %s", point_id)
        return True

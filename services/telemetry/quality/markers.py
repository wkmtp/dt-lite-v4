"""Quality Markers — Real-time quality marking for telemetry points."""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class QualityMarker:
    """Marks telemetry points with quality status based on rules."""

    def __init__(self, rule_engine):
        self._engine = rule_engine
        self._markers: dict[str, dict] = {}  # point_id -> marker

    def mark(self, point_id: str, property_code: str, value: float,
             metadata: Optional[dict] = None) -> dict:
        """Mark a telemetry point with quality status."""
        triggered = self._engine.evaluate(property_code, value, metadata or {})

        if triggered:
            quality = "BAD"
            reason = f"rules_triggered: {','.join(triggered)}"
        else:
            quality = "GOOD"
            reason = ""

        marker = {
            "point_id": point_id,
            "property_code": property_code,
            "quality": quality,
            "rules_triggered": triggered,
            "reason": reason,
            "marked_at": datetime.now(timezone.utc),
        }
        self._markers[point_id] = marker
        return marker

    def get_marker(self, point_id: str) -> Optional[dict]:
        """Get quality marker for a point."""
        return self._markers.get(point_id)

    def get_bad_markers(self, limit: int = 100) -> list[dict]:
        """Get all BAD quality markers."""
        return [m for m in self._markers.values() if m["quality"] == "BAD"][:limit]

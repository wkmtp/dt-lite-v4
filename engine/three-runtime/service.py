"""ThreeRuntime — Asset state → 3D visual mapping."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class VisualState:
    """Visual representation of an Asset's current state in 3D."""
    asset_id: str
    color: tuple[float, float, float]  # RGB [0,1]
    opacity: float  # 0.0-1.0
    animation: dict[str, Any] = field(default_factory=dict)
    tooltip: dict[str, Any] = field(default_factory=dict)
    updated_at: float = 0.0  # timestamp in seconds


class ThreeRuntime:
    """Three.js runtime integration layer.

    Converts Asset state (telemetry + lifecycle) into 3D visual properties.
    Does NOT manage scenes or bindings — those are handled by SceneService
    and ModelBindingService.
    """

    # Color thresholds: (min, max, r, g, b)
    COLOR_THRESHOLDS = [
        (0.0,  0.3, 0.0, 0.8, 0.0),   # green: normal
        (0.3,  0.7, 1.0, 0.8, 0.0),   # yellow: warning
        (0.7,  1.0, 1.0, 0.0, 0.0),   # red: alarm
    ]

    # Lifecycle opacity
    LIFECYCLE_OPACITY = {
        "active":       1.0,
        "provisioned":  0.6,
        "decommissioned": 0.3,
        "retired":      0.1,
    }

    def __init__(self) -> None:
        self._visual_states: dict[str, VisualState] = {}
        self._update_log: list[dict[str, Any]] = []

    def update(self, asset_id: str, telemetry: dict[str, Any], lifecycle_status: str = "active") -> VisualState:
        """Update 3D visual state for an asset.

        Args:
            asset_id: Asset identifier.
            telemetry: {point_code: value} mapping from telemetry.
            lifecycle_status: One of active/provisioned/decommissioned/retired.

        Returns:
            The updated VisualState.
        """
        start_time = time.monotonic()

        # Compute color from telemetry
        color = self._compute_color(telemetry)

        # Compute opacity from lifecycle
        opacity = self.LIFECYCLE_OPACITY.get(lifecycle_status, 1.0)

        # Compute animation from alarm/capability state
        animation = self._compute_animation(telemetry, lifecycle_status)

        # Compute tooltip
        tooltip = self._compute_tooltip(asset_id, telemetry, lifecycle_status)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        state = VisualState(
            asset_id=asset_id,
            color=color,
            opacity=opacity,
            animation=animation,
            tooltip=tooltip,
            updated_at=time.time(),
        )
        self._visual_states[asset_id] = state

        self._update_log.append({
            "asset_id": asset_id,
            "elapsed_ms": round(elapsed_ms, 3),
            "color": color,
            "opacity": opacity,
        })

        logger.debug(
            "Updated 3D visual for %s: color=%s opacity=%.2f latency=%.1fms",
            asset_id, color, opacity, elapsed_ms,
        )
        return state

    def get(self, asset_id: str) -> Optional[VisualState]:
        """Get current visual state for an asset."""
        return self._visual_states.get(asset_id)

    def list_all(self) -> list[VisualState]:
        """List all tracked visual states."""
        return list(self._visual_states.values())

    def remove(self, asset_id: str) -> bool:
        """Remove visual state for an asset."""
        if asset_id in self._visual_states:
            del self._visual_states[asset_id]
            return True
        return False

    def last_latency_ms(self, asset_id: str) -> Optional[float]:
        """Get last update latency in ms for an asset."""
        for entry in reversed(self._update_log):
            if entry["asset_id"] == asset_id:
                return entry["elapsed_ms"]
        return None

    # ── Internal helpers ────────────────────────────────────────────

    def _compute_color(self, telemetry: dict[str, Any]) -> tuple[float, float, float]:
        """Compute RGB color from telemetry values.

        Uses the maximum normalized value across all telemetry points
        to determine color position on the gradient.
        """
        if not telemetry:
            return (0.0, 0.8, 0.0)  # default green

        max_value = max(
            abs(v) for v in telemetry.values()
            if isinstance(v, (int, float))
        )
        # Normalize to [0, 1] — assume max possible value is 1.0 for simplicity
        normalized = min(max_value, 1.0)

        for min_v, max_v, r, g, b in self.COLOR_THRESHOLDS:
            if min_v <= normalized <= max_v:
                # Interpolate within the band
                ratio = (normalized - min_v) / (max_v - min_v) if max_v > min_v else 0
                return (
                    r + (0.0 - r) * ratio if r > 0 else r,
                    g + (0.0 - g) * ratio if g > 0 else g,
                    b + (0.0 - b) * ratio if b > 0 else b,
                )

        return (1.0, 0.0, 0.0)  # red as fallback

    def _compute_animation(self, telemetry: dict[str, Any], lifecycle: str) -> dict[str, Any]:
        """Compute animation properties from telemetry."""
        if lifecycle in ("decommissioned", "retired"):
            return {"type": "none"}

        # Check for alarm conditions (any value > 0.7 = warning)
        has_alarm = any(
            isinstance(v, (int, float)) and v > 0.7
            for v in telemetry.values()
        )
        if has_alarm:
            return {"type": "pulse", "speed": 2.0}

        # Normal rotation based on first numeric value
        for v in telemetry.values():
            if isinstance(v, (int, float)) and v > 0:
                return {"type": "rotate", "speed": v * 0.5}

        return {"type": "none"}

    def _compute_tooltip(self, asset_id: str, telemetry: dict[str, Any], lifecycle: str) -> dict[str, Any]:
        """Compute tooltip content."""
        return {
            "asset_id": asset_id,
            "lifecycle": lifecycle,
            "telemetry": {k: v for k, v in telemetry.items() if isinstance(v, (int, float))},
        }

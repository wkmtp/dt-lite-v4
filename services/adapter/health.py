"""Adapter Health Monitoring.

Provides health status reporting without auto-recovery or scheduling.
Health checks are triggered on-demand or via explicit calls.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class AdapterHealth:
    """Health status for a single adapter instance."""

    adapter_name: str
    status: str  # "HEALTHY", "UNHEALTHY", "UNKNOWN", "ERROR"
    last_check_time: datetime
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize health report."""
        return {
            "adapter_name": self.adapter_name,
            "status": self.status,
            "last_check_time": self.last_check_time.isoformat(),
            "message": self.message,
            "metadata": self.metadata,
        }


class HealthMonitor:
    """Monitors adapter health via explicit check calls.

    Does NOT implement:
    - Automatic periodic checking
    - Auto-recovery
    - Alerting
    - Scheduling

    Health is determined by calling adapter.health() and mapping result.
    """

    def __init__(self) -> None:
        self._health_cache: dict[str, AdapterHealth] = {}

    async def check(self, adapter_name: str, adapter: Any) -> AdapterHealth:
        """Perform health check on adapter.

        Args:
            adapter_name: Name of the adapter to check.
            adapter: ProtocolAdapter instance.

        Returns:
            AdapterHealth with current status.
        """
        check_time = datetime.now(timezone.utc)

        try:
            is_healthy = await adapter.health()
            if is_healthy:
                status = "HEALTHY"
                message = "Adapter is operational"
            else:
                status = "UNHEALTHY"
                message = "Adapter health check returned False"

            health = AdapterHealth(
                adapter_name=adapter_name,
                status=status,
                last_check_time=check_time,
                message=message,
            )

        except Exception as e:
            status = "ERROR"
            message = f"Health check failed: {type(e).__name__}"
            health = AdapterHealth(
                adapter_name=adapter_name,
                status=status,
                last_check_time=check_time,
                message=message,
                metadata={"error_type": type(e).__name__},
            )

        self._health_cache[adapter_name] = health
        return health

    def get_health(self, adapter_name: str) -> Optional[AdapterHealth]:
        """Get cached health status for adapter."""
        return self._health_cache.get(adapter_name)

    def get_all_health(self) -> dict[str, AdapterHealth]:
        """Get all cached health statuses."""
        return dict(self._health_cache)

    def clear_cache(self) -> None:
        """Clear health cache."""
        self._health_cache.clear()

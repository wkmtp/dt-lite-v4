"""Adapter Runtime Models (In-Memory).

These models track runtime state only. They do NOT persist to database.
Persistence is handled by IOTA layer services via NormalizedTelemetry.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class AdapterInstance:
    """Runtime instance tracking for a registered adapter.

    This model holds:
    - Logical name (key in registry)
    - Protocol adapter reference
    - Lifecycle state
    - Health status
    - Connection metadata (endpoint redacted)

    Security: No credentials stored here. Only endpoint summary.
    """

    name: str
    adapter: Any  # ProtocolAdapter instance
    state: str = "CREATED"
    last_health_check: Optional[datetime] = None
    health_status: str = "UNKNOWN"
    health_message: str = ""
    health_metadata: dict[str, Any] = field(default_factory=dict)
    connected_endpoint: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_state(self, new_state: str) -> None:
        """Update state and timestamp."""
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)

    def record_health(self, status: str, message: str, metadata: Optional[dict] = None) -> None:
        """Record health check result."""
        self.health_status = status
        self.health_message = message
        self.health_metadata = metadata or {}
        self.last_health_check = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def record_error(self, error_msg: str) -> None:
        """Record an error occurrence."""
        self.error_count += 1
        self.last_error = error_msg
        self.updated_at = datetime.now(timezone.utc)

    def to_health_dict(self) -> dict[str, Any]:
        """Serialize to health report dict."""
        return {
            "adapter_name": self.name,
            "state": self.state,
            "health_status": self.health_status,
            "last_check_time": self.last_health_check.isoformat() if self.last_health_check else None,
            "message": self.health_message,
            "metadata": self.health_metadata,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "connected_endpoint_masked": self._mask_endpoint(self.connected_endpoint),
        }

    @staticmethod
    def _mask_endpoint(endpoint: Optional[str]) -> Optional[str]:
        """Mask sensitive parts of endpoint for safe logging."""
        if not endpoint:
            return None
        # Mask anything after :// as potentially sensitive
        if "://" in endpoint:
            scheme, rest = endpoint.split("://", 1)
            # Keep scheme and host, mask the rest
            parts = rest.split("@", 1)
            if len(parts) == 2:
                return f"{scheme}://{parts[0]}@***"
            return f"{scheme}://[HOST_REDACTED]"
        return "[ENDPOINT_REDACTED]"

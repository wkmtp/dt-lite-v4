"""Adapter health monitoring and metrics."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from services.iota.contracts import ProtocolAdapter

logger = logging.getLogger(__name__)


class AdapterHealthStatus:
    """Health status for an adapter instance."""

    def __init__(
        self,
        adapter_id: UUID,
        tenant_id: UUID,
        adapter_type: str,
        endpoint: str,
        connected: bool,
        circuit_state: str,
        last_health_check: Optional[datetime] = None,
        error_message: Optional[str] = None,
        metrics: Optional[dict[str, Any]] = None,
    ):
        self.adapter_id = adapter_id
        self.tenant_id = tenant_id
        self.adapter_type = adapter_type
        self.endpoint = endpoint
        self.connected = connected
        self.circuit_state = circuit_state
        self.last_health_check = last_health_check
        self.error_message = error_message
        self.metrics = metrics or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": str(self.adapter_id),
            "tenant_id": str(self.tenant_id),
            "adapter_type": self.adapter_type,
            "endpoint": self.endpoint,
            "connected": self.connected,
            "circuit_state": self.circuit_state,
            "last_health_check": (
                self.last_health_check.isoformat()
                if self.last_health_check else None
            ),
            "error_message": self.error_message,
            "metrics": self.metrics,
        }


class AdapterHealthChecker:
    """Performs health checks on adapters and tracks metrics."""

    def __init__(self):
        self._statuses: dict[tuple[UUID, UUID], AdapterHealthStatus] = {}

    async def check(
        self,
        adapter_id: UUID,
        tenant_id: UUID,
        adapter: ProtocolAdapter,
        adapter_type: str,
        endpoint: str,
        circuit_state: str,
    ) -> AdapterHealthStatus:
        try:
            healthy = await adapter.health()
            now = datetime.now(timezone.utc)
            status = AdapterHealthStatus(
                adapter_id=adapter_id,
                tenant_id=tenant_id,
                adapter_type=adapter_type,
                endpoint=endpoint,
                connected=healthy,
                circuit_state=circuit_state,
                last_health_check=now,
                error_message=None if healthy else "Health check returned False",
                metrics={"last_check_at": now.isoformat()},
            )
        except Exception as e:
            now = datetime.now(timezone.utc)
            status = AdapterHealthStatus(
                adapter_id=adapter_id,
                tenant_id=tenant_id,
                adapter_type=adapter_type,
                endpoint=endpoint,
                connected=False,
                circuit_state=circuit_state,
                last_health_check=now,
                error_message=str(e),
                metrics={"last_check_at": now.isoformat(), "error": str(e)},
            )

        key = (adapter_id, tenant_id)
        self._statuses[key] = status
        return status

    def get_status(self, adapter_id: UUID, tenant_id: UUID) -> Optional[AdapterHealthStatus]:
        return self._statuses.get((adapter_id, tenant_id))

    def list_statuses(self, tenant_id: UUID) -> list[AdapterHealthStatus]:
        return [s for (aid, tid), s in self._statuses.items() if tid == tenant_id]

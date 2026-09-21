"""Edge Adapter Pack — Base adapter with offline caching."""
from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AdapterStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class EdgeTelemetryPoint:
    """Telemetry point with edge-specific metadata."""
    asset_id: str
    property_code: str
    timestamp: datetime
    value: float
    data_type: str = "FLOAT"
    unit: str = ""
    quality: str = "GOOD"
    source_adapter: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    hlc_physical_ts: int = 0
    hlc_logical_counter: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "property_code": self.property_code,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "data_type": self.data_type,
            "unit": self.unit,
            "quality": self.quality,
            "source_adapter": self.source_adapter,
            "metadata": self.metadata,
            "hlc": {
                "physical_ts": self.hlc_physical_ts,
                "logical_counter": self.hlc_logical_counter,
            },
        }


class EdgeAdapter(ABC):
    """
    Base class for edge adapters.

    Provides:
    - Connection lifecycle management
    - Offline data buffering
    - Retry with exponential backoff
    - Quality marking
    """

    def __init__(
        self,
        adapter_id: str,
        adapter_type: str,
        endpoint: str,
        tenant_id: str,
        buffer_size: int = 10000,
    ) -> None:
        self.adapter_id = adapter_id
        self.adapter_type = adapter_type
        self.endpoint = endpoint
        self.tenant_id = tenant_id
        self.buffer_size = buffer_size
        self.status = AdapterStatus.DISCONNECTED
        self._buffer: list[EdgeTelemetryPoint] = []
        self._lock = asyncio.Lock()
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to device/protocol endpoint."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from device/protocol endpoint."""
        ...

    @abstractmethod
    async def read(self, external_ids: list[str]) -> list[EdgeTelemetryPoint]:
        """Read telemetry data from devices."""
        ...

    @abstractmethod
    async def write(self, external_id: str, value: float) -> bool:
        """Write control value to device."""
        ...

    @abstractmethod
    async def subscribe(self, external_ids: list[str]) -> str:
        """Subscribe to device updates. Returns subscription_id."""
        ...

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from device updates."""
        ...

    async def buffer_point(self, point: EdgeTelemetryPoint) -> None:
        """Add point to offline buffer."""
        async with self._lock:
            if len(self._buffer) >= self.buffer_size:
                # Drop oldest
                self._buffer.pop(0)
            self._buffer.append(point)

    async def flush_buffer(self) -> list[EdgeTelemetryPoint]:
        """Flush buffered points for sync."""
        async with self._lock:
            if not self._buffer:
                return []
            points = self._buffer[:]
            self._buffer.clear()
            return points

    async def get_buffer_size(self) -> int:
        """Get current buffer size."""
        async with self._lock:
            return len(self._buffer)

    def get_capabilities(self) -> dict[str, Any]:
        """Get adapter capabilities."""
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "endpoint": self.endpoint,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "buffer_size": self.buffer_size,
            "supported_operations": ["read", "write", "subscribe"],
        }


# ---------------------------------------------------------------------------
# Adapter Registry
# ---------------------------------------------------------------------------

class EdgeAdapterRegistry:
    """Registry for edge adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, EdgeAdapter] = {}

    def register(self, adapter: EdgeAdapter) -> None:
        """Register an adapter."""
        self._adapters[adapter.adapter_id] = adapter
        logger.info("Registered adapter: %s (%s)", adapter.adapter_id, adapter.adapter_type)

    def get(self, adapter_id: str) -> Optional[EdgeAdapter]:
        """Get adapter by ID."""
        return self._adapters.get(adapter_id)

    def list_adapters(self) -> list[dict[str, Any]]:
        """List all registered adapters."""
        return [a.get_capabilities() for a in self._adapters.values()]

    async def connect_all(self) -> dict[str, bool]:
        """Connect all adapters."""
        results = {}
        for adapter_id, adapter in self._adapters.items():
            try:
                ok = await adapter.connect()
                results[adapter_id] = ok
            except Exception as exc:
                logger.error("Failed to connect adapter %s: %s", adapter_id, exc)
                results[adapter_id] = False
        return results

    async def disconnect_all(self) -> None:
        """Disconnect all adapters."""
        for adapter in self._adapters.values():
            try:
                await adapter.disconnect()
            except Exception as exc:
                logger.error("Failed to disconnect adapter: %s", exc)


# Schemas
class RegisterAdapterRequest(BaseModel):
    adapter_id: str
    adapter_type: str
    endpoint: str
    config: dict[str, Any] = Field(default_factory=dict)


class RegisterAdapterResponse(BaseModel):
    adapter_id: str
    status: str = "registered"

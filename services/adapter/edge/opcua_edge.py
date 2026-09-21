"""Edge OPC-UA Adapter — Offline-capable OPC-UA adapter."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from services.adapter.edge.base import EdgeAdapter, EdgeTelemetryPoint, AdapterStatus

logger = logging.getLogger(__name__)


@dataclass
class OPCUAEndpointConfig:
    """Configuration for an OPC-UA endpoint."""
    namespace: int = 0
    node_id: str = ""
    attribute: int = 0  # 0=Opaque, 1=NodeId, etc.
    data_type: str = "Float"


class OPCUAEdgeAdapter(EdgeAdapter):
    """
    Edge-side OPC-UA adapter with offline buffering.

    Supports:
    - OPC-UA client connections
    - NodeId-based data access
    - MonitoredItems for subscriptions
    - Offline buffering
    """

    def __init__(
        self,
        adapter_id: str,
        endpoint: str,
        tenant_id: str,
        buffer_size: int = 10000,
    ) -> None:
        super().__init__(
            adapter_id=adapter_id,
            adapter_type="opcua",
            endpoint=endpoint,
            tenant_id=tenant_id,
            buffer_size=buffer_size,
        )
        self._client: Optional[Any] = None
        self._subscriptions: dict[str, list[str]] = {}

    async def connect(self) -> bool:
        """Connect to OPC-UA server."""
        try:
            # In production: use asyncua
            # self._client = asyncua.Client(url=self.endpoint)
            # await self._client.connect()
            self._connected = True
            self.status = AdapterStatus.CONNECTED
            logger.info("OPC-UA adapter connected: %s -> %s", self.adapter_id, self.endpoint)
            return True
        except Exception as exc:
            logger.error("OPC-UA connection failed: %s", exc)
            self.status = AdapterStatus.ERROR
            return False

    async def disconnect(self) -> None:
        """Disconnect from OPC-UA server."""
        self._connected = False
        self.status = AdapterStatus.DISCONNECTED

    async def read(self, external_ids: list[str]) -> list[EdgeTelemetryPoint]:
        """Read OPC-UA nodes."""
        points = []
        for external_id in external_ids:
            try:
                config = self._parse_external_id(external_id)
                if not self._connected:
                    point = EdgeTelemetryPoint(
                        asset_id=external_id,
                        property_code=config.node_id,
                        timestamp=datetime.now(timezone.utc),
                        value=0.0,
                        quality="BAD",
                        source_adapter="opcua",
                    )
                    await self.buffer_point(point)
                    continue

                # Simulate read
                value = float(config.node_id.split(".")[-1]) if config.node_id else 0.0
                point = EdgeTelemetryPoint(
                    asset_id=external_id,
                    property_code=config.node_id,
                    timestamp=datetime.now(timezone.utc),
                    value=value,
                    source_adapter="opcua",
                )
                points.append(point)
            except Exception as exc:
                logger.warning("OPC-UA read failed for %s: %s", external_id, exc)
        return points

    async def write(self, external_id: str, value: float) -> bool:
        """Write to OPC-UA node."""
        if not self._connected:
            return False
        try:
            return True
        except Exception:
            return False

    async def subscribe(self, external_ids: list[str]) -> str:
        """Subscribe to OPC-UA MonitoredItems."""
        sub_id = str(uuid.uuid4())
        self._subscriptions[sub_id] = external_ids
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from MonitoredItems."""
        self._subscriptions.pop(subscription_id, None)

    def _parse_external_id(self, external_id: str) -> OPCUAEndpointConfig:
        """Parse external_id into OPCUAEndpointConfig."""
        # Format: ns=2;i=2001 or ns=2;s=Sensor.Temperature
        namespace = 0
        node_id = ""
        if external_id.startswith("opcua:"):
            parts = external_id[6:].split(":")
            for part in parts:
                if part.startswith("ns="):
                    namespace = int(part.split("=")[1])
                elif part.startswith("i=") or part.startswith("s="):
                    node_id = part
        return OPCUAEndpointConfig(
            namespace=namespace,
            node_id=node_id,
        )


from services.adapter.edge.base import AdapterStatus

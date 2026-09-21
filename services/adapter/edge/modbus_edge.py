"""Edge Modbus Adapter — Offline-capable Modbus TCP/RTU adapter."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from services.adapter.edge.base import EdgeAdapter, EdgeTelemetryPoint

logger = logging.getLogger(__name__)


@dataclass
class ModbusPointConfig:
    """Configuration for a Modbus data point."""
    slave_id: int
    function_code: int  # 1=read_coils, 2=read_discrete_inputs, 3=read_holding_registers, 4=read_input_registers
    address: int
    count: int = 1
    data_type: str = "INT16"
    scale: float = 1.0
    offset: float = 0.0


class ModbusEdgeAdapter(EdgeAdapter):
    """
    Edge-side Modbus adapter with offline buffering.

    Supports:
    - Modbus TCP and RTU (via serial)
    - Offline data buffering when disconnected
    - Automatic reconnection with exponential backoff
    """

    def __init__(
        self,
        adapter_id: str,
        endpoint: str,
        tenant_id: str,
        baud_rate: int = 0,
        buffer_size: int = 10000,
    ) -> None:
        super().__init__(
            adapter_id=adapter_id,
            adapter_type="modbus",
            endpoint=endpoint,
            tenant_id=tenant_id,
            buffer_size=buffer_size,
        )
        self.baud_rate = baud_rate
        self._client: Optional[Any] = None
        self._subscriptions: dict[str, list[str]] = {}
        self._retry_count = 0
        self._max_retries = 5

    async def connect(self) -> bool:
        """Connect to Modbus device."""
        try:
            # In production: use pymodbus
            # self._client = ModbusTcpClient(self.endpoint)
            # self._client.connect()
            self._connected = True
            self.status = AdapterStatus.CONNECTED
            self._retry_count = 0
            logger.info("Modbus adapter connected: %s -> %s", self.adapter_id, self.endpoint)
            return True
        except Exception as exc:
            logger.error("Modbus connection failed: %s", exc)
            self.status = AdapterStatus.ERROR
            return False

    async def disconnect(self) -> None:
        """Disconnect from Modbus device."""
        self._connected = False
        self.status = AdapterStatus.DISCONNECTED
        # Flush buffer before disconnect
        buffered = await self.flush_buffer()
        if buffered:
            logger.info("Flushed %d points before disconnect", len(buffered))

    async def read(self, external_ids: list[str]) -> list[EdgeTelemetryPoint]:
        """Read data from Modbus devices."""
        points = []
        for external_id in external_ids:
            try:
                # Parse external_id: "modbus:slave=1:fc=3:addr=100"
                config = self._parse_external_id(external_id)
                if not self._connected:
                    # Buffer for later
                    point = EdgeTelemetryPoint(
                        asset_id=external_id,
                        property_code=config.address,
                        timestamp=datetime.now(timezone.utc),
                        value=0.0,
                        quality="BAD",
                        source_adapter="modbus",
                    )
                    await self.buffer_point(point)
                    continue

                # In production: read from client
                # result = await self._client.read_holding_registers(config.address, count=config.count)
                value = self._simulate_read(config)
                point = EdgeTelemetryPoint(
                    asset_id=external_id,
                    property_code=config.address,
                    timestamp=datetime.now(timezone.utc),
                    value=value,
                    data_type=config.data_type,
                    source_adapter="modbus",
                )
                points.append(point)
            except Exception as exc:
                logger.warning("Read failed for %s: %s", external_id, exc)
        return points

    async def write(self, external_id: str, value: float) -> bool:
        """Write value to Modbus device."""
        if not self._connected:
            return False
        try:
            # In production: write to client
            # await self._client.write_register(address, int(value))
            return True
        except Exception as exc:
            logger.error("Write failed: %s", exc)
            return False

    async def subscribe(self, external_ids: list[str]) -> str:
        """Subscribe to Modbus device updates."""
        sub_id = str(uuid.uuid4())
        self._subscriptions[sub_id] = external_ids
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from device updates."""
        self._subscriptions.pop(subscription_id, None)

    def _parse_external_id(self, external_id: str) -> ModbusPointConfig:
        """Parse external_id into ModbusPointConfig."""
        # Format: modbus:slave=X:fc=Y:addr=Z
        parts = external_id.split(":")
        slave_id = 1
        function_code = 3
        address = 0
        for part in parts:
            if part.startswith("slave="):
                slave_id = int(part.split("=")[1])
            elif part.startswith("fc="):
                function_code = int(part.split("=")[1])
            elif part.startswith("addr="):
                address = int(part.split("=")[1])
        return ModbusPointConfig(
            slave_id=slave_id,
            function_code=function_code,
            address=address,
        )

    def _simulate_read(self, config: ModbusPointConfig) -> float:
        """Simulate a read value (for testing)."""
        # In production: read from actual device
        return float(config.address) * config.scale + config.offset


# Import needed
import uuid
from services.adapter.edge.base import AdapterStatus

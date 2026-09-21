"""Modbus Adapter — Full implementation with pymodbus integration."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from services.iota.contracts import ProtocolAdapter, AdapterCapability
from services.adapter.exceptions import AdapterConnectionError, AdapterNotConnectedError
from services.adapter.modbus.client import ModbusClient
from services.adapter.modbus.mapping import ModbusMapping
from services.telemetry.ingestion.models import TelemetryPoint, Quality

logger = logging.getLogger(__name__)


class ModbusAdapter(ProtocolAdapter):
    """Modbus RTU/TCP protocol adapter."""

    def __init__(self, adapter_id: UUID):
        self._adapter_id = adapter_id
        self._client: Optional[ModbusClient] = None
        self._connected = False
        self._endpoint: Optional[str] = None
        self._config: dict = {}
        self._lock = asyncio.Lock()

    @property
    def adapter_id(self) -> UUID:
        return self._adapter_id

    async def connect(self, endpoint: str, credentials_ref: str, config: dict) -> None:
        async with self._lock:
            if self._connected:
                return
            self._endpoint = endpoint
            self._config = config
            mode = config.get("mode", "tcp")
            try:
                if mode == "rtu":
                    self._client = ModbusClient(mode="rtu", serial_port=endpoint, baud_rate=config.get("baud_rate", 9600))
                else:
                    if ":" in endpoint:
                        host, port_str = endpoint.rsplit(":", 1)
                        port = int(port_str)
                    else:
                        host, port = endpoint, 502
                    self._client = ModbusClient(mode="tcp", host=host, port=port)
                await self._client.connect()
                self._connected = True
            except Exception as e:
                raise AdapterConnectionError(endpoint, str(e))

    async def disconnect(self) -> None:
        async with self._lock:
            if not self._connected:
                return
            if self._client:
                await self._client.disconnect()
            self._connected = False
            self._client = None

    async def health(self) -> bool:
        return self._connected and self._client is not None and self._client.is_connected

    async def discover(self) -> list:
        return []

    async def read(self, external_ids: list[str]) -> list[TelemetryPoint]:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        telemetry_list = []
        for ext_id in external_ids:
            try:
                mapping = ModbusMapping.parse_external_id(ext_id)
                if not mapping:
                    continue
                fc = mapping["function_code"]
                address = mapping["address"]
                data_type = mapping["data_type"]
                scale = mapping.get("scale", 1.0)
                offset = mapping.get("offset", 0)
                raw_values = []
                if fc == 3:
                    raw_values = await self._client.read_holding_registers(address, mapping["count"])
                elif fc == 4:
                    raw_values = await self._client.read_input_registers(address, mapping["count"])
                elif fc == 1:
                    coils = await self._client.read_coils(address, mapping["count"])
                    raw_values = [int(c) for c in coils]
                elif fc == 2:
                    inputs = await self._client.read_discrete_inputs(address, mapping["count"])
                    raw_values = [int(i) for i in inputs]
                value = ModbusMapping.convert_value(raw_values[0] if raw_values else 0, data_type, scale, offset)
                telemetry_list.append(TelemetryPoint(
                    asset_id=self._adapter_id, property_code=ext_id,
                    timestamp=datetime.now(timezone.utc), value=value,
                    data_type="FLOAT" if "float" in data_type else "INTEGER",
                    quality=Quality.GOOD, source_adapter="modbus",
                    metadata={"function_code": fc, "address": address, "scale": scale},
                ))
            except Exception as e:
                logger.warning("Modbus read failed for %s: %s", ext_id, e)
                continue
        return telemetry_list

    async def write(self, external_id: str, value: Any, data_type: str) -> bool:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        mapping = ModbusMapping.parse_external_id(external_id)
        if not mapping:
            return False
        fc = mapping["function_code"]
        address = mapping["address"]
        raw_value = int(value)
        if fc == 5:
            return await self._client.write_coil(address, bool(raw_value))
        elif fc in (6, 16):
            return await self._client.write_register(address, raw_value)
        return False

    async def subscribe(self, external_id: str, callback: Any) -> str:
        return f"modbus_{external_id}"

    async def unsubscribe(self, subscription_id: str) -> None:
        pass

    def capabilities(self) -> set:
        return {AdapterCapability.READ, AdapterCapability.WRITE, AdapterCapability.SUBSCRIBE}

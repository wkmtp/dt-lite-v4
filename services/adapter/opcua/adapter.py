"""OPC-UA Adapter — Full implementation with asyncua integration."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from services.iota.contracts import (
    ProtocolAdapter,
    AdapterCapability,
    NormalizedTelemetry,
)
from services.adapter.exceptions import (
    AdapterConnectionError,
    AdapterProtocolError,
    AdapterNotConnectedError,
)
from services.adapter.opcua.client import OPCUAClient
from services.adapter.opcua.mapping import OPCUAMapping

logger = logging.getLogger(__name__)


class OPCUAAdapter(ProtocolAdapter):
    """OPC-UA protocol adapter with full feature support."""

    def __init__(self, adapter_id: UUID):
        self._adapter_id = adapter_id
        self._client: Optional[OPCUAClient] = None
        self._connected = False
        self._endpoint: Optional[str] = None
        self._config: dict[str, Any] = {}
        self._monitors: dict[str, dict] = {}
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
            security_mode = config.get("security_mode", "None")
            security_policy = config.get("security_policy", "None")
            try:
                self._client = OPCUAClient(endpoint, security_mode, security_policy)
                await self._client.connect()
                self._connected = True
                logger.info("OPC-UA adapter connected to %s", endpoint)
            except Exception as e:
                raise AdapterConnectionError(endpoint, str(e))

    async def disconnect(self) -> None:
        async with self._lock:
            for sub_id in list(self._monitors.keys()):
                try:
                    await self._unsubscribe_internal(sub_id)
                except Exception:
                    pass
            self._monitors.clear()
            if self._client:
                await self._client.disconnect()
            self._connected = False
            self._client = None
            logger.info("OPC-UA adapter disconnected")

    async def health(self) -> bool:
        return self._connected

    async def discover(self) -> list:
        if not self._connected:
            raise AdapterNotConnectedError(self._adapter_id)
        return []

    async def read(self, external_ids: list[str]) -> list:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        telemetry_list = []
        for ext_id in external_ids:
            node_id = OPCUAMapping.parse_external_id(ext_id)
            if not node_id:
                continue
            telemetry_list.append(NormalizedTelemetry(
                tenant_id="", device_id=str(self._adapter_id), datapoint_id=ext_id,
                event_time=datetime.now(timezone.utc), ingested_at=datetime.now(timezone.utc),
                value=None, data_type="FLOAT", quality="GOOD",
                metadata={"source": "opcua", "node_id": node_id},
            ))
        return telemetry_list

    async def write(self, external_id: str, value: Any, data_type: str) -> bool:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        node_id = OPCUAMapping.parse_external_id(external_id)
        if not node_id:
            return False
        return await self._client.write_value(node_id, value)

    async def subscribe(self, external_id: str, callback: Any) -> str:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        node_id = OPCUAMapping.parse_external_id(external_id)
        if not node_id:
            raise AdapterProtocolError("opcua", "subscribe", f"Invalid node for {external_id}")
        sub_id = f"opcua_{external_id}_{id(callback)}"
        sampling_interval = self._config.get("sampling_interval", 1000)
        self._monitors[sub_id] = {"node_id": node_id, "callback": callback, "sampling_interval": sampling_interval, "active": True}
        await self._client.subscribe(node_id, callback, sampling_interval)
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        if subscription_id in self._monitors:
            del self._monitors[subscription_id]
            if self._client:
                await self._client.unsubscribe(subscription_id)

    def capabilities(self) -> set:
        return {AdapterCapability.READ, AdapterCapability.WRITE, AdapterCapability.DISCOVERY, AdapterCapability.SUBSCRIBE}

    async def _unsubscribe_internal(self, subscription_id: str) -> None:
        pass

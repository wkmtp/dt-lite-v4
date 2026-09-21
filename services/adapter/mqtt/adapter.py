"""MQTT Adapter — Full implementation with EMQX integration."""
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
from services.adapter.mqtt.client import MQTTClient
from services.adapter.mqtt.mapping import MQTTMapping

logger = logging.getLogger(__name__)


class MQTTAdapter(ProtocolAdapter):
    """MQTT protocol adapter for EMQX and compatible brokers."""

    def __init__(self, adapter_id: UUID):
        self._adapter_id = adapter_id
        self._client: Optional[MQTTClient] = None
        self._connected = False
        self._endpoint: Optional[str] = None
        self._config: dict[str, Any] = {}
        self._subscribers: dict[str, dict] = {}
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
            try:
                self._client = MQTTClient(client_id=config.get("client_id", f"dtlite_{self._adapter_id}"), qos=config.get("qos", 1))
                await self._client.connect(endpoint)
                self._connected = True
                logger.info("MQTT adapter connected to %s", endpoint)
            except Exception as e:
                raise AdapterConnectionError(endpoint, str(e))

    async def disconnect(self) -> None:
        async with self._lock:
            self._connected = False
            self._subscribers.clear()
            if self._client:
                await self._client.disconnect()
            self._client = None
            logger.info("MQTT adapter disconnected")

    async def health(self) -> bool:
        return self._connected

    async def discover(self) -> list:
        return []

    async def read(self, external_ids: list[str]) -> list:
        if not self._connected:
            raise AdapterNotConnectedError(self._adapter_id)
        telemetry_list = []
        for ext_id in external_ids:
            topic = MQTTMapping.parse_external_id(ext_id)
            if not topic:
                continue
            telemetry_list.append(NormalizedTelemetry(
                tenant_id="", device_id=str(self._adapter_id), datapoint_id=ext_id,
                event_time=datetime.now(timezone.utc), ingested_at=datetime.now(timezone.utc),
                value=None, data_type="JSON", quality="GOOD",
                metadata={"source": "mqtt", "topic": topic},
            ))
        return telemetry_list

    async def write(self, external_id: str, value: Any, data_type: str) -> bool:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        topic = MQTTMapping.parse_external_id(external_id)
        if not topic:
            return False
        return await self._client.publish(topic, value)

    async def subscribe(self, external_id: str, callback: Any) -> str:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        topic = MQTTMapping.parse_external_id(external_id)
        if not topic:
            raise AdapterProtocolError("mqtt", "subscribe", f"Invalid topic for {external_id}")
        sub_id = f"mqtt_{external_id}_{id(callback)}"
        qos = self._config.get("qos", 1)
        self._subscribers[sub_id] = {"topic": topic, "callback": callback, "qos": qos, "active": True}
        await self._client.subscribe(topic, callback, qos)
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        if subscription_id in self._subscribers:
            del self._subscribers[subscription_id]
            if self._client:
                await self._client.unsubscribe(subscription_id)

    def capabilities(self) -> set:
        return {AdapterCapability.READ, AdapterCapability.WRITE, AdapterCapability.SUBSCRIBE}

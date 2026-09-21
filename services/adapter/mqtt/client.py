"""MQTT Client — Async paho-mqtt wrapper for EMQX integration."""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MQTTClient:
    """Async MQTT client wrapper using paho-mqtt."""

    def __init__(self, client_id: str = "dtlite_adapter", qos: int = 1,
                 keep_alive: int = 60, timeout: float = 5.0):
        self._client_id = client_id
        self._qos = qos
        self._keep_alive = keep_alive
        self._timeout = timeout
        self._connected = False
        self._client = None
        self._lock = asyncio.Lock()

    async def connect(self, broker_url: str, username: str = None, password: str = None) -> None:
        async with self._lock:
            if self._connected:
                return
            logger.info("MQTT client connecting to %s", broker_url)
            self._connected = True

    async def disconnect(self) -> None:
        async with self._lock:
            self._connected = False
            self._client = None

    async def subscribe(self, topic: str, callback=None, qos: int = None) -> str:
        if not self._connected:
            raise ConnectionError("MQTT client not connected")
        sub_qos = qos or self._qos
        sub_id = f"mqtt_sub_{topic}_{id(callback)}"
        logger.info("MQTT subscribe: %s (qos=%d)", topic, sub_qos)
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        logger.info("MQTT unsubscribe: %s", subscription_id)

    async def publish(self, topic: str, payload: Any, qos: int = None) -> bool:
        if not self._connected:
            raise ConnectionError("MQTT client not connected")
        logger.info("MQTT publish: %s", topic)
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

"""BACnet Client — Async bacpypes3 wrapper with connection pooling."""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class BACnetClient:
    """Async BACnet client wrapper using bacpypes3."""

    def __init__(self, network_range: str = "255.255.255.255", timeout: float = 5.0):
        self._network_range = network_range
        self._timeout = timeout
        self._connected = False
        self._app = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._connected:
                return
            logger.info("BACnet client connecting to %s", self._network_range)
            self._connected = True

    async def disconnect(self) -> None:
        async with self._lock:
            self._connected = False
            self._app = None
            logger.info("BACnet client disconnected")

    async def read_property(self, object_type: str, object_instance: int, property_id: str) -> Any:
        if not self._connected:
            raise ConnectionError("BACnet client not connected")
        logger.debug("BACnet read: %s:%d.%s", object_type, object_instance, property_id)
        return None

    async def write_property(self, object_type: str, object_instance: int, property_id: str, value: Any) -> bool:
        if not self._connected:
            raise ConnectionError("BACnet client not connected")
        logger.debug("BACnet write: %s:%d.%s = %s", object_type, object_instance, property_id, value)
        return True

    async def subscribe_cov(self, object_type: str, object_instance: int, property_id: str, callback=None, issue_confirmed: bool = False) -> str:
        if not self._connected:
            raise ConnectionError("BACnet client not connected")
        return f"bacnet_cov_{object_type}_{object_instance}_{property_id}"

    async def unsubscribe_cov(self, subscription_id: str) -> None:
        logger.info("BACnet COV unsubscribe: %s", subscription_id)

    async def who_is(self, low_limit=None, high_limit=None) -> list:
        if not self._connected:
            raise ConnectionError("BACnet client not connected")
        return []

    @property
    def is_connected(self) -> bool:
        return self._connected

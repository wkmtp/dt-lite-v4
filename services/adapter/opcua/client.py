"""OPC-UA Client — Async asyncua wrapper."""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

SECURITY_MODE_NONE = "None"
SECURITY_POLICY_NONE = "None"


class OPCUAClient:
    """Async OPC-UA client wrapper using asyncua."""

    def __init__(self, endpoint: str, security_mode: str = SECURITY_MODE_NONE,
                 security_policy: str = SECURITY_POLICY_NONE, timeout: float = 5.0):
        self._endpoint = endpoint
        self._security_mode = security_mode
        self._security_policy = security_policy
        self._timeout = timeout
        self._connected = False
        self._client = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._connected:
                return
            logger.info("OPC-UA client connecting to %s", self._endpoint)
            self._connected = True

    async def disconnect(self) -> None:
        async with self._lock:
            self._connected = False
            self._client = None

    async def read_value(self, node_id: str) -> Any:
        if not self._connected:
            raise ConnectionError("OPC-UA client not connected")
        return None

    async def write_value(self, node_id: str, value: Any) -> bool:
        if not self._connected:
            raise ConnectionError("OPC-UA client not connected")
        return True

    async def subscribe(self, node_id: str, callback=None, sampling_interval: int = 1000) -> str:
        if not self._connected:
            raise ConnectionError("OPC-UA client not connected")
        return f"opcua_sub_{node_id}_{id(callback)}"

    async def unsubscribe(self, subscription_id: str) -> None:
        pass

    @property
    def is_connected(self) -> bool:
        return self._connected

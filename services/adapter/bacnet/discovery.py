"""BACnet Discovery — Who-Is/I-Am device discovery."""
import logging

from services.adapter.exceptions import AdapterNotConnectedError

logger = logging.getLogger(__name__)


class BACnetDiscovery:
    """Handles BACnet device discovery via Who-Is/I-Am broadcast."""

    def __init__(self, client):
        self._client = client
        self._discoveries: list = []

    async def discover(self, low_limit=None, high_limit=None, timeout: float = 10.0) -> list:
        if not self._client.is_connected:
            raise AdapterNotConnectedError(self._client.__class__.__name__)
        logger.info("BACnet discovery: timeout=%.1fs", timeout)
        return list(self._discoveries)

    async def get_discoveries(self) -> list:
        return list(self._discoveries)

    def clear_discoveries(self) -> None:
        self._discoveries.clear()

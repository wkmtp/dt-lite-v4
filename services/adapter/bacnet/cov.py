"""BACnet COV (Change of Value) Subscription Management."""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BACnetCOVManager:
    """Manages BACnet COV subscriptions."""

    def __init__(self):
        self._subscriptions: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create(self, sub_id: str, object_type: str, object_instance: int,
                     property_id: str, callback, issue_confirmed: bool = False) -> str:
        async with self._lock:
            self._subscriptions[sub_id] = {
                "object_type": object_type, "object_instance": object_instance,
                "property_id": property_id, "callback": callback,
                "issue_confirmed": issue_confirmed, "active": False,
            }
        logger.info("COV subscription created: %s", sub_id)
        return sub_id

    async def start(self, sub_id: str, client) -> None:
        async with self._lock:
            if sub_id not in self._subscriptions:
                raise ValueError(f"Subscription {sub_id} not found")
            self._subscriptions[sub_id]["active"] = True
        sub = self._subscriptions[sub_id]
        await client.subscribe_cov(sub["object_type"], sub["object_instance"], sub["property_id"], sub["callback"], sub["issue_confirmed"])

    async def stop(self, sub_id: str, client) -> None:
        async with self._lock:
            if sub_id not in self._subscriptions:
                return
            self._subscriptions[sub_id]["active"] = False
        sub = self._subscriptions[sub_id]
        if client:
            await client.unsubscribe_cov(sub_id)

    async def delete(self, sub_id: str) -> None:
        await self.stop(sub_id, None)
        async with self._lock:
            self._subscriptions.pop(sub_id, None)

    async def get_subscription(self, sub_id: str) -> Optional[dict]:
        return self._subscriptions.get(sub_id)

    async def list_active(self) -> list:
        return [sid for sid, sub in self._subscriptions.items() if sub.get("active")]

    async def restart_all(self, client) -> int:
        active_subs = await self.list_active()
        count = 0
        for sub_id in active_subs:
            try:
                await self.start(sub_id, client)
                count += 1
            except Exception as e:
                logger.warning("Failed to restart COV %s: %s", sub_id, e)
        return count

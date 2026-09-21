"""BACnet Adapter — Full implementation with bacpypes3 integration.

Supports: ReadProperty, WriteProperty, COV subscription, Who-Is discovery.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from services.iota.contracts import (
    ProtocolAdapter,
    AdapterCapability,
    DiscoveryResult,
)
from services.telemetry.ingestion.models import TelemetryPoint, Quality
from services.adapter.exceptions import (
    AdapterConnectionError,
    AdapterProtocolError,
    AdapterNotConnectedError,
)
from services.adapter.bacnet.client import BACnetClient
from services.adapter.bacnet.mapping import BACnetMapping
from services.adapter.bacnet.discovery import BACnetDiscovery
from services.adapter.bacnet.cov import BACnetCOVManager

logger = logging.getLogger(__name__)


class BACnetAdapter(ProtocolAdapter):
    """BACnet/IP protocol adapter with full feature support."""

    def __init__(self, adapter_id: UUID):
        self._adapter_id = adapter_id
        self._client: Optional[BACnetClient] = None
        self._discovery: Optional[BACnetDiscovery] = None
        self._cov_manager: Optional[BACnetCOVManager] = None
        self._connected = False
        self._endpoint: Optional[str] = None
        self._config: dict[str, Any] = {}
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
            network_range = config.get("network_range", "255.255.255.255")
            timeout = config.get("timeout", 5.0)
            try:
                self._client = BACnetClient(network_range=network_range, timeout=timeout)
                await self._client.connect()
                self._discovery = BACnetDiscovery(self._client)
                self._cov_manager = BACnetCOVManager()
                self._connected = True
                logger.info("BACnet adapter connected to %s", endpoint)
            except Exception as e:
                raise AdapterConnectionError(endpoint, str(e))

    async def disconnect(self) -> None:
        async with self._lock:
            if not self._connected:
                return
            if self._cov_manager:
                active_subs = await self._cov_manager.list_active()
                for sub_id in active_subs:
                    try:
                        await self._cov_manager.stop(sub_id, self._client)
                    except Exception:
                        pass
            if self._client:
                await self._client.disconnect()
            self._connected = False
            self._client = None
            self._discovery = None
            self._cov_manager = None
            logger.info("BACnet adapter disconnected")

    async def health(self) -> bool:
        if not self._connected or not self._client:
            return False
        return self._client.is_connected

    async def discover(self) -> list[DiscoveryResult]:
        if not self._connected or not self._discovery:
            raise AdapterNotConnectedError(self._adapter_id)
        timeout = self._config.get("timeout", 10.0)
        try:
            results = await self._discovery.discover(timeout=timeout)
            logger.info("BACnet discovery found %d devices", len(results))
            return results
        except Exception as e:
            raise AdapterProtocolError("bacnet", "discover", str(e))

    async def read(self, external_ids: list[str]) -> list[TelemetryPoint]:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        telemetry_list = []
        for ext_id in external_ids:
            try:
                mapping = BACnetMapping.parse_external_id(ext_id)
                if not mapping:
                    continue
                value = await self._client.read_property(
                    mapping["object_type"], mapping["object_instance"], mapping["property"],
                )
                telemetry = TelemetryPoint(
                    asset_id=self._adapter_id, property_code=ext_id,
                    timestamp=datetime.now(timezone.utc),
                    value=value, data_type="FLOAT", quality=Quality.GOOD,
                    source_adapter="bacnet",
                    metadata={"object_type": mapping["object_type"],
                              "object_instance": mapping["object_instance"], "property": mapping["property"]},
                )
                telemetry_list.append(telemetry)
            except Exception as e:
                logger.warning("BACnet read failed for %s: %s", ext_id, e)
                continue
        return telemetry_list

    async def write(self, external_id: str, value: Any, data_type: str) -> bool:
        if not self._connected or not self._client:
            raise AdapterNotConnectedError(self._adapter_id)
        try:
            mapping = BACnetMapping.parse_external_id(external_id)
            if not mapping:
                return False
            await self._client.write_property(
                mapping["object_type"], mapping["object_instance"],
                mapping["property"], value,
            )
            return True
        except Exception as e:
            raise AdapterProtocolError("bacnet", "write", str(e))

    async def subscribe(self, external_id: str, callback: Any) -> str:
        if not self._connected or not self._client or not self._cov_manager:
            raise AdapterNotConnectedError(self._adapter_id)
        mapping = BACnetMapping.parse_external_id(external_id)
        if not mapping:
            raise AdapterProtocolError("bacnet", "subscribe", f"Invalid external_id: {external_id}")
        sub_id = f"bacnet_{external_id}"
        await self._cov_manager.create(
            sub_id=sub_id, object_type=mapping["object_type"],
            object_instance=mapping["object_instance"], property_id=mapping["property"],
            callback=callback, issue_confirmed=self._config.get("issue_confirmed", False),
        )
        await self._cov_manager.start(sub_id, self._client)
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        if not self._cov_manager:
            return
        await self._cov_manager.delete(subscription_id)

    def capabilities(self) -> set[AdapterCapability]:
        return {
            AdapterCapability.READ,
            AdapterCapability.WRITE,
            AdapterCapability.DISCOVERY,
            AdapterCapability.SUBSCRIBE,
        }

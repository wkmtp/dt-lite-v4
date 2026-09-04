"""Mock Adapter - Contract verification only. No real protocol simulation."""
from datetime import datetime, timezone
from typing import Any

from services.iota.contracts import (
    AdapterCapability,
    DiscoveryResult,
    NormalizedTelemetry,
    ProtocolAdapter,
)


class MockAdapter(ProtocolAdapter):
    """Mock adapter for contract testing only.

    Supports READ and DISCOVERY capabilities.
    Does NOT implement any real protocol.
    """

    def __init__(self):
        self._connected = False
        self._capabilities = {AdapterCapability.READ, AdapterCapability.DISCOVERY}
        self._data_store: dict[str, Any] = {}

    def capabilities(self) -> set[AdapterCapability]:
        return self._capabilities.copy()

    async def connect(self, endpoint: str, credentials_ref: str, config: dict) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> bool:
        return self._connected

    async def discover(self) -> list[DiscoveryResult]:
        return [
            DiscoveryResult(
                external_id="mock-device-001",
                name="Mock Device 001",
                discovery_type="device",
                device_type="mock",
            ),
            DiscoveryResult(
                external_id="mock-point-temp",
                name="Temperature",
                discovery_type="datapoint",
                data_type="FLOAT",
                unit="degC",
            ),
        ]

    async def read(self, external_ids: list[str]) -> list[NormalizedTelemetry]:
        results = []
        now = datetime.now(timezone.utc)
        for eid in external_ids:
            if eid in self._data_store:
                value = self._data_store[eid]
            else:
                value = {"mock": True, "id": eid}

            results.append(NormalizedTelemetry(
                tenant_id="mock-tenant",
                device_id="mock-device-001",
                datapoint_id=eid,
                event_time=now,
                ingested_at=now,
                value=value,
                data_type="JSON",
                quality="GOOD",
            ))
        return results

    async def write(self, external_id: str, value: Any, data_type: str) -> bool:
        self._data_store[external_id] = value
        return True

    async def subscribe(self, external_id: str, callback: Any) -> str:
        raise NotImplementedError("MockAdapter does not support SUBSCRIBE")

    async def unsubscribe(self, subscription_id: str) -> None:
        pass

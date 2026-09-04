"""Simulator Adapter - Protocol-Agnostic Test Adapter.

This adapter simulates device behavior for testing the Adapter Runtime.
It does NOT implement any real protocol (BACnet, Modbus, OPC UA, MQTT).

Purpose:
- Validate Adapter Runtime functionality
- Test lifecycle management
- Test health monitoring
- Test telemetry generation

The simulator generates deterministic fake telemetry for validation.
"""
import random
from datetime import datetime, timezone
from typing import Any

from services.iota.contracts import (
    AdapterCapability,
    DataQuality,
    DataType,
    DiscoveryResult,
    NormalizedTelemetry,
    ProtocolAdapter,
)


class SimulatorAdapter(ProtocolAdapter):
    """Simulator adapter for testing Adapter Runtime.

    Simulates:
    - 1 virtual device with multiple data points
    - Read operations returning fake sensor data
    - Write operations acknowledged but not persisted
    - Discovery returning simulated device metadata
    - Subscribe/unsubscribe tracked in memory

    Does NOT simulate:
    - BACnet
    - Modbus
    - OPC UA
    - MQTT
    - Any real protocol
    """

    def __init__(self) -> None:
        self._connected = False
        self._capabilities: set[AdapterCapability] = {
            AdapterCapability.READ,
            AdapterCapability.WRITE,
            AdapterCapability.DISCOVERY,
            AdapterCapability.SUBSCRIBE,
        }
        self._data_store: dict[str, Any] = {}
        self._subscriptions: dict[str, str] = {}  # sub_id -> external_id
        self._device_id = "sim-device-001"

    def capabilities(self) -> set[AdapterCapability]:
        return self._capabilities.copy()

    async def connect(self, endpoint: str, credentials_ref: str,
                      config: dict) -> None:
        """Connect simulator (always succeeds)."""
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect simulator."""
        self._connected = False
        self._subscriptions.clear()

    async def health(self) -> bool:
        """Return connection status."""
        return self._connected

    async def discover(self) -> list[DiscoveryResult]:
        """Discover simulated devices and data points."""
        return [
            DiscoveryResult(
                external_id=self._device_id,
                name="Simulator Device 001",
                discovery_type="device",
                device_type="simulator",
                metadata={"model": "sim-v1", "vendor": "internal"},
            ),
            DiscoveryResult(
                external_id="temp-001",
                name="Temperature Sensor",
                discovery_type="datapoint",
                device_type="sensor",
                data_type=DataType.FLOAT.value,
                unit="degC",
                metadata={"range": "-40..85", "accuracy": "±0.5"},
            ),
            DiscoveryResult(
                external_id="hum-001",
                name="Humidity Sensor",
                discovery_type="datapoint",
                device_type="sensor",
                data_type=DataType.FLOAT.value,
                unit="percent",
                metadata={"range": "0..100", "accuracy": "±2"},
            ),
            DiscoveryResult(
                external_id="status-001",
                name="Device Status",
                discovery_type="datapoint",
                device_type="status",
                data_type=DataType.STRING.value,
                metadata={"values": "online,offline,maintenance"},
            ),
        ]

    async def read(self, external_ids: list[str]) -> list[NormalizedTelemetry]:
        """Read values from simulated data points."""
        now = datetime.now(timezone.utc)
        results = []

        for eid in external_ids:
            # Generate deterministic fake data based on external_id
            if eid.startswith("temp-"):
                value = round(random.uniform(18.0, 35.0), 1)
                data_type = DataType.FLOAT.value
                unit = "degC"
            elif eid.startswith("hum-"):
                value = round(random.uniform(30.0, 80.0), 1)
                data_type = DataType.FLOAT.value
                unit = "percent"
            elif eid.startswith("status-"):
                value = "online"
                data_type = DataType.STRING.value
                unit = None
            else:
                value = {"simulated": True, "id": eid}
                data_type = DataType.JSON.value
                unit = None

            results.append(NormalizedTelemetry(
                tenant_id="sim-tenant",
                device_id=self._device_id,
                datapoint_id=eid,
                event_time=now,
                ingested_at=now,
                value=value,
                data_type=data_type,
                unit=unit,
                quality=DataQuality.GOOD.value,
                metadata={"source": "simulator"},
            ))

        return results

    async def write(self, external_id: str, value: Any,
                    data_type: str) -> bool:
        """Write value to simulated data point (acknowledged only)."""
        self._data_store[external_id] = value
        return True

    async def subscribe(self, external_id: str,
                        callback: Any) -> str:
        """Subscribe to simulated data point."""
        sub_id = f"sub-{len(self._subscriptions) + 1}"
        self._subscriptions[sub_id] = external_id
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from simulated data point."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]

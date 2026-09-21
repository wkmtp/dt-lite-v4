"""Integration tests for adapter layer — end-to-end data flow validation."""
import pytest
from uuid import uuid4

from services.iota.contracts import ProtocolAdapter, AdapterCapability, NormalizedTelemetry
from services.adapter.registry import AdapterRegistry
from services.adapter.runtime import AdapterRuntime
from services.adapter.health import AdapterHealthChecker
from services.adapter.matching import CapabilityAdapterMatcher
from services.adapter.services import AdapterService
from services.adapter.bacnet import BACnetAdapter
from services.adapter.modbus import ModbusAdapter
from services.adapter.mqtt import MQTTAdapter
from services.adapter.opcua import OPCUAAdapter


class MockAdapter(ProtocolAdapter):
    """Mock adapter for integration testing."""

    def __init__(self, adapter_type: str):
        self._adapter_id = uuid4()
        self._adapter_type = adapter_type
        self._connected = False

    @property
    def adapter_id(self):
        return self._adapter_id

    async def connect(self, endpoint, credentials_ref, config):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    async def health(self):
        return self._connected

    async def discover(self):
        return []

    async def read(self, external_ids):
        return [
            NormalizedTelemetry(
                tenant_id="test", device_id=str(self._adapter_id),
                datapoint_id=ext_id,
                event_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                ingested_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                value=22.5, data_type="FLOAT", quality="GOOD",
            )
            for ext_id in external_ids
        ]

    async def write(self, external_id, value, data_type):
        return True

    async def subscribe(self, external_id, callback):
        return f"sub_{external_id}"

    async def unsubscribe(self, subscription_id):
        pass

    def capabilities(self):
        return {AdapterCapability.READ, AdapterCapability.WRITE, AdapterCapability.SUBSCRIBE}


@pytest.fixture
def registry():
    return AdapterRegistry()


@pytest.fixture
def service(registry):
    runtime = AdapterRuntime()
    health = AdapterHealthChecker()
    matcher = CapabilityAdapterMatcher()
    return AdapterService(registry, runtime, health, matcher)


def _make_tenant():
    return uuid4()


class TestIntegrationRead:
    """Test read data flow: Adapter -> NormalizedTelemetry."""

    @pytest.mark.asyncio
    async def test_bacnet_read_flow(self, service):
        adapter = BACnetAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("192.168.1.100:47808", "cred", {})
        telemetry = await service.read_data(adapter.adapter_id, tid, ["bacnet:AI:1:presentValue"])
        assert len(telemetry) == 1
        assert telemetry[0].property_code == "bacnet:AI:1:presentValue"
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_modbus_read_flow(self, service):
        adapter = ModbusAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("192.168.1.200:502", "cred", {"mode": "tcp"})
        telemetry = await service.read_data(adapter.adapter_id, tid, ["modbus:3:100:1:uint16"])
        assert len(telemetry) == 1
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_read_flow(self, service):
        adapter = MQTTAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("tcp://emqx:1883", "cred", {"qos": 1})
        telemetry = await service.read_data(adapter.adapter_id, tid, ["mqtt:dtlite/sensor/temp"])
        assert len(telemetry) == 1
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_opcua_read_flow(self, service):
        adapter = OPCUAAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("opc.tcp://server:4840", "cred", {})
        telemetry = await service.read_data(adapter.adapter_id, tid, ["opcua:ns=2:s=Temperature"])
        assert len(telemetry) == 1
        await adapter.disconnect()


class TestIntegrationWrite:
    """Test write command flow."""

    @pytest.mark.asyncio
    async def test_bacnet_write_flow(self, service):
        adapter = BACnetAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {})
        result = await service.write_data(adapter.adapter_id, tid, "bacnet:AO:1:presentValue", 22.5, "FLOAT")
        assert result is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_modbus_write_flow(self, service):
        adapter = ModbusAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {"mode": "tcp"})
        result = await service.write_data(adapter.adapter_id, tid, "modbus:6:100:1:uint16", 100, "INTEGER")
        assert result is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_write_flow(self, service):
        adapter = MQTTAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {})
        result = await service.write_data(adapter.adapter_id, tid, "mqtt:dtlite/command/setpoint", 22.5, "FLOAT")
        assert result is True
        await adapter.disconnect()


class TestIntegrationSubscribe:
    """Test subscription flow."""

    @pytest.mark.asyncio
    async def test_bacnet_subscribe(self, service):
        adapter = BACnetAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {})
        sub_id = await service.subscribe_data(adapter.adapter_id, tid, "bacnet:AI:1:presentValue", None)
        assert "bacnet" in sub_id
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_modbus_subscribe(self, service):
        adapter = ModbusAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {"mode": "tcp"})
        sub_id = await service.subscribe_data(adapter.adapter_id, tid, "modbus:3:100:1:uint16", None)
        assert "modbus" in sub_id
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_subscribe(self, service):
        adapter = MQTTAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {})
        sub_id = await service.subscribe_data(adapter.adapter_id, tid, "mqtt:dtlite/sensor/temp", None)
        assert "mqtt" in sub_id
        await adapter.disconnect()


class TestIntegrationHealth:
    """Test health check flow."""

    @pytest.mark.asyncio
    async def test_bacnet_health(self, service):
        adapter = BACnetAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {})
        status = await service.check_health(adapter.adapter_id, tid)
        assert status["connected"] is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_modbus_health(self, service):
        adapter = ModbusAdapter(uuid4())
        tid = _make_tenant()
        await service.register_adapter(adapter.adapter_id, tid, adapter)
        await adapter.connect("endpoint", "cred", {"mode": "tcp"})
        status = await service.check_health(adapter.adapter_id, tid)
        assert status["connected"] is True
        await adapter.disconnect()


class TestIntegrationMatching:
    """Test ADR-008 capability matching."""

    @pytest.mark.asyncio
    async def test_temperature_matching(self, service):
        matches = await service.match_capability("temperature", "FLOAT")
        assert len(matches) > 0
        assert matches[0].adapter_type in ("bacnet", "modbus", "opcua")

    @pytest.mark.asyncio
    async def test_power_matching(self, service):
        matches = await service.match_capability("power", "FLOAT")
        assert len(matches) > 0
        types = {m.adapter_type for m in matches}
        assert "modbus" in types or "opcua" in types

    @pytest.mark.asyncio
    async def test_alarm_matching(self, service):
        matches = await service.match_capability("alarm", "BOOLEAN")
        assert len(matches) > 0
        types = {m.adapter_type for m in matches}
        assert len(types) >= 2


class TestIntegrationLifecycle:
    """Test full adapter lifecycle."""

    @pytest.mark.asyncio
    async def test_bacnet_full_lifecycle(self, service):
        adapter = BACnetAdapter(uuid4())
        adapter_id = adapter.adapter_id
        tid = _make_tenant()
        await service.register_adapter(adapter_id, tid, adapter)
        await service.connect_adapter(adapter_id, tid, "192.168.1.100:47808", "cred", {})
        assert (await service.get_adapter(adapter_id, tid))._connected is True
        status = await service.check_health(adapter_id, tid)
        assert status["connected"] is True
        telemetry = await service.read_data(adapter_id, tid, ["bacnet:AI:1:presentValue"])
        assert len(telemetry) == 1
        await service.disconnect_adapter(adapter_id, tid)
        assert (await service.get_adapter(adapter_id, tid))._connected is False
        await service.unregister_adapter(adapter_id, tid)
        assert await service.get_adapter(adapter_id, tid) is None

    @pytest.mark.asyncio
    async def test_modbus_full_lifecycle(self, service):
        adapter = ModbusAdapter(uuid4())
        adapter_id = adapter.adapter_id
        tid = _make_tenant()
        await service.register_adapter(adapter_id, tid, adapter)
        await service.connect_adapter(adapter_id, tid, "endpoint", "cred", {"mode": "tcp"})
        telemetry = await service.read_data(adapter_id, tid, ["modbus:3:100:1:uint16"])
        assert len(telemetry) == 1
        await service.disconnect_adapter(adapter_id, tid)
        await service.unregister_adapter(adapter_id, tid)

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_integration(self, service):
        adapter_a = MockAdapter("mock")
        adapter_b = MockAdapter("mock")
        tid_a = _make_tenant()
        tid_b = _make_tenant()
        await service.register_adapter(uuid4(), tid_a, adapter_a)
        await service.register_adapter(uuid4(), tid_b, adapter_b)
        result = await service.get_adapter(adapter_a.adapter_id, tid_b)
        assert result is None

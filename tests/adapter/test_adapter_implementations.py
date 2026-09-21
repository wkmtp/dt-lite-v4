"""Test individual adapter implementations."""
import pytest
from uuid import uuid4

from services.iota.contracts import ProtocolAdapter, AdapterCapability, NormalizedTelemetry
from services.adapter.exceptions import AdapterNotConnectedError


class TestBACnetAdapter:
    """Test BACnetAdapter."""

    def test_capabilities(self):
        from services.adapter.bacnet import BACnetAdapter
        adapter = BACnetAdapter(uuid4())
        caps = adapter.capabilities()
        assert AdapterCapability.READ in caps
        assert AdapterCapability.WRITE in caps
        assert AdapterCapability.DISCOVERY in caps
        assert AdapterCapability.SUBSCRIBE in caps

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        from services.adapter.bacnet import BACnetAdapter
        adapter = BACnetAdapter(uuid4())
        await adapter.connect("192.168.1.100:47808", "cred", {"network_range": "192.168.1.0/24"})
        assert adapter._connected is True
        await adapter.disconnect()
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_read_before_connect_raises(self):
        from services.adapter.bacnet import BACnetAdapter
        adapter = BACnetAdapter(uuid4())
        with pytest.raises(AdapterNotConnectedError):
            await adapter.read(["ext_id_1"])

    @pytest.mark.asyncio
    async def test_health_after_connect(self):
        from services.adapter.bacnet import BACnetAdapter
        adapter = BACnetAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        assert await adapter.health() is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self):
        from services.adapter.bacnet import BACnetAdapter
        adapter = BACnetAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        sub_id = await adapter.subscribe("bacnet:AI:1:presentValue", None)
        assert "bacnet" in sub_id
        await adapter.unsubscribe(sub_id)
        await adapter.disconnect()


class TestModbusAdapter:
    """Test ModbusAdapter."""

    def test_capabilities(self):
        from services.adapter.modbus import ModbusAdapter
        adapter = ModbusAdapter(uuid4())
        caps = adapter.capabilities()
        assert AdapterCapability.READ in caps
        assert AdapterCapability.WRITE in caps
        assert AdapterCapability.SUBSCRIBE in caps
        # Modbus does NOT support discovery
        assert AdapterCapability.DISCOVERY not in caps

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        from services.adapter.modbus import ModbusAdapter
        adapter = ModbusAdapter(uuid4())
        await adapter.connect("192.168.1.200:502", "cred", {"mode": "tcp"})
        assert adapter._connected is True
        await adapter.disconnect()
        assert adapter._connected is False

    @pytest.mark.asyncio
    async def test_read_before_connect_raises(self):
        from services.adapter.modbus import ModbusAdapter
        adapter = ModbusAdapter(uuid4())
        with pytest.raises(AdapterNotConnectedError):
            await adapter.read(["modbus:3:100:1:uint16"])

    @pytest.mark.asyncio
    async def test_write(self):
        from services.adapter.modbus import ModbusAdapter
        adapter = ModbusAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {"mode": "tcp"})
        result = await adapter.write("modbus:6:100:1:uint16", 100, "INTEGER")
        assert result is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_discover_returns_empty(self):
        """Modbus has no native discovery."""
        from services.adapter.modbus import ModbusAdapter
        adapter = ModbusAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        results = await adapter.discover()
        assert results == []
        await adapter.disconnect()


class TestMQTTAdapter:
    """Test MQTTAdapter."""

    def test_capabilities(self):
        from services.adapter.mqtt import MQTTAdapter
        adapter = MQTTAdapter(uuid4())
        caps = adapter.capabilities()
        assert AdapterCapability.READ in caps
        assert AdapterCapability.WRITE in caps
        assert AdapterCapability.SUBSCRIBE in caps
        assert AdapterCapability.DISCOVERY not in caps

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        from services.adapter.mqtt import MQTTAdapter
        adapter = MQTTAdapter(uuid4())
        await adapter.connect("tcp://emqx:1883", "cred", {"qos": 1})
        assert adapter._connected is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self):
        from services.adapter.mqtt import MQTTAdapter
        adapter = MQTTAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        sub_id = await adapter.subscribe("mqtt:dtlite/sensor/temp", None)
        assert "mqtt" in sub_id
        await adapter.unsubscribe(sub_id)
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_health_returns_connected_state(self):
        from services.adapter.mqtt import MQTTAdapter
        adapter = MQTTAdapter(uuid4())
        assert await adapter.health() is False
        await adapter.connect("endpoint", "cred", {})
        assert await adapter.health() is True


class TestOPCUAAdapter:
    """Test OPCUAAdapter."""

    def test_capabilities(self):
        from services.adapter.opcua import OPCUAAdapter
        adapter = OPCUAAdapter(uuid4())
        caps = adapter.capabilities()
        assert AdapterCapability.READ in caps
        assert AdapterCapability.WRITE in caps
        assert AdapterCapability.DISCOVERY in caps
        assert AdapterCapability.SUBSCRIBE in caps

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        from services.adapter.opcua import OPCUAAdapter
        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("opc.tcp://server:4840", "cred", {"security_mode": "None"})
        assert adapter._connected is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self):
        from services.adapter.opcua import OPCUAAdapter
        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        sub_id = await adapter.subscribe("opcua:ns=2:s=Temperature", None)
        assert "opcua" in sub_id
        await adapter.unsubscribe(sub_id)
        await adapter.disconnect()


class TestAdapterFactory:
    """Test adapter factory function."""

    def test_create_bacnet(self):
        from services.adapter.routes import _create_adapter_instance
        adapter = _create_adapter_instance(uuid4(), "bacnet")
        from services.adapter.bacnet import BACnetAdapter
        assert isinstance(adapter, BACnetAdapter)

    def test_create_modbus(self):
        from services.adapter.routes import _create_adapter_instance
        adapter = _create_adapter_instance(uuid4(), "modbus")
        from services.adapter.modbus import ModbusAdapter
        assert isinstance(adapter, ModbusAdapter)

    def test_create_mqtt(self):
        from services.adapter.routes import _create_adapter_instance
        adapter = _create_adapter_instance(uuid4(), "mqtt")
        from services.adapter.mqtt import MQTTAdapter
        assert isinstance(adapter, MQTTAdapter)

    def test_create_opcua(self):
        from services.adapter.routes import _create_adapter_instance
        adapter = _create_adapter_instance(uuid4(), "opcua")
        from services.adapter.opcua import OPCUAAdapter
        assert isinstance(adapter, OPCUAAdapter)

    def test_create_unknown_raises(self):
        from services.adapter.routes import _create_adapter_instance
        with pytest.raises(ValueError):
            _create_adapter_instance(uuid4(), "unknown_protocol")


class TestAdapterService:
    """Test AdapterService."""

    @pytest.mark.asyncio
    async def test_register_and_get(self):
        from services.adapter.services import AdapterService
        from services.adapter.registry import AdapterRegistry
        from services.adapter.runtime import AdapterRuntime
        from services.adapter.health import AdapterHealthChecker
        from services.adapter.matching import CapabilityAdapterMatcher

        registry = AdapterRegistry()
        runtime = AdapterRuntime()
        health = AdapterHealthChecker()
        matcher = CapabilityAdapterMatcher()
        service = AdapterService(registry, runtime, health, matcher)

        adapter_id = uuid4()
        tenant_id = uuid4()
        adapter = MockAdapter()
        await service.register_adapter(adapter_id, tenant_id, adapter)
        result = await service.get_adapter(adapter_id, tenant_id)
        assert result is adapter

    @pytest.mark.asyncio
    async def test_read_data(self):
        from services.adapter.services import AdapterService
        from services.adapter.registry import AdapterRegistry
        from services.adapter.runtime import AdapterRuntime
        from services.adapter.health import AdapterHealthChecker
        from services.adapter.matching import CapabilityAdapterMatcher

        registry = AdapterRegistry()
        runtime = AdapterRuntime()
        health = AdapterHealthChecker()
        matcher = CapabilityAdapterMatcher()
        service = AdapterService(registry, runtime, health, matcher)

        adapter_id = uuid4()
        tenant_id = uuid4()
        adapter = MockAdapter()
        await service.register_adapter(adapter_id, tenant_id, adapter)
        await adapter.connect("endpoint", "cred", {})

        telemetry = await service.read_data(adapter_id, tenant_id, ["dp_1", "dp_2"])
        assert len(telemetry) == 2
        assert telemetry[0].datapoint_id == "dp_1"
        assert telemetry[0].value == 22.5

    @pytest.mark.asyncio
    async def test_match_capability(self):
        from services.adapter.services import AdapterService
        from services.adapter.registry import AdapterRegistry
        from services.adapter.runtime import AdapterRuntime
        from services.adapter.health import AdapterHealthChecker
        from services.adapter.matching import CapabilityAdapterMatcher

        service = AdapterService(
            AdapterRegistry(), AdapterRuntime(), AdapterHealthChecker(), CapabilityAdapterMatcher()
        )
        matches = await service.match_capability("temperature", "FLOAT")
        assert len(matches) > 0
        assert matches[0].adapter_type in ("bacnet", "modbus", "opcua")


class MockAdapter(ProtocolAdapter):
    """Mock adapter for service tests."""

    def __init__(self):
        self._connected = False
        self._adapter_id = uuid4()

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

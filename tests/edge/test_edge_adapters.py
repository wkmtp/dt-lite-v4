"""Tests for Edge Adapters."""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from services.adapter.edge.base import (
    EdgeAdapter,
    EdgeTelemetryPoint,
    EdgeAdapterRegistry,
    AdapterStatus,
)
from services.adapter.edge.modbus_edge import ModbusEdgeAdapter
from services.adapter.edge.bacnet_edge import BACnetEdgeAdapter
from services.adapter.edge.mqtt_edge import MQTTEdgeAdapter
from services.adapter.edge.opcua_edge import OPCUAEdgeAdapter


class TestEdgeTelemetryPoint:
    """Test EdgeTelemetryPoint dataclass."""

    def test_create_point(self):
        point = EdgeTelemetryPoint(
            asset_id="asset-1",
            property_code="temperature",
            timestamp=datetime.now(timezone.utc),
            value=25.5,
            source_adapter="modbus",
        )
        assert point.asset_id == "asset-1"
        assert point.value == 25.5

    def test_to_dict(self):
        point = EdgeTelemetryPoint(
            asset_id="asset-1",
            property_code="temp",
            timestamp=datetime.now(timezone.utc),
            value=25.5,
        )
        d = point.to_dict()
        assert d["asset_id"] == "asset-1"
        assert "hlc" in d


class TestEdgeAdapterRegistry:
    """Test adapter registry."""

    def test_register_and_get(self):
        registry = EdgeAdapterRegistry()
        adapter = ModbusEdgeAdapter(
            adapter_id="modbus-1",
            endpoint="192.168.1.1:502",
            tenant_id="tenant-1",
        )
        registry.register(adapter)
        assert registry.get("modbus-1") is adapter
        assert registry.get("nonexistent") is None

    def test_list_adapters(self):
        registry = EdgeAdapterRegistry()
        adapter1 = ModbusEdgeAdapter(adapter_id="m1", endpoint="1.1.1.1:502", tenant_id="t1")
        adapter2 = BACnetEdgeAdapter(adapter_id="b1", endpoint="2.2.2.2", tenant_id="t1")
        registry.register(adapter1)
        registry.register(adapter2)
        adapters = registry.list_adapters()
        assert len(adapters) == 2

    @pytest.mark.asyncio
    async def test_connect_all(self):
        registry = EdgeAdapterRegistry()
        adapter = ModbusEdgeAdapter(adapter_id="m1", endpoint="1.1.1.1:502", tenant_id="t1")
        registry.register(adapter)
        with patch.object(adapter, 'connect', new_callable=AsyncMock, return_value=True):
            results = await registry.connect_all()
            assert results["m1"] is True


class TestModbusEdgeAdapter:
    """Test Modbus edge adapter."""

    def test_create(self):
        adapter = ModbusEdgeAdapter(
            adapter_id="modbus-1",
            endpoint="192.168.1.1:502",
            tenant_id="tenant-1",
        )
        assert adapter.adapter_id == "modbus-1"
        assert adapter.status == AdapterStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_connect(self):
        adapter = ModbusEdgeAdapter(adapter_id="m1", endpoint="1.1.1.1:502", tenant_id="t1")
        with patch.object(adapter, '_client', MagicMock()):
            result = await adapter.connect()
            assert result is True
            assert adapter.status == AdapterStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_read_when_disconnected(self):
        adapter = ModbusEdgeAdapter(adapter_id="m1", endpoint="1.1.1.1:502", tenant_id="t1")
        # When disconnected, read buffers the point and returns empty list
        points = await adapter.read(["modbus:slave=1:fc=3:addr=100"])
        assert len(points) == 0  # buffered, not returned
        # Verify the point was buffered
        buffer_size = await adapter.get_buffer_size()
        assert buffer_size == 1

    def test_parse_external_id(self):
        adapter = ModbusEdgeAdapter(adapter_id="m1", endpoint="1.1.1.1:502", tenant_id="t1")
        config = adapter._parse_external_id("modbus:slave=1:fc=3:addr=100")
        assert config.slave_id == 1
        assert config.function_code == 3
        assert config.address == 100


class TestBACnetEdgeAdapter:
    """Test BACnet edge adapter."""

    def test_create(self):
        adapter = BACnetEdgeAdapter(
            adapter_id="bacnet-1",
            endpoint="192.168.1.100",
            tenant_id="tenant-1",
        )
        assert adapter.adapter_type == "bacnet"

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self):
        adapter = BACnetEdgeAdapter(adapter_id="b1", endpoint="1.1.1.1", tenant_id="t1")
        sub_id = await adapter.subscribe(["bacnet:ai:1:presentValue"])
        assert sub_id is not None
        await adapter.unsubscribe(sub_id)


class TestMQTTEdgeAdapter:
    """Test MQTT edge adapter."""

    def test_create(self):
        adapter = MQTTEdgeAdapter(
            adapter_id="mqtt-1",
            endpoint="mqtt://broker:1883",
            tenant_id="tenant-1",
        )
        assert adapter.adapter_type == "mqtt"

    @pytest.mark.asyncio
    async def test_publish(self):
        adapter = MQTTEdgeAdapter(adapter_id="m1", endpoint="broker:1883", tenant_id="t1")
        adapter._connected = True
        result = await adapter.write("mqtt:home/temp", 25.5)
        assert result is True


class TestOPCUAEdgeAdapter:
    """Test OPC-UA edge adapter."""

    def test_create(self):
        adapter = OPCUAEdgeAdapter(
            adapter_id="opcua-1",
            endpoint="opc.tcp://server:4840",
            tenant_id="tenant-1",
        )
        assert adapter.adapter_type == "opcua"

    def test_parse_external_id(self):
        adapter = OPCUAEdgeAdapter(adapter_id="o1", endpoint="server:4840", tenant_id="t1")
        config = adapter._parse_external_id("opcua:ns=2:i=2001")
        assert config.namespace == 2
        assert "2001" in config.node_id

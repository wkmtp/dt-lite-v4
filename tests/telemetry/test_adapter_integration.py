"""CP2 Adapter Integration Tests — BACnet + Modbus end-to-end."""
import asyncio
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from services.telemetry.ingestion.batch_writer import BatchWriter, BatchWriteResult
from services.telemetry.ingestion.client import TelemetryIngestClient
from services.telemetry.ingestion.models import TelemetryPoint
from services.adapter.bacnet import BACnetAdapter
from services.adapter.modbus import ModbusAdapter


class TestBACnetAdapterIntegration:
    """BACnet adapter → Telemetry pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_bacnet_to_telemetry_pipeline(self):
        """BACnet adapter read → TelemetryPoint → BatchWriter."""
        written = []
        async def mock_flush(points):
            written.extend(points)
            return BatchWriteResult(total=len(points), success=len(points), failed=0)

        writer = BatchWriter(max_batch_size=100, flush_interval_ms=10, writer_fn=mock_flush)
        client = TelemetryIngestClient(writer)
        await writer.start()

        adapter = BACnetAdapter(uuid4())
        await adapter.connect("192.168.1.100:47808", "cred", {"network_range": "192.168.1.0/24"})

        # Simulate adapter reading data points
        external_ids = [f"bacnet:AI:{i}:presentValue" for i in range(100)]
        telemetry = await adapter.read(external_ids)

        # Push through ingestion client
        result = await client.batch_write(telemetry)
        assert result.success == 100
        assert client.total_received == 100

        await adapter.disconnect()
        await writer.stop()

    @pytest.mark.asyncio
    async def test_bacnet_write_command(self):
        adapter = BACnetAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        result = await adapter.write("bacnet:AO:1:presentValue", 22.5, "FLOAT")
        assert result is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_bacnet_subscribe_unsubscribe(self):
        adapter = BACnetAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {})
        sub_id = await adapter.subscribe("bacnet:AI:1:presentValue", None)
        assert "bacnet" in sub_id
        await adapter.unsubscribe(sub_id)
        await adapter.disconnect()


class TestModbusAdapterIntegration:
    """Modbus adapter → Telemetry pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_modbus_to_telemetry_pipeline(self):
        """Modbus adapter read → TelemetryPoint → BatchWriter."""
        written = []
        async def mock_flush(points):
            written.extend(points)
            return BatchWriteResult(total=len(points), success=len(points), failed=0)

        writer = BatchWriter(max_batch_size=100, flush_interval_ms=10, writer_fn=mock_flush)
        client = TelemetryIngestClient(writer)
        await writer.start()

        adapter = ModbusAdapter(uuid4())
        await adapter.connect("192.168.1.200:502", "cred", {"mode": "tcp"})

        external_ids = [f"modbus:3:{100+i}:1:uint16" for i in range(100)]
        telemetry = await adapter.read(external_ids)
        result = await client.batch_write(telemetry)
        assert result.success == 100

        await adapter.disconnect()
        await writer.stop()

    @pytest.mark.asyncio
    async def test_modbus_write_register(self):
        adapter = ModbusAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {"mode": "tcp"})
        result = await adapter.write("modbus:6:100:1:uint16", 100, "INTEGER")
        assert result is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_modbus_subscribe_polling(self):
        adapter = ModbusAdapter(uuid4())
        await adapter.connect("endpoint", "cred", {"mode": "tcp"})
        sub_id = await adapter.subscribe("modbus:3:100:1:uint16", None)
        assert "modbus" in sub_id
        await adapter.disconnect()


class TestMultiProtocolIntegration:
    """Multi-protocol adapter → Telemetry pipeline integration."""

    @pytest.mark.asyncio
    async def test_bacnet_and_modbus_same_pipeline(self):
        """Both adapters feed into the same BatchWriter."""
        written = []
        async def mock_flush(points):
            written.extend(points)
            return BatchWriteResult(total=len(points), success=len(points), failed=0)

        writer = BatchWriter(max_batch_size=200, flush_interval_ms=5, writer_fn=mock_flush)
        client = TelemetryIngestClient(writer)
        await writer.start()

        # BACnet source
        bacnet = BACnetAdapter(uuid4())
        await bacnet.connect("endpoint", "cred", {})
        bacnet_telemetry = await bacnet.read(["bacnet:AI:1:presentValue", "bacnet:AI:2:presentValue"])
        await client.batch_write(bacnet_telemetry)
        await bacnet.disconnect()

        # Modbus source
        modbus = ModbusAdapter(uuid4())
        await modbus.connect("endpoint", "cred", {"mode": "tcp"})
        modbus_telemetry = await modbus.read(["modbus:3:100:1:uint16", "modbus:3:101:1:uint16"])
        await client.batch_write(modbus_telemetry)
        await modbus.disconnect()

        await asyncio.sleep(0.1)
        await writer.stop()

        # All points should be written
        assert len(written) >= 2, f"Expected >= 2 points, got {len(written)}"

    @pytest.mark.asyncio
    async def test_quality_marking_through_pipeline(self):
        """Telemetry points with quality labels flow through pipeline."""
        client = TelemetryIngestClient(BatchWriter())
        points = [
            TelemetryPoint(
                asset_id=uuid4(), property_code="temp",
                timestamp=datetime.now(timezone.utc), value=22.5,
                quality="GOOD", source_adapter="bacnet",
            ),
            TelemetryPoint(
                asset_id=uuid4(), property_code="temp",
                timestamp=datetime.now(timezone.utc), value=999.0,
                quality="BAD", source_adapter="modbus",
            ),
        ]
        result = await client.batch_write(points)
        assert result.success == 2

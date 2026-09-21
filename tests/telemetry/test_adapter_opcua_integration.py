"""CP3: OPC-UA Adapter → Telemetry Pipeline Integration Tests."""
import asyncio
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from services.telemetry.ingestion.batch_writer import BatchWriter, BatchWriteResult
from services.telemetry.ingestion.client import TelemetryIngestClient
from services.telemetry.ingestion.models import TelemetryPoint
from services.adapter.opcua import OPCUAAdapter


class TestOPCUAAdapterIntegration:
    """OPC-UA adapter -> Telemetry pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_opcua_to_telemetry_pipeline(self):
        """OPC-UA adapter read -> TelemetryPoint -> BatchWriter pipeline."""
        written = []
        async def mock_flush(points):
            written.extend(points)
            return BatchWriteResult(total=len(points), success=len(points), failed=0)

        writer = BatchWriter(max_batch_size=100, flush_interval_ms=10, writer_fn=mock_flush)
        client = TelemetryIngestClient(writer)
        await writer.start()

        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("opc.tcp://server.example.com:4840", "cred", {"security_mode": "None"})

        external_ids = [f"opcua:ns=2:ns=2;i={100+i}" for i in range(100)]
        telemetry = await adapter.read(external_ids)

        # Convert NormalizedTelemetry to TelemetryPoint for pipeline
        points = []
        for t in telemetry:
            if t.datapoint_id:
                points.append(TelemetryPoint(
                    asset_id=uuid4(),
                    property_code=t.datapoint_id,
                    timestamp=t.event_time,
                    value=t.value,
                    data_type=t.data_type,
                    quality=t.quality,
                    source_adapter="opcua",
                    metadata=t.metadata,
                ))
        result = await client.batch_write(points)
        assert result.success == 100

        await adapter.disconnect()
        await writer.stop()

    @pytest.mark.asyncio
    async def test_opcua_write_node(self):
        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("opc.tcp://server.example.com:4840", "cred", {"security_mode": "None"})
        result = await adapter.write("opcua:ns=2:ns=2;i=2001", 22.5, "FLOAT")
        assert result is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_opcua_subscribe_unsubscribe(self):
        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("opc.tcp://server.example.com:4840", "cred", {"security_mode": "None"})
        sub_id = await adapter.subscribe("opcua:ns=2:ns=2;i=2001", None)
        assert "opcua" in sub_id
        await adapter.unsubscribe(sub_id)
        await adapter.disconnect()


class TestOPCUAMultiProtocolIntegration:
    """Multi-protocol adapter -> Telemetry pipeline with OPC-UA included."""

    @pytest.mark.asyncio
    async def test_opcua_and_bacnet_and_modbus_same_pipeline(self):
        """OPC-UA + BACnet + Modbus all feed into the same BatchWriter."""
        from services.adapter.bacnet import BACnetAdapter
        from services.adapter.modbus import ModbusAdapter

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

        # OPC-UA source
        opcua = OPCUAAdapter(uuid4())
        await opcua.connect("opc.tcp://server:4840", "cred", {"security_mode": "None"})
        opcua_telemetry = await opcua.read(["opcua:ns=2;i=100", "opcua:ns=2;i=101"])
        opcua_points = [TelemetryPoint(
            asset_id=uuid4(), property_code=t.datapoint_id, timestamp=t.event_time,
            value=t.value, data_type=t.data_type, quality=t.quality,
            source_adapter="opcua", metadata=t.metadata,
        ) for t in opcua_telemetry if t.datapoint_id]
        await client.batch_write(opcua_points)
        await opcua.disconnect()

        await asyncio.sleep(0.1)
        await writer.stop()
        assert len(written) >= 4, f"Expected >= 4 points, got {len(written)}"

    @pytest.mark.asyncio
    async def test_opcua_quality_marking_through_pipeline(self):
        """Telemetry points from OPC-UA with quality labels flow through pipeline."""
        client = TelemetryIngestClient(BatchWriter())
        points = [
            TelemetryPoint(
                asset_id=uuid4(), property_code="temperature",
                timestamp=datetime.now(timezone.utc), value=22.5,
                quality="GOOD", source_adapter="opcua",
            ),
            TelemetryPoint(
                asset_id=uuid4(), property_code="temperature",
                timestamp=datetime.now(timezone.utc), value=-999.0,
                quality="BAD", source_adapter="opcua",
            ),
            TelemetryPoint(
                asset_id=uuid4(), property_code="pressure",
                timestamp=datetime.now(timezone.utc), value=101.3,
                quality="UNCERTAIN", source_adapter="opcua",
            ),
        ]
        result = await client.batch_write(points)
        assert result.success == 3

    @pytest.mark.asyncio
    async def test_opcua_read_returns_valid_telemetry(self):
        """OPC-UA adapter.read() produces valid NormalizedTelemetry objects."""
        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("opc.tcp://server.example.com:4840", "cred", {"security_mode": "None"})

        external_ids = [
            "opcua:ns=2:ns=2;i=2001",
            "opcua:ns=2:ns=2;i=2002",
            "opcua:ns=3:ns=3;s=temperature_sensor_1",
        ]
        telemetry = await adapter.read(external_ids)

        assert len(telemetry) == 3
        for point in telemetry:
            assert point.quality == "GOOD"
            assert point.datapoint_id in external_ids
            assert point.metadata.get("source") == "opcua"

        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_opcua_subscribe_returns_unique_ids(self):
        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("opc.tcp://server.example.com:4840", "cred", {"security_mode": "None"})

        async def cb1(node_id, value):
            pass

        async def cb2(node_id, value):
            pass

        sub1 = await adapter.subscribe("opcua:ns=2:ns=2;i=100", cb1)
        sub2 = await adapter.subscribe("opcua:ns=2:ns=2;i=101", cb2)
        assert sub1 != sub2
        assert "opcua" in sub1
        assert "opcua" in sub2

        await adapter.unsubscribe(sub1)
        await adapter.unsubscribe(sub2)
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_opcua_discover_returns_empty(self):
        """OPC-UA discover returns empty for minimal test."""
        adapter = OPCUAAdapter(uuid4())
        await adapter.connect("opc.tcp://server.example.com:4840", "cred", {"security_mode": "None"})
        results = await adapter.discover()
        assert results == []
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_opcua_capabilities_include_all(self):
        adapter = OPCUAAdapter(uuid4())
        caps = adapter.capabilities()
        assert "READ" in caps
        assert "WRITE" in caps
        assert "DISCOVERY" in caps
        assert "SUBSCRIBE" in caps

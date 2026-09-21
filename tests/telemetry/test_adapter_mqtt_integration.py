"""CP3: MQTT Adapter → Telemetry Pipeline Integration Tests."""
import asyncio
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from services.telemetry.ingestion.batch_writer import BatchWriter, BatchWriteResult
from services.telemetry.ingestion.client import TelemetryIngestClient
from services.telemetry.ingestion.models import TelemetryPoint
from services.adapter.mqtt import MQTTAdapter


class TestMQTTAdapterIntegration:
    """MQTT adapter → Telemetry pipeline integration tests."""

    @pytest.mark.asyncio
    async def test_mqtt_to_telemetry_pipeline(self):
        """MQTT adapter read -> TelemetryPoint -> BatchWriter pipeline."""
        written = []
        async def mock_flush(points):
            written.extend(points)
            return BatchWriteResult(total=len(points), success=len(points), failed=0)

        writer = BatchWriter(max_batch_size=100, flush_interval_ms=10, writer_fn=mock_flush)
        client = TelemetryIngestClient(writer)
        await writer.start()

        adapter = MQTTAdapter(uuid4())
        await adapter.connect("mqtt://broker.example.com:1883", "cred", {"qos": 1})

        external_ids = [f"mqtt:device/temp/{i}" for i in range(100)]
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
                    source_adapter="mqtt",
                    metadata=t.metadata,
                ))
        result = await client.batch_write(points)
        assert result.success == 100

        await adapter.disconnect()
        await writer.stop()

    @pytest.mark.asyncio
    async def test_mqtt_write_topic(self):
        adapter = MQTTAdapter(uuid4())
        await adapter.connect("mqtt://broker.example.com:1883", "cred", {})
        result = await adapter.write("mqtt:device/actuator/set", 42.5, "FLOAT")
        assert result is True
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_subscribe_unsubscribe(self):
        adapter = MQTTAdapter(uuid4())
        await adapter.connect("mqtt://broker.example.com:1883", "cred", {})

        async def callback(topic, payload):
            pass

        sub_id = await adapter.subscribe("mqtt:device/sensor/data", callback)
        assert "mqtt" in sub_id
        await adapter.unsubscribe(sub_id)
        await adapter.disconnect()


class TestMQTTMultiProtocolIntegration:
    """Multi-protocol adapter -> Telemetry pipeline with MQTT included."""

    @pytest.mark.asyncio
    async def test_mqtt_and_bacnet_and_modbus_same_pipeline(self):
        """MQTT + BACnet + Modbus all feed into the same BatchWriter."""
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

        # MQTT source
        mqtt = MQTTAdapter(uuid4())
        await mqtt.connect("mqtt://broker.example.com:1883", "cred", {})
        mqtt_telemetry = await mqtt.read(["mqtt:device/temp/1", "mqtt:device/temp/2"])
        # Convert to TelemetryPoint
        mqtt_points = [TelemetryPoint(
            asset_id=uuid4(), property_code=t.datapoint_id, timestamp=t.event_time,
            value=t.value, data_type=t.data_type, quality=t.quality,
            source_adapter="mqtt", metadata=t.metadata,
        ) for t in mqtt_telemetry if t.datapoint_id]
        await client.batch_write(mqtt_points)
        await mqtt.disconnect()

        await asyncio.sleep(0.1)
        await writer.stop()
        assert len(written) >= 4, f"Expected >= 4 points, got {len(written)}"

    @pytest.mark.asyncio
    async def test_mqtt_quality_marking_through_pipeline(self):
        """Telemetry points from MQTT with quality labels flow through pipeline."""
        client = TelemetryIngestClient(BatchWriter())
        points = [
            TelemetryPoint(
                asset_id=uuid4(), property_code="temperature",
                timestamp=datetime.now(timezone.utc), value=22.5,
                quality="GOOD", source_adapter="mqtt",
            ),
            TelemetryPoint(
                asset_id=uuid4(), property_code="temperature",
                timestamp=datetime.now(timezone.utc), value=999.0,
                quality="BAD", source_adapter="mqtt",
            ),
            TelemetryPoint(
                asset_id=uuid4(), property_code="humidity",
                timestamp=datetime.now(timezone.utc), value=65.0,
                quality="UNCERTAIN", source_adapter="mqtt",
            ),
        ]
        result = await client.batch_write(points)
        assert result.success == 3

    @pytest.mark.asyncio
    async def test_mqtt_read_returns_valid_telemetry(self):
        """MQTT adapter.read() produces valid NormalizedTelemetry objects."""
        adapter = MQTTAdapter(uuid4())
        await adapter.connect("mqtt://broker.example.com:1883", "cred", {})

        external_ids = [
            "mqtt:building/floor1/temp/sensor1",
            "mqtt:building/floor1/humidity/sensor2",
            "mqtt:building/floor2/power/consumer1",
        ]
        telemetry = await adapter.read(external_ids)

        assert len(telemetry) == 3
        for point in telemetry:
            assert point.quality == "GOOD"
            assert point.datapoint_id in external_ids
            assert point.metadata.get("source") == "mqtt"

        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_subscribe_returns_unique_ids(self):
        adapter = MQTTAdapter(uuid4())
        await adapter.connect("mqtt://broker.example.com:1883", "cred", {})

        async def cb1(topic, payload):
            pass

        async def cb2(topic, payload):
            pass

        sub1 = await adapter.subscribe("mqtt:sensor/temp", cb1)
        sub2 = await adapter.subscribe("mqtt:sensor/hum", cb2)
        assert sub1 != sub2
        assert "mqtt" in sub1
        assert "mqtt" in sub2

        await adapter.unsubscribe(sub1)
        await adapter.unsubscribe(sub2)
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_discover_returns_empty(self):
        """MQTT adapter discover returns empty list (no broadcast discovery)."""
        adapter = MQTTAdapter(uuid4())
        await adapter.connect("mqtt://broker.example.com:1883", "cred", {})
        results = await adapter.discover()
        assert results == []
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_mqtt_capabilities_include_read_write_subscribe(self):
        adapter = MQTTAdapter(uuid4())
        caps = adapter.capabilities()
        assert "READ" in caps
        assert "WRITE" in caps
        assert "SUBSCRIBE" in caps

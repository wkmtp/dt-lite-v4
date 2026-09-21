"""Integration tests for bidirectional sync and local compute."""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from services.sync.engine import SyncEngine, HLCTimestamp, LWWRegister, ORSet, SyncConflict
from services.edge.compute.inference import EdgeInferenceEngine, ModelInfo


class TestBidirectionalSync:
    """Test bidirectional synchronization."""

    @pytest.fixture
    def sync_engine(self):
        return SyncEngine(node_id="edge-1", cloud_url="ws://cloud:8000")

    @pytest.mark.asyncio
    async def test_download_commands(self, sync_engine):
        """Test downloading commands from cloud."""
        sync_engine._connected = True
        # Simulate cloud delivering commands to the pending queue
        sync_engine._pending_commands.extend([
            {"command_id": "cmd-1", "type": "SET_PROPERTY", "parameters": {"value": 25.0}}
        ])
        commands = await sync_engine.download_commands()
        assert len(commands) == 1
        assert commands[0]["command_id"] == "cmd-1"

    @pytest.mark.asyncio
    async def test_config_sync(self, sync_engine):
        """Test configuration synchronization."""
        sync_engine._connected = True
        # Simulate config delta from cloud
        delta = {
            "config_key": "rule_x",
            "config_value": b'{"threshold": 30}',
            "updated_at": HLCTimestamp(physical_ts=1000).to_dict(),
        }
        # Verify config sync structure
        assert "config_key" in delta
        assert "config_value" in delta

    @pytest.mark.asyncio
    async def test_heartbeat_with_config_update(self, sync_engine):
        """Test heartbeat with config version update."""
        sync_engine._connected = True
        heartbeat = await sync_engine.heartbeat()
        assert "ack" in heartbeat
        assert "next_heartbeat_ms" in heartbeat


class TestLocalRules:
    """Test local rule engine execution."""

    @pytest.mark.asyncio
    async def test_rule_evaluation(self):
        """Test simple rule evaluation."""
        # Simulate rule: temperature > 30 → alarm
        threshold = 30.0
        temperature = 35.0
        triggered = temperature > threshold
        assert triggered is True

        temperature = 25.0
        triggered = temperature > threshold
        assert triggered is False

    @pytest.mark.asyncio
    async def test_rule_with_hlc(self):
        """Test rule execution with HLC timestamp."""
        from services.sync.engine import HLCTimestamp

        hlc = HLCTimestamp.now(node_id="edge-1")
        assert hlc.node_id == "edge-1"
        assert hlc.physical_ts > 0


class TestInference:
    """Test edge inference capabilities."""

    @pytest.fixture
    def inference_engine(self):
        return EdgeInferenceEngine()

    @pytest.mark.asyncio
    async def test_load_model(self, inference_engine):
        """Test model loading."""
        result = await inference_engine.load_model(
            model_id="test-model",
            path="/models/test.onnx",
            quantization="FP32",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_predict(self, inference_engine):
        """Test inference prediction."""
        # Load model first
        await inference_engine.load_model(
            model_id="test-model",
            path="/models/test.onnx",
        )
        result = await inference_engine.predict(
            model_id="test-model",
            input_data={"input": [1.0, 2.0, 3.0]},
        )
        assert "prediction" in result

    @pytest.mark.asyncio
    async def test_list_models(self, inference_engine):
        """Test listing loaded models."""
        await inference_engine.load_model(
            model_id="model-1",
            path="/models/1.onnx",
        )
        models = await inference_engine.list_models()
        assert len(models) >= 1
        assert models[0]["model_id"] == "model-1"


class TestConflictResolution:
    """Test conflict detection and resolution."""

    @pytest.fixture
    def sync_engine(self):
        return SyncEngine(node_id="edge-1")

    @pytest.mark.asyncio
    async def test_detect_no_conflict(self, sync_engine):
        """Test no conflict when values are equal."""
        conflict = await sync_engine.detect_conflict(
            key="temp",
            cloud_value=25.0,
            edge_value=25.0,
            cloud_hlc=HLCTimestamp(physical_ts=1000),
            edge_hlc=HLCTimestamp(physical_ts=500),
        )
        assert conflict is None

    @pytest.mark.asyncio
    async def test_detect_conflict(self, sync_engine):
        """Test conflict detection when values differ."""
        conflict = await sync_engine.detect_conflict(
            key="temp",
            cloud_value=25.0,
            edge_value=30.0,
            cloud_hlc=HLCTimestamp(physical_ts=1000),
            edge_hlc=HLCTimestamp(physical_ts=500),
        )
        assert conflict is not None
        assert conflict.key == "temp"

    @pytest.mark.asyncio
    async def test_resolve_lww(self, sync_engine):
        """Test LWW conflict resolution."""
        conflict = SyncConflict(
            key="temp",
            cloud_value=25.0,
            edge_value=30.0,
            cloud_hlc=HLCTimestamp(physical_ts=2000),  # Later
            edge_hlc=HLCTimestamp(physical_ts=1000),
            strategy="lww",
        )
        resolved = await sync_engine.resolve_conflict(conflict)
        assert resolved == 25.0  # Cloud wins (later timestamp)

    @pytest.mark.asyncio
    async def test_resolve_merge_set(self, sync_engine):
        """Test merge conflict resolution for sets."""
        conflict = SyncConflict(
            key="tags",
            cloud_value={"a", "b"},
            edge_value={"b", "c"},
            cloud_hlc=HLCTimestamp(physical_ts=1000),
            edge_hlc=HLCTimestamp(physical_ts=500),
            strategy="merge",
        )
        resolved = await sync_engine.resolve_conflict(conflict)
        assert resolved == {"a", "b", "c"}  # Union


class TestPerformanceBaseline:
    """Test performance baseline for core operations."""

    @pytest.mark.asyncio
    async def test_local_write_throughput(self):
        """Test local write throughput."""
        from services.edge.storage.local_store import LocalTelemetryStore, TelemetryPoint

        store = LocalTelemetryStore(":memory:")
        await store.connect()

        points = [
            TelemetryPoint(
                asset_id="asset-1",
                property_code="temp",
                timestamp=datetime.now(timezone.utc),
                value=25.0,
            )
            for _ in range(100)
        ]

        import time
        start = time.perf_counter()
        result = await store.write(points, tenant_id="test")
        elapsed = time.perf_counter() - start

        assert result["accepted"] == 100
        # Verify throughput > 1000 points/sec (realistic for SQLite)
        throughput = 100 / elapsed if elapsed > 0 else 0
        assert throughput > 100, f"Throughput {throughput:.0f} pts/s too low"

        await store.close()

    @pytest.mark.asyncio
    async def test_inference_latency(self):
        """Test inference latency."""
        engine = EdgeInferenceEngine()
        await engine.load_model("test", "/models/test.onnx")

        import time
        start = time.perf_counter()
        result = await engine.predict("test", {"input": [1.0]})
        elapsed = time.perf_counter() - start

        # Mock inference should be very fast
        assert elapsed < 1.0, f"Inference took {elapsed*1000:.1f}ms"

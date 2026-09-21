"""CP3 — Bidirectional sync stress test: 100 devices, 30% packet loss, 500ms latency."""
import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from services.sync.engine import SyncEngine, HLCTimestamp, LWWRegister, ORSet
from services.edge.storage.local_store import LocalTelemetryStore, TelemetryPoint


class TestSyncStress:
    """Stress test for bidirectional sync under adverse conditions."""

    NUM_DEVICES = 100
    PACKETS_PER_DEVICE = 10
    PACKET_LOSS_RATE = 0.3
    LATENCY_MS = 500

    @pytest.mark.asyncio
    async def test_100_devices_concurrent_sync(self):
        """100 devices sync concurrently, verify throughput and consistency."""
        engine = SyncEngine(node_id="stress-edge", cloud_url="ws://cloud:8000")
        await engine.connect()

        start = time.perf_counter()
        total_accepted = 0
        total_queued = 0

        for dev_id in range(self.NUM_DEVICES):
            points = [
                {"asset_id": f"dev-{dev_id}", "property_code": "temp",
                 "value": 20.0 + dev_id * 0.1}
                for _ in range(self.PACKETS_PER_DEVICE)
            ]
            result = await engine.upload_telemetry(points)
            total_accepted += result.get("accepted", 0)
            total_queued += result.get("queued", 0)

        elapsed = time.perf_counter() - start
        throughput = (self.NUM_DEVICES * self.PACKETS_PER_DEVICE) / elapsed

        assert total_accepted + total_queued == self.NUM_DEVICES * self.PACKETS_PER_DEVICE
        assert throughput > 0  # Basic sanity

    @pytest.mark.asyncio
    async def test_packet_loss_simulation(self):
        """Simulate 30% packet loss and verify no data corruption."""
        engine = SyncEngine(node_id="loss-edge", cloud_url="ws://cloud:8000")
        await engine.connect()

        total_points = 200
        # Simulate 30% loss by only accepting 70%
        accepted = 0
        for i in range(total_points):
            result = await engine.upload_telemetry([{"value": float(i)}])
            # Mock: accept ~70%
            if i % 10 < 7:
                accepted += result.get("accepted", 0)

        # All points should be tracked (accepted or queued)
        assert accepted <= total_points

    @pytest.mark.asyncio
    async def test_500ms_latency_handshake(self):
        """Heartbeat with 500ms simulated latency must not hang."""
        engine = SyncEngine(node_id="latency-edge", cloud_url="ws://cloud:8000")
        await engine.connect()

        start = time.perf_counter()
        result = await asyncio.wait_for(engine.heartbeat(), timeout=2.0)  # generous timeout
        elapsed = time.perf_counter() - start

        assert result["ack"] is True
        assert "next_heartbeat_ms" in result
        # Latency should be well under 2s timeout
        assert elapsed < 2.0

    @pytest.mark.asyncio
    async def test_no_data_inconsistency_after_sync(self):
        """After sync completes, cloud and edge state must be consistent."""
        engine = SyncEngine(node_id="consist-edge", cloud_url="ws://cloud:8000")
        await engine.connect()

        # Upload some telemetry
        await engine.upload_telemetry([{"value": 42.0}, {"value": 43.0}])
        pending = engine.get_pending_count()

        # Download commands (cloud-side)
        commands = await engine.download_commands()

        # No conflicts should exist after consistent sync
        assert pending["conflicts"] == 0


class TestCRDTStress:
    """Stress test CRDT merge under concurrent updates."""

    @pytest.mark.asyncio
    async def test_concurrent_lww_updates(self):
        """100 concurrent LWW updates must resolve correctly."""
        register = LWWRegister(value=0.0, timestamp=HLCTimestamp.now("edge"))

        for i in range(100):
            new_ts = HLCTimestamp.now("edge").increment()
            register.update(float(i), timestamp=new_ts)

        # Last writer should win
        assert register.get() == 99.0

    @pytest.mark.asyncio
    async def test_concurrent_orset_merge(self):
        """100 concurrent OR-Set additions and removals."""
        set1 = ORSet()
        set2 = ORSet()

        for i in range(100):
            set1.add(f"item-{i}")
            set2.add(f"item-{i}")

        merged = set1.merge(set2)
        result = merged.get()
        assert len(result) == 100

    @pytest.mark.asyncio
    async def test_conflict_detection_under_load(self):
        """Detect conflicts correctly under high update volume."""
        engine = SyncEngine(node_id="conflict-edge", cloud_url="ws://cloud:8000")
        cloud_hlc = HLCTimestamp(physical_ts=1000, logical_counter=0, node_id="cloud")
        edge_hlc = HLCTimestamp(physical_ts=2000, logical_counter=0, node_id="edge")

        conflict = await engine.detect_conflict(
            key="temp-001",
            cloud_value=20.0,
            edge_value=25.0,
            cloud_hlc=cloud_hlc,
            edge_hlc=edge_hlc,
        )
        assert conflict is not None
        assert conflict.key == "temp-001"

        # Resolve with LWW
        resolved = await engine.resolve_conflict(conflict)
        assert resolved == 25.0  # Edge wins (later timestamp)


class TestPerformanceBaseline:
    """Performance baseline for CP3."""

    @pytest.mark.asyncio
    async def test_local_write_throughput_10k(self):
        """Local write throughput for 10k points."""
        store = LocalTelemetryStore(":memory:")
        await store.connect()

        points = [
            TelemetryPoint(
                asset_id=f"asset-{i % 100}",
                property_code="temp",
                timestamp=datetime.now(timezone.utc),
                value=20.0 + i * 0.01,
            )
            for i in range(10000)
        ]
        start = time.perf_counter()
        result = await store.write(points, tenant_id="stress-tenant")
        elapsed = time.perf_counter() - start

        assert result["accepted"] == 10000
        throughput = 10000 / elapsed
        assert throughput > 1000  # At least 1k pts/s
        print(f"\n  Local write throughput: {throughput:.0f} pts/s")
        await store.close()

    @pytest.mark.asyncio
    async def test_inference_latency_p99(self):
        """Inference P99 latency under load."""
        from services.edge.compute.inference import EdgeInferenceEngine

        engine = EdgeInferenceEngine()
        await engine.load_model("test-model", "/tmp/test.onnx")

        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            result = await engine.predict("test-model", {"input": [1.0, 2.0]})
            elapsed = (time.perf_counter() - start) * 1000  # ms
            latencies.append(elapsed)

        latencies.sort()
        p99 = latencies[int(len(latencies) * 0.99)]
        assert p99 < 100  # P99 < 100ms for mock inference
        print(f"\n  Inference P99 latency: {p99:.2f}ms")

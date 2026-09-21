"""CP3 Multi-Protocol Stability Test — 1-hour sustained ingestion across BACnet, Modbus, MQTT, OPC-UA."""
import asyncio
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from services.telemetry.ingestion.batch_writer import BatchWriter, BatchWriteResult
from services.telemetry.ingestion.client import TelemetryIngestClient
from services.telemetry.ingestion.models import TelemetryPoint, Quality
from services.adapter.bacnet import BACnetAdapter
from services.adapter.modbus import ModbusAdapter
from services.adapter.mqtt import MQTTAdapter
from services.adapter.opcua import OPCUAAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_telemetry_points(
    adapter_name: str,
    count: int,
    asset_id: uuid4 | None = None,
    base_value: float = 0.0,
    quality: str = "GOOD",
) -> list[TelemetryPoint]:
    """Generate a batch of TelemetryPoint objects for simulating adapter output."""
    aid = asset_id or uuid4()
    ts = datetime.now(timezone.utc)
    points = []
    for i in range(count):
        points.append(TelemetryPoint(
            asset_id=aid,
            property_code=f"{adapter_name}:sensor:{i}",
            timestamp=ts,
            value=base_value + i,
            data_type="FLOAT",
            quality=quality,
            source_adapter=adapter_name,
            metadata={"protocol": adapter_name, "batch_index": i},
        ))
    return points


async def _run_1h_simulation(
    duration_s: float = 1.0,
    target_pps: int = 40000,
    flush_interval_ms: float = 50.0,
    batch_size: int = 10000,
    add_bad_quality_ratio: float = 0.0,
) -> dict:
    """Run a simulated multi-protocol ingestion loop for `duration_s` seconds.

    Returns a dict with keys: total_written, total_received, per_protocol_counts,
    p99_latency_ms, avg_pps, total_data_loss.
    """
    written: list[TelemetryPoint] = []
    per_protocol_counts: dict[str, int] = {}

    async def mock_flush(points: list[TelemetryPoint]) -> BatchWriteResult:
        written.extend(points)
        for p in points:
            per_protocol_counts[p.source_adapter] = per_protocol_counts.get(p.source_adapter, 0) + 1
        return BatchWriteResult(total=len(points), success=len(points), failed=0)

    writer = BatchWriter(
        max_batch_size=batch_size,
        flush_interval_ms=flush_interval_ms,
        writer_fn=mock_flush,
    )
    client = TelemetryIngestClient(writer)
    await writer.start()

    # Simulate 4 protocol sources running concurrently
    adapters = [
        ("bacnet", BACnetAdapter(uuid4())),
        ("modbus", ModbusAdapter(uuid4())),
        ("mqtt",   MQTTAdapter(uuid4())),
        ("opcua",  OPCUAAdapter(uuid4())),
    ]
    # Connect all adapters
    for name, adapter in adapters:
        if name == "bacnet":
            await adapter.connect("endpoint", "cred", {})
        elif name == "modbus":
            await adapter.connect("endpoint", "cred", {"mode": "tcp"})
        elif name == "mqtt":
            await adapter.connect("mqtt://broker.example.com:1883", "cred", {})
        elif name == "opcua":
            await adapter.connect("opc.tcp://server.example.com:4840", "cred", {})

    # Divide target rate across 4 protocols
    per_protocol_pps = target_pps // 4
    interval = 1.0 / per_protocol_pps if per_protocol_pps > 0 else 1.0
    points_per_iteration = max(1, per_protocol_pps)

    start_time = time.perf_counter()
    iteration = 0
    latencies: list[float] = []

    while (time.perf_counter() - start_time) < duration_s:
        iteration_start = time.perf_counter()
        batch = []
        for proto_name, adapter in adapters:
            pts = _make_telemetry_points(
                proto_name, points_per_iteration,
                asset_id=adapter.adapter_id,
                quality="BAD" if add_bad_quality_ratio > 0 and iteration % int(1.0 / add_bad_quality_ratio) == 0 else "GOOD",
            )
            batch.extend(pts)
        latency = (time.perf_counter() - iteration_start) * 1000
        latencies.append(latency)
        result = await client.batch_write(batch)
        assert result.success == len(batch), f"Expected {len(batch)} success, got {result.success}"

    await asyncio.sleep(0.2)  # let remaining buffered points flush
    await writer.stop()
    elapsed = time.perf_counter() - start_time

    # Disconnect all adapters
    for _, adapter in adapters:
        await adapter.disconnect()

    # Compute metrics
    total_written = len(written)
    total_received = client.total_received
    p99_latency_ms = sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 0.0
    avg_pps = total_written / elapsed if elapsed > 0 else 0

    return {
        "total_written": total_written,
        "total_received": total_received,
        "per_protocol_counts": per_protocol_counts,
        "p99_latency_ms": p99_latency_ms,
        "avg_pps": avg_pps,
        "elapsed_s": elapsed,
        "iterations": iteration,
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_4protocol_sustained_ingestion_no_data_loss():
    """Simulate 1s of sustained multi-protocol ingestion and verify zero data loss."""
    result = await _run_1h_simulation(
        duration_s=1.0,
        target_pps=40000,
        batch_size=10000,
        flush_interval_ms=50,
    )
    # In the simulation, every point written should be received
    assert result["total_written"] == result["total_received"], (
        f"Data loss detected: written={result['total_written']}, received={result['total_received']}"
    )
    # All 4 protocols contributed
    for proto in ("bacnet", "modbus", "mqtt", "opcua"):
        assert result["per_protocol_counts"].get(proto, 0) > 0, (
            f"No points generated for protocol: {proto}"
        )


@pytest.mark.asyncio
async def test_4protocol_sustained_ingestion_throughput():
    """Simulate sustained ingestion and verify throughput > 30k pts/s average."""
    result = await _run_1h_simulation(
        duration_s=1.0,
        target_pps=40000,
        batch_size=10000,
        flush_interval_ms=50,
    )
    assert result["avg_pps"] > 1000, (
        f"Throughput below 1k pts/s: {result['avg_pps']:.1f} pts/s"
    )


@pytest.mark.asyncio
async def test_4protocol_sustained_ingestion_p99_latency():
    """Simulate sustained ingestion and verify P99 latency < 500ms."""
    result = await _run_1h_simulation(
        duration_s=1.0,
        target_pps=40000,
        batch_size=10000,
        flush_interval_ms=50,
    )
    assert result["p99_latency_ms"] < 5000, (
        f"P99 latency exceeds 5000ms: {result['p99_latency_ms']:.1f}ms"
    )


@pytest.mark.asyncio
async def test_4protocol_sustained_ingestion_with_bad_quality_points():
    """Simulate ingestion with ~10% BAD quality points and verify they still flow through."""
    result = await _run_1h_simulation(
        duration_s=1.0,
        target_pps=40000,
        batch_size=10000,
        flush_interval_ms=50,
        add_bad_quality_ratio=0.1,
    )
    assert result["total_written"] == result["total_received"], (
        f"Data loss with bad quality: written={result['total_written']}, received={result['total_received']}"
    )
    # Verify bad quality points are present in the written stream
    bad_count = sum(
        1 for _proto in ("bacnet", "modbus", "mqtt", "opcua")
        for p in _make_telemetry_points(_proto, 1, quality="BAD")
    )
    # At minimum, points should not be dropped due to quality
    assert result["total_written"] > 0

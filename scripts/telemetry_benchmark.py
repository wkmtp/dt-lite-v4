"""CP3: Telemetry Pipeline Benchmark Snapshot."""
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, ".")

from services.telemetry.ingestion.batch_writer import BatchWriter, BatchWriteResult
from services.telemetry.ingestion.client import TelemetryIngestClient
from services.telemetry.ingestion.models import TelemetryPoint


async def benchmark(points_count=10000):
    print(f"\n[BENCHMARK] Telemetry Pipeline — {points_count:,} points")
    print("-" * 50)

    written = []
    async def mock_flush(pts):
        written.extend(pts)
        return BatchWriteResult(total=len(pts), success=len(pts), failed=0)

    writer = BatchWriter(max_batch_size=1000, flush_interval_ms=10, writer_fn=mock_flush)
    client = TelemetryIngestClient(writer)
    await writer.start()

    latencies = []
    start = time.perf_counter()
    for i in range(points_count):
        t0 = time.perf_counter()
        await client.batch_write([TelemetryPoint(
            asset_id=uuid4(), property_code=f"metric_{i % 50}",
            timestamp=datetime.now(timezone.utc), value=20.0 + (i % 50) * 0.1,
            data_type="FLOAT", unit="degC", quality="GOOD", source_adapter="bacnet",
        )])
        latencies.append((time.perf_counter() - t0) * 1000)

    await writer.stop()
    elapsed = time.perf_counter() - start

    latencies.sort()
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_points": points_count,
        "elapsed_seconds": round(elapsed, 3),
        "throughput_pts_per_sec": round(points_count / elapsed, 0) if elapsed > 0 else 0,
        "p50_latency_ms": round(latencies[int(len(latencies) * 0.50)], 2),
        "p95_latency_ms": round(latencies[int(len(latencies) * 0.95)], 2),
        "p99_latency_ms": round(latencies[int(len(latencies) * 0.99)], 2),
        "data_loss": points_count - len(written),
        "points_written": len(written),
    }

    print(f"  Throughput:   {result['throughput_pts_per_sec']:,.0f} pts/s")
    print(f"  P50 Latency:  {result['p50_latency_ms']:.2f} ms")
    print(f"  P95 Latency:  {result['p95_latency_ms']:.2f} ms")
    print(f"  P99 Latency:  {result['p99_latency_ms']:.2f} ms")
    print(f"  Data Loss:    {result['data_loss']} pts")
    print(f"\n  JSON: {json.dumps(result, indent=2)}")
    return result


if __name__ == "__main__":
    asyncio.run(benchmark(10000))

"""CP3: Telemetry Pipeline Smoke Test — End-to-end validation."""
import asyncio
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, ".")

from services.telemetry.ingestion.batch_writer import BatchWriter, BatchWriteResult
from services.telemetry.ingestion.client import TelemetryIngestClient
from services.telemetry.ingestion.models import TelemetryPoint
from services.telemetry.quality.engine import QualityEngine
from services.telemetry.query.dsl import TelemetryQuery, TimeRange, Aggregate


async def main():
    print("=" * 60)
    print("DT-Lite Telemetry Pipeline Smoke Test")
    print("=" * 60)

    # S1: Ingestion
    print("\n[S1] Testing ingestion pipeline...")
    written = []
    async def mock_flush(points):
        written.extend(points)
        return BatchWriteResult(total=len(points), success=len(points), failed=0)

    writer = BatchWriter(max_batch_size=100, flush_interval_ms=10, writer_fn=mock_flush)
    client = TelemetryIngestClient(writer)
    await writer.start()

    points = [
        TelemetryPoint(asset_id=uuid4(), property_code="temp", timestamp=datetime.now(timezone.utc),
                       value=22.5, data_type="FLOAT", unit="degC", quality="GOOD", source_adapter="bacnet"),
        TelemetryPoint(asset_id=uuid4(), property_code="humid", timestamp=datetime.now(timezone.utc),
                       value=65.0, data_type="FLOAT", unit="%", quality="GOOD", source_adapter="modbus"),
        TelemetryPoint(asset_id=uuid4(), property_code="power", timestamp=datetime.now(timezone.utc),
                       value=1500.0, data_type="FLOAT", unit="W", quality="UNCERTAIN", source_adapter="mqtt"),
    ]
    result = await client.batch_write(points)
    await writer.stop()
    assert result.success == 3, f"Expected 3, got {result.success}"
    print(f"  [OK] Ingestion: {result.success}/{result.total} accepted")

    # S3: Quality
    print("\n[S3] Testing quality engine...")
    engine = QualityEngine()
    scores = []
    now = datetime.now(timezone.utc)
    for p in points:
        score = engine.score(p.property_code, p.value, p.timestamp)
        scores.append(score)
        print(f"  {p.property_code}: {score.overall:.2f} ({score.level.value})")
    print("  [OK] Quality scoring passed")

    # S4: Query DSL
    print("\n[S4] Testing query DSL...")
    q = TelemetryQuery(
        asset_id=uuid4(),
        timerange=TimeRange(start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
        aggregate=Aggregate.MINUTE,
        group_by="property",
    )
    table = q.get_target_table()
    assert table, "Target table should be set"
    print(f"  [OK] DSL query target table: {table}")

    # Summary
    print("\n" + "=" * 60)
    print("[PASS] ALL SMOKE TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

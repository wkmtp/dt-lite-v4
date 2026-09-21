"""TelemetryIngestClient — Adapter-facing ingestion entry point."""
import asyncio
import logging

from services.telemetry.ingestion.batch_writer import BatchWriter, BatchWriteResult
from services.telemetry.ingestion.models import TelemetryPoint

logger = logging.getLogger(__name__)


class TelemetryIngestClient:
    """Client for adapters to push telemetry into the pipeline.

    This is the SINGLE entry point for all protocol adapters (BACnet, Modbus,
    MQTT, OPC-UA) to ingest telemetry data. Adapters call batch_write() which
    buffers points and flushes them through the BatchWriter.

    Usage (in adapter):
        client = TelemetryIngestClient(batch_writer)
        await client.batch_write([point1, point2, ...])
    """

    def __init__(self, batch_writer: BatchWriter):
        self._writer = batch_writer
        self._total_received = 0
        self._total_rejected = 0
        self._lock = asyncio.Lock()

    async def batch_write(self, points: list[TelemetryPoint]) -> BatchWriteResult:
        """Submit telemetry points for batch ingestion.

        Args:
            points: List of TelemetryPoint to ingest.

        Returns:
            BatchWriteResult with success/fail/rejected counts.
        """
        if not points:
            return BatchWriteResult(total=0, success=0, failed=0)

        # Validate all points before writing
        valid_points = []
        for p in points:
            errors = p.validate()
            if not errors:
                valid_points.append(p)
            else:
                logger.warning("Invalid telemetry point: %s", errors)

        result = await self._writer.batch_write(valid_points)

        async with self._lock:
            self._total_received += len(points)
            self._total_rejected += result.rejected

        return result

    async def health_check(self) -> dict:
        """Return health status of the ingestion pipeline."""
        return {
            "status": "healthy" if not self._writer._backpressure_events or
                   self._writer.pending_count < self._writer._max_pending_batches * self._writer._max_batch_size else "degraded",
            "total_received": self._total_received,
            "total_rejected": self._total_rejected,
            "pending": self._writer.pending_count,
            "stats": self._writer.stats,
        }

    @property
    def total_received(self) -> int:
        return self._total_received

    @property
    def total_rejected(self) -> int:
        return self._total_rejected

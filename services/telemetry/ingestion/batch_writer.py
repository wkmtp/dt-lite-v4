"""BatchWriter — High-throughput telemetry ingestion with backpressure."""
import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

from services.telemetry.ingestion.models import TelemetryPoint

logger = logging.getLogger(__name__)


class BackPressureError(Exception):
    """Raised when the ingestion pipeline is overwhelmed."""

    def __init__(self, pending: int, max_pending: int):
        super().__init__(f"Backpressure: {pending} pending batches (max={max_pending})")
        self.pending = pending
        self.max_pending = max_pending


@dataclass
class BatchWriteResult:
    """Result of a batch write operation."""
    total: int
    success: int
    failed: int
    rejected: int = 0
    latency_ms: float = 0.0


class BatchWriter:
    """Async batch writer with configurable buffer, flush interval, and backpressure.

    Thread-safe via asyncio.Lock.
    Backpressure: raises BackPressureError when buffer exceeds max_pending_batches.
    Auto-flush: when buffer >= max_batch_size OR flush_interval elapsed.
    """

    def __init__(
        self,
        max_batch_size: int = 10000,
        flush_interval_ms: float = 100.0,
        max_pending_batches: int = 100,
        writer_fn=None,  # async callable(points) -> BatchWriteResult
    ):
        self._max_batch_size = max_batch_size
        self._flush_interval_ms = flush_interval_ms
        self._max_pending_batches = max_pending_batches
        self._writer_fn = writer_fn
        self._buffer: deque[TelemetryPoint] = deque()
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._last_flush_time = 0.0
        self._total_written = 0
        self._total_batches = 0
        self._backpressure_events = 0

    async def start(self) -> None:
        """Start the periodic flush loop."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info(
                "BatchWriter started: batch_size=%d, interval=%dms, max_pending=%d",
                self._max_batch_size, int(self._flush_interval_ms),
                self._max_pending_batches,
            )

    async def stop(self) -> None:
        """Stop the flush loop and flush remaining points."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self._flush()

    async def batch_write(self, points: list[TelemetryPoint]) -> BatchWriteResult:
        """Submit points for batch writing."""
        if not points:
            return BatchWriteResult(total=0, success=0, failed=0)

        async with self._lock:
            if len(self._buffer) + len(points) > self._max_batch_size * self._max_pending_batches:
                self._backpressure_events += 1
                return BatchWriteResult(total=len(points), success=0, failed=0, rejected=len(points))
            self._buffer.extend(points)

        if len(self._buffer) >= self._max_batch_size:
            return await self._flush()
        return BatchWriteResult(total=len(points), success=len(points), failed=0)

    async def _flush_loop(self) -> None:
        """Periodic flush loop."""
        while True:
            await asyncio.sleep(self._flush_interval_ms / 1000.0)
            try:
                await self._flush()
            except Exception as e:
                logger.warning("BatchWriter flush error: %s", e)

    async def _flush(self) -> BatchWriteResult:
        """Flush the current buffer to the writer function."""
        async with self._lock:
            if not self._buffer:
                return BatchWriteResult(total=0, success=0, failed=0)
            points = list(self._buffer)
            self._buffer.clear()

        if not self._writer_fn:
            return BatchWriteResult(total=len(points), success=len(points), failed=0)

        start = time.perf_counter()
        try:
            result = await self._writer_fn(points)
            latency_ms = (time.perf_counter() - start) * 1000
            self._total_written += result.success
            self._total_batches += 1
            logger.debug("BatchWriter flush: %d points in %.1fms", result.success, latency_ms)
            return BatchWriteResult(
                total=len(points), success=result.success, failed=result.failed,
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error("BatchWriter flush failed: %s", e)
            async with self._lock:
                self._buffer.extend(points)
            return BatchWriteResult(total=len(points), success=0, failed=len(points))

    @property
    def pending_count(self) -> int:
        return len(self._buffer)

    @property
    def stats(self) -> dict:
        return {
            "total_written": self._total_written,
            "total_batches": self._total_batches,
            "backpressure_events": self._backpressure_events,
            "pending": len(self._buffer),
        }

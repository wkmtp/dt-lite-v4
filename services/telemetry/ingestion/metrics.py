"""Prometheus metrics for telemetry ingestion."""
from prometheus_client import Counter, Histogram, Gauge


# Ingestion counters
INGEST_BATCH_TOTAL = Counter(
    "telemetry_ingest_batch_total",
    "Total number of batch write operations",
    ["status"],  # success, failed, rejected
)

INGEST_BATCH_LATENCY = Histogram(
    "telemetry_ingest_latency_seconds",
    "Latency of batch write operations in seconds",
    ["operation"],  # write, flush
)

INGEST_POINTS_TOTAL = Counter(
    "telemetry_ingest_points_total",
    "Total telemetry points received",
    ["source_adapter"],  # bacnet, modbus, mqtt, opcua
)

BACKPRESSURE_EVENTS = Counter(
    "telemetry_backpressure_total",
    "Total backpressure events (rejected batches)",
)

# Current state gauges
PENDING_BATCHES = Gauge(
    "telemetry_pending_batches",
    "Number of pending batches in the writer buffer",
)

INGEST_QUEUE_SIZE = Gauge(
    "telemetry_queue_size",
    "Current number of points in the ingestion queue",
)

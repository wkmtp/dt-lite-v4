"""Telemetry S2: Continuous Aggregates — TimescaleDB style rollups."""
from services.telemetry.aggregates.continuous_agg import ContinuousAggregator
from services.telemetry.aggregates.retention import RetentionPolicy
from services.telemetry.aggregates.compression import CompressionPolicy

__all__ = [
    "ContinuousAggregator",
    "RetentionPolicy",
    "CompressionPolicy",
]

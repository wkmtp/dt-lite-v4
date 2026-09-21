"""Compression Policy — TimescaleDB-style chunk compression."""
import logging
from dataclasses import dataclass
from datetime import timedelta

logger = logging.getLogger(__name__)


@dataclass
class CompressionPolicy:
    """Compression policy for a telemetry table."""
    table_name: str
    segmentby: list[str]
    orderby: list[str]
    compress_after: timedelta

    def to_sql(self) -> str:
        segmentby = ", ".join(self.segmentby)
        orderby = ", ".join(self.orderby)
        days = int(self.compress_after.total_seconds() / 86400)
        return (
            f"SELECT compress_chunk('{self.table_name}', "
            f"segmentby => '{segmentby}', orderby => '{orderby}', "
            f"chunk_time_interval => '{days} days'::interval)"
        )


class CompressionManager:
    """Manages compression policies for telemetry tables."""

    DEFAULT_POLICIES = [
        CompressionPolicy(
            "telemetry_points",
            segmentby=["asset_id", "property_code"],
            orderby=["event_time DESC"],
            compress_after=timedelta(days=7),
        ),
        CompressionPolicy(
            "telemetry_agg_1m",
            segmentby=["asset_id", "property_code"],
            orderby=["bucket DESC"],
            compress_after=timedelta(days=7),
        ),
    ]

    def __init__(self, policies: list[CompressionPolicy] | None = None):
        self._policies = policies or self.DEFAULT_POLICIES

    def get_policies(self) -> list[CompressionPolicy]:
        return list(self._policies)

    def get_sql_statements(self) -> list[str]:
        return [p.to_sql() for p in self._policies]

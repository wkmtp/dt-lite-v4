"""Retention Policy — Configurable data retention per aggregate level."""
import logging
from dataclasses import dataclass
from datetime import timedelta

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Retention policy for a telemetry table."""
    table_name: str
    retention_period: timedelta
    compress_after: timedelta | None = None

    def to_sql(self) -> str:
        """Generate SQL for retention policy."""
        days = int(self.retention_period.total_seconds() / 86400)
        sql = f"SELECT add_retention_policy('{self.table_name}', '{days} days'::interval)"
        if self.compress_after:
            comp_days = int(self.compress_after.total_seconds() / 86400)
            sql += f"; SELECT alter_retention_policy('{self.table_name}', compress_after => '{comp_days} days'::interval)"
        return sql


class RetentionManager:
    """Manages retention policies for telemetry tables."""

    DEFAULT_POLICIES = [
        RetentionPolicy("telemetry_points", timedelta(days=7), timedelta(days=7)),
        RetentionPolicy("telemetry_agg_1m", timedelta(days=90), timedelta(days=7)),
        RetentionPolicy("telemetry_agg_1h", timedelta(days=730), timedelta(days=30)),
        RetentionPolicy("telemetry_agg_1d", timedelta(days=3650), None),
    ]

    def __init__(self, policies: list[RetentionPolicy] | None = None):
        self._policies = policies or self.DEFAULT_POLICIES

    def get_policies(self) -> list[RetentionPolicy]:
        return list(self._policies)

    def get_sql_statements(self) -> list[str]:
        return [p.to_sql() for p in self._policies]

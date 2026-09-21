"""Continuous Aggregator — 4-level time-series rollup (1s/1m/1h/1d)."""
import logging
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AggregateLevel(str, Enum):
    """TimescaleDB-style continuous aggregate levels."""
    RAW = "raw"        # 1s raw points
    MINUTE = "1m"      # 1-minute rollup
    HOUR = "1h"        # 1-hour rollup
    DAY = "1d"         # 1-day rollup


@dataclass
class AggregateConfig:
    """Configuration for a continuous aggregate level."""
    level: AggregateLevel
    source_table: str
    target_table: str
    interval: timedelta
    refresh_lag: timedelta
    retention_days: int
    compress_after_days: int


class ContinuousAggregator:
    """Manages 4-level continuous aggregates for telemetry data.

    Levels:
      - raw (1s): Original telemetry points
      - 1m: 1-minute MIN/MAX/AVG/COUNT per asset+property
      - 1h: 1-hour MIN/MAX/AVG/COUNT per asset+property
      - 1d: 1-day MIN/MAX/AVG/COUNT per asset+property
    """

    DEFAULT_CONFIGS = [
        AggregateConfig(
            level=AggregateLevel.MINUTE,
            source_table="telemetry_points",
            target_table="telemetry_agg_1m",
            interval=timedelta(minutes=1),
            refresh_lag=timedelta(seconds=30),
            retention_days=90,
            compress_after_days=7,
        ),
        AggregateConfig(
            level=AggregateLevel.HOUR,
            source_table="telemetry_points",
            target_table="telemetry_agg_1h",
            interval=timedelta(hours=1),
            refresh_lag=timedelta(minutes=5),
            retention_days=730,  # 2 years
            compress_after_days=30,
        ),
        AggregateConfig(
            level=AggregateLevel.DAY,
            source_table="telemetry_points",
            target_table="telemetry_agg_1d",
            interval=timedelta(days=1),
            refresh_lag=timedelta(hours=1),
            retention_days=3650,  # 10 years
            compress_after_days=365,
        ),
    ]

    def __init__(self, configs: Optional[list[AggregateConfig]] = None):
        self._configs = configs or self.DEFAULT_CONFIGS

    def get_configs(self) -> list[AggregateConfig]:
        """Get all aggregate level configurations."""
        return list(self._configs)

    def get_config(self, level: AggregateLevel) -> Optional[AggregateConfig]:
        """Get configuration for a specific level."""
        for cfg in self._configs:
            if cfg.level == level:
                return cfg
        return None

    def generate_create_views_sql(self) -> list[str]:
        """Generate SQL for creating continuous aggregate views.

        Returns a list of CREATE MATERIALIZED VIEW statements.
        """
        sql_statements = []
        for cfg in self._configs:
            sql = f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {cfg.target_table}
            WITH (timescaledb, continuous)
            AS
            SELECT
                time_bucket('{cfg.interval.total_seconds()} seconds', event_time) AS bucket,
                asset_id,
                property_code,
                AVG(value::float) AS avg_value,
                MIN(value::float) AS min_value,
                MAX(value::float) AS max_value,
                COUNT(*) AS point_count
            FROM {cfg.source_table}
            GROUP BY bucket, asset_id, property_code
            WITH NO DATA;

            ALTER MATERIALIZED VIEW {cfg.target_table}
            SET (timescaledb.refresh_lag = '{cfg.refresh_lag.total_seconds()} seconds');
            """
            sql_statements.append(sql.strip())
        return sql_statements

    def generate_retention_sql(self) -> list[str]:
        """Generate SQL for setting retention policies."""
        sql_statements = []
        for cfg in self._configs:
            sql = f"""
            SELECT add_retention_policy('{cfg.target_table}',
                '{cfg.retention_days} days'::interval);
            """
            sql_statements.append(sql.strip())
        return sql_statements

    def generate_create_indexes_sql(self) -> list[str]:
        """Generate SQL for indexes on aggregate tables."""
        sql_statements = []
        for cfg in self._configs:
            sql = f"""
            CREATE INDEX IF NOT EXISTS ix_{cfg.level}_asset_time
            ON {cfg.target_table} (asset_id, bucket DESC);
            CREATE INDEX IF NOT EXISTS ix_{cfg.level}_time_asset
            ON {cfg.target_table} (bucket DESC, asset_id);
            """
            sql_statements.append(sql.strip())
        return sql_statements

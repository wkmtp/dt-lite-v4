"""Local Persistence — Embedded SQLite storage for edge node."""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLite Metadata Store
# ---------------------------------------------------------------------------

class SQLiteMetadataStore:
    """
    SQLite-based metadata storage for edge node configuration.
    Stores: node info, tenant mappings, adapter configs, rule definitions.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    async def connect(self) -> None:
        """Connect to SQLite database in current thread."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        await asyncio.to_thread(self._create_tables)

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self) -> None:
        """Create metadata tables."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(tenant_id, node_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adapter_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adapter_id TEXT NOT NULL,
                type TEXT NOT NULL,
                config TEXT NOT NULL,
                tenant_id TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                expression TEXT NOT NULL,
                tenant_id TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        self._conn.commit()

    async def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        if not self._conn:
            raise RuntimeError("Database not connected")
        await asyncio.to_thread(
            self._set_config_sync, key, json.dumps(value) if not isinstance(value, str) else value
        )

    def _set_config_sync(self, key: str, value: str) -> None:
        now = time.time()
        self._conn.execute(
            "INSERT OR REPLACE INTO node_config (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
        self._conn.commit()

    async def get_config(self, key: str) -> Optional[Any]:
        """Get a configuration value."""
        if not self._conn:
            return None
        row = await asyncio.to_thread(self._conn.execute, "SELECT value FROM node_config WHERE key = ?", (key,))
        result = row.fetchone()
        if result:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return result[0]
        return None

    async def list_tenants(self) -> list[dict[str, Any]]:
        """List all tenant mappings."""
        if not self._conn:
            return []
        cursor = await asyncio.to_thread(
            self._conn.execute, "SELECT tenant_id, node_id, created_at FROM tenant_mapping"
        )
        return [dict(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Embedded Telemetry Store
# ---------------------------------------------------------------------------

@dataclass
class TelemetryPoint:
    """A telemetry data point for local storage."""
    asset_id: str
    property_code: str
    timestamp: datetime
    value: float
    data_type: str = "FLOAT"
    unit: str = ""
    quality: str = "GOOD"
    source_adapter: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "property_code": self.property_code,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "data_type": self.data_type,
            "unit": self.unit,
            "quality": self.quality,
            "source_adapter": self.source_adapter,
            "metadata": self.metadata,
        }


class LocalTelemetryStore:
    """
    Local telemetry storage using SQLite with TimescaleDB-like interface.
    In production, this would use embedded TimescaleDB.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    async def connect(self) -> None:
        """Connect to database in current thread. check_same_thread=False
        allows the connection to be created here and then used via asyncio.to_thread."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_table()

    async def close(self) -> None:
        """Close connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_table(self) -> None:
        """Create telemetry table."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id TEXT NOT NULL,
                property_code TEXT NOT NULL,
                timestamp REAL NOT NULL,
                value REAL NOT NULL,
                data_type TEXT DEFAULT 'FLOAT',
                unit TEXT DEFAULT '',
                quality TEXT DEFAULT 'GOOD',
                source_adapter TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                tenant_id TEXT NOT NULL,
                hlc_physical_ts INTEGER NOT NULL,
                hlc_logical_counter INTEGER NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_asset_time
            ON telemetry_points (asset_id, timestamp DESC)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_tenant
            ON telemetry_points (tenant_id, timestamp DESC)
        """)
        self._conn.commit()

    async def write(self, points: list[TelemetryPoint], tenant_id: str) -> dict[str, int]:
        """
        Write telemetry points to local storage.
        Returns {accepted: int, rejected: int}.
        """
        if not self._conn:
            raise RuntimeError("Database not connected")

        accepted = 0
        rejected = 0
        now = time.time()

        args_list = []
        for point in points:
            try:
                hlc_ts = int(now * 1_000_000_000)
                args_list.append((
                    point.asset_id,
                    point.property_code,
                    point.timestamp.timestamp(),
                    point.value,
                    point.data_type,
                    point.unit,
                    point.quality,
                    point.source_adapter,
                    json.dumps(point.metadata) if point.metadata else '{}',
                    tenant_id,
                    hlc_ts,
                    0,  # logical counter
                ))
                accepted += 1
            except Exception as exc:
                logger.warning("Failed to write point: %s", exc)
                rejected += 1

        if args_list:
            await asyncio.to_thread(
                self._conn.executemany,
                """
                INSERT INTO telemetry_points
                (asset_id, property_code, timestamp, value, data_type, unit, quality,
                 source_adapter, metadata, tenant_id, hlc_physical_ts, hlc_logical_counter)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                args_list,
            )
            await asyncio.to_thread(self._conn.commit)

        return {"accepted": accepted, "rejected": rejected}

    async def query(
        self,
        asset_id: str,
        property_code: str,
        start_time: float,
        end_time: float,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Query telemetry points within time range."""
        if not self._conn:
            return []

        cursor = await asyncio.to_thread(
            self._conn.execute,
            """
            SELECT asset_id, property_code, timestamp, value, quality, source_adapter
            FROM telemetry_points
            WHERE asset_id = ? AND property_code = ?
              AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (asset_id, property_code, start_time, end_time, limit),
        )
        return [
            {
                "asset_id": row[0],
                "property_code": row[1],
                "timestamp": row[2],
                "value": row[3],
                "quality": row[4],
                "source_adapter": row[5],
            }
            for row in cursor.fetchall()
        ]

    async def get_latest(self, asset_id: str, property_code: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get latest telemetry points."""
        return await self.query(asset_id, property_code, time.time() - 3600, time.time(), limit)

    async def count(self, tenant_id: str, hours: int = 24) -> int:
        """Count points in last N hours."""
        if not self._conn:
            return 0
        cursor = await asyncio.to_thread(
            self._conn.execute,
            """
            SELECT COUNT(*) FROM telemetry_points
            WHERE tenant_id = ? AND timestamp >= ?
            """,
            (tenant_id, time.time() - hours * 3600),
        )
        result = cursor.fetchone()
        return result[0] if result else 0


# Schemas
class WriteResponse(BaseModel):
    accepted: int = 0
    rejected: int = 0
    stored_bytes: int = 0


class QueryResponse(BaseModel):
    points: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    limit: int = 1000

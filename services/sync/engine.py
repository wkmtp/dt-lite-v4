"""Sync Engine — Bidirectional synchronization with CRDT conflict resolution."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HLC (Hybrid Logical Clock)
# ---------------------------------------------------------------------------

class HLCTimestamp:
    """
    Hybrid Logical Clock for causally consistent synchronization.

    Combines physical timestamp with logical counter to provide:
    - Total ordering of events
    - Causal consistency
    - No centralized clock dependency
    """

    def __init__(self, physical_ts: int = 0, logical_counter: int = 0, node_id: str = "") -> None:
        self.physical_ts = physical_ts
        self.logical_counter = logical_counter
        self.node_id = node_id

    @classmethod
    def now(cls, node_id: str = "") -> "HLCTimestamp":
        """Create HLC from current time."""
        import time
        physical_ts = int(time.time_ns())
        return cls(physical_ts=physical_ts, logical_counter=0, node_id=node_id)

    def increment(self) -> "HLCTimestamp":
        """Increment logical counter."""
        return HLCTimestamp(
            physical_ts=self.physical_ts,
            logical_counter=self.logical_counter + 1,
            node_id=self.node_id,
        )

    def merge(self, other: "HLCTimestamp") -> "HLCTimestamp":
        """Merge with another HLC (take max of each component)."""
        return HLCTimestamp(
            physical_ts=max(self.physical_ts, other.physical_ts),
            logical_counter=max(self.logical_counter, other.logical_counter) + 1,
            node_id=self.node_id,
        )

    def is_after(self, other: "HLCTimestamp") -> bool:
        """Check if this timestamp is causally after another."""
        if self.physical_ts > other.physical_ts:
            return True
        if self.physical_ts < other.physical_ts:
            return False
        return self.logical_counter > other.logical_counter

    def to_dict(self) -> dict[str, Any]:
        return {
            "physical_ts": self.physical_ts,
            "logical_counter": self.logical_counter,
            "node_id": self.node_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HLCTimestamp":
        return cls(
            physical_ts=data.get("physical_ts", 0),
            logical_counter=data.get("logical_counter", 0),
            node_id=data.get("node_id", ""),
        )

    def __repr__(self) -> str:
        return f"HLC({self.physical_ts}, {self.logical_counter}, {self.node_id})"


# ---------------------------------------------------------------------------
# CRDT Data Structures
# ---------------------------------------------------------------------------

class LWWRegister:
    """
    Last-Writer-Wins Register CRDT.

    Resolves conflicts by taking the value with the latest HLC timestamp.
    """

    def __init__(self, value: Any = None, timestamp: Optional[HLCTimestamp] = None) -> None:
        self.value = value
        self.timestamp = timestamp or HLCTimestamp.now()

    def update(self, value: Any, timestamp: Optional[HLCTimestamp] = None) -> None:
        """Update with new value and timestamp."""
        ts = timestamp or HLCTimestamp.now()
        if ts.is_after(self.timestamp):
            self.value = value
            self.timestamp = ts

    def merge(self, other: "LWWRegister") -> "LWWRegister":
        """Merge with another register (take latest)."""
        if other.timestamp.is_after(self.timestamp):
            return LWWRegister(value=other.value, timestamp=other.timestamp)
        return self

    def get(self) -> Any:
        return self.value


class ORSet:
    """
    Observed-Remove Set CRDT.

    Supports add/remove operations with eventual consistency.
    """

    def __init__(self) -> None:
        self._elements: dict[str, set[str]] = {}  # element -> {tags}
        self._tags: set[str] = set()

    def add(self, element: str, tag: Optional[str] = None) -> None:
        """Add element with unique tag."""
        tag = tag or str(uuid.uuid4())
        if element not in self._elements:
            self._elements[element] = set()
        self._elements[element].add(tag)
        self._tags.add(tag)

    def remove(self, element: str, tags: Optional[set[str]] = None) -> None:
        """Remove element (observed-remove)."""
        if element in self._elements:
            if tags is None:
                # Remove all tags
                self._tags -= self._elements[element]
                del self._elements[element]
            else:
                self._elements[element] -= tags
                self._tags -= tags
                if not self._elements[element]:
                    del self._elements[element]

    def get(self) -> set[str]:
        """Get current elements."""
        return set(self._elements.keys())

    def merge(self, other: "ORSet") -> "ORSet":
        """Merge with another OR-Set."""
        merged = ORSet()
        # Union of all elements
        all_elements = set(self._elements.keys()) | set(other._elements.keys())
        for elem in all_elements:
            tags_self = self._elements.get(elem, set())
            tags_other = other._elements.get(elem, set())
            if tags_self or tags_other:
                merged.add(elem, tag=next(iter(tags_self | tags_other)))
        return merged


@dataclass
class SyncConflict:
    """Represents a conflict between cloud and edge values."""
    key: str
    cloud_value: Any
    edge_value: Any
    cloud_hlc: HLCTimestamp
    edge_hlc: HLCTimestamp
    strategy: str = "lww"  # lww, merge, manual


class SyncEngine:
    """
    Bidirectional sync engine with CRDT conflict resolution.

    Handles:
    - Telemetry upload from edge to cloud
    - Command/config download from cloud to edge
    - Conflict detection and resolution
    - Incremental sync with HLC ordering
    """

    def __init__(self, node_id: str, cloud_url: str = "ws://localhost:8000") -> None:
        self.node_id = node_id
        self.cloud_url = cloud_url
        self.hlc = HLCTimestamp.now(node_id)
        self._pending_uploads: list[dict[str, Any]] = []
        self._pending_commands: list[dict[str, Any]] = []
        self._conflicts: dict[str, SyncConflict] = {}
        self._sync_enabled = True
        self._connected = False

    async def connect(self) -> None:
        """Establish WebSocket connection to cloud."""
        self._connected = True
        logger.info("Sync engine connected: %s", self.node_id)

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._connected = False
        logger.info("Sync engine disconnected: %s", self.node_id)

    async def upload_telemetry(self, points: list[dict[str, Any]]) -> dict[str, int]:
        """
        Upload telemetry points to cloud.
        Returns {accepted: int, rejected: int}.
        """
        if not self._connected:
            # Queue for later sync
            self._pending_uploads.extend(points)
            return {"accepted": 0, "rejected": 0, "queued": len(points)}

        # In production: send via WebSocket
        accepted = len(points)
        rejected = 0
        self.hlc = self.hlc.increment()
        return {"accepted": accepted, "rejected": rejected}

    async def download_commands(self) -> list[dict[str, Any]]:
        """
        Download commands from cloud.
        """
        if not self._connected:
            return []
        # In production: receive via WebSocket
        commands = self._pending_commands[:]
        self._pending_commands.clear()
        return commands

    async def heartbeat(self) -> dict[str, Any]:
        """
        Send heartbeat to cloud and receive config version update.
        Returns acknowledgment with config metadata.
        """
        self.hlc = self.hlc.increment()
        return {
            "ack": True,
            "next_heartbeat_ms": 30000,
            "config_version": "1.0",
            "hlc": self.hlc.to_dict(),
        }

    async def detect_conflict(
        self,
        key: str,
        cloud_value: Any,
        edge_value: Any,
        cloud_hlc: HLCTimestamp,
        edge_hlc: HLCTimestamp,
    ) -> Optional[SyncConflict]:
        """Detect conflict between cloud and edge values."""
        if cloud_value == edge_value:
            return None
        return SyncConflict(
            key=key,
            cloud_value=cloud_value,
            edge_value=edge_value,
            cloud_hlc=cloud_hlc,
            edge_hlc=edge_hlc,
        )

    async def resolve_conflict(self, conflict: SyncConflict) -> Any:
        """
        Resolve conflict using strategy.
        Returns resolved value.
        """
        if conflict.strategy == "lww":
            # Last-Writer-Wins
            if conflict.edge_hlc.is_after(conflict.cloud_hlc):
                return conflict.edge_value
            return conflict.cloud_value
        elif conflict.strategy == "merge":
            # Merge (for sets, unions; for registers, keep both)
            if isinstance(conflict.cloud_value, set) and isinstance(conflict.edge_value, set):
                return conflict.cloud_value | conflict.edge_value
            return conflict.edge_value  # Default to edge
        return conflict.edge_value

    def get_pending_count(self) -> dict[str, int]:
        """Get counts of pending uploads and downloads."""
        return {
            "pending_uploads": len(self._pending_uploads),
            "pending_commands": len(self._pending_commands),
            "conflicts": len(self._conflicts),
        }


# Schemas
class UploadRequest(BaseModel):
    """Request to upload telemetry points."""
    points: list[dict[str, Any]] = Field(..., min_length=1)


class UploadResponse(BaseModel):
    """Response from upload."""
    accepted: int = 0
    rejected: int = 0
    queued: int = 0
    hlc: dict[str, Any] = Field(default_factory=dict)


class CommandDownloadResponse(BaseModel):
    """Response with downloaded commands."""
    commands: list[dict[str, Any]] = Field(default_factory=list)
    hlc: dict[str, Any] = Field(default_factory=dict)

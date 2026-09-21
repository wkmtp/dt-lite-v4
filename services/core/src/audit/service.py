"""Audit Log Service — Immutable append-only, tamper-evident hash chain, query API."""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_ACTIONS = {"execute", "read", "write", "approve", "deny", "administer", "create", "update", "delete"}
VALID_RESULT_CODES = {"success", "failure", "approved", "denied", "pending"}
VALID_ACTOR_TYPES = {"agent", "tool", "capability", "system", "human"}
VALID_RESOURCE_TYPES = {"asset", "point", "alarm", "tool", "agent", "permission", "scene", "workflow", "workorder", "kpi"}


@dataclass
class AuditEntry:
    """Immutable audit log entry with hash chain."""
    id: str
    timestamp: str
    actor_id: str
    actor_type: str
    action: str
    resource_type: str
    resource_id: str
    result: str
    safety_level: str
    prev_hash: str  # SHA256 of previous entry
    entry_hash: str  # SHA256(this entry content)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_tampered(self) -> bool:
        """Check if this entry's hash has been modified."""
        # Recompute expected hash
        content = f"{self.timestamp}:{self.actor_id}:{self.actor_type}:{self.action}:{self.resource_type}:{self.resource_id}:{self.result}:{self.safety_level}:{self.prev_hash}:{str(self.metadata)}"
        expected = hashlib.sha256(content.encode()).hexdigest()
        return self.entry_hash != expected


class AuditLogService:
    """Audit log service: immutable append-only, tamper-evident hash chain.

    Every AI security chain step MUST produce an audit entry.
    """

    def __init__(self) -> None:
        self._entries: dict[str, AuditEntry] = {}
        self._last_hash: str = ""  # SHA256 of empty string as genesis

    def append(
        self,
        actor_id: str,
        actor_type: str,
        action: str,
        resource_type: str,
        resource_id: str,
        result: str,
        safety_level: str = "C0",
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Append an immutable audit entry."""
        # Validate inputs
        if actor_type not in VALID_ACTOR_TYPES:
            raise ValueError(f"Invalid actor_type '{actor_type}'. Must be one of: {sorted(VALID_ACTOR_TYPES)}")
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action '{action}'. Must be one of: {sorted(VALID_ACTIONS)}")
        if resource_type not in VALID_RESOURCE_TYPES:
            raise ValueError(f"Invalid resource_type '{resource_type}'. Must be one of: {sorted(VALID_RESOURCE_TYPES)}")
        if result not in VALID_RESULT_CODES:
            raise ValueError(f"Invalid result '{result}'. Must be one of: {sorted(VALID_RESULT_CODES)}")
        if safety_level not in {"C0", "C1", "C2", "C3", "C4"}:
            raise ValueError(f"Invalid safety_level '{safety_level}'")

        entry_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        meta = metadata or {}

        # Compute hash chain
        content = f"{timestamp}:{actor_id}:{actor_type}:{action}:{resource_type}:{resource_id}:{result}:{safety_level}:{self._last_hash}:{str(meta)}"
        entry_hash = hashlib.sha256(content.encode()).hexdigest()

        entry = AuditEntry(
            id=entry_id,
            timestamp=timestamp,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            safety_level=safety_level,
            prev_hash=self._last_hash,
            entry_hash=entry_hash,
            metadata=meta,
        )

        self._entries[entry_id] = entry
        self._last_hash = entry_hash

        logger.info(
            "Audit: %s %s by %s(%s) on %s/%s → %s safety=%s",
            action, result, actor_id, actor_type, resource_type, resource_id, safety_level,
        )
        return entry

    def get(self, entry_id: str) -> Optional[AuditEntry]:
        return self._entries.get(entry_id)

    def query(
        self,
        actor_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        result: str | None = None,
        safety_level: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with filters."""
        results = []
        for entry in self._entries.values():
            if actor_id and entry.actor_id != actor_id:
                continue
            if action and entry.action != action:
                continue
            if resource_type and entry.resource_type != resource_type:
                continue
            if resource_id and entry.resource_id != resource_id:
                continue
            if result and entry.result != result:
                continue
            if safety_level and entry.safety_level != safety_level:
                continue
            results.append(entry)

        # Return most recent first, limited
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def verify_chain(self) -> bool:
        """Verify the entire hash chain integrity."""
        if not self._entries:
            return True

        sorted_entries = sorted(self._entries.values(), key=lambda e: e.timestamp)
        expected_prev_hash = ""

        for entry in sorted_entries:
            # Check prev_hash matches expected
            if entry.prev_hash != expected_prev_hash:
                logger.error("Chain break at entry %s: expected prev_hash=%s, got %s",
                             entry.id[:8], expected_prev_hash[:8], entry.prev_hash[:8])
                return False

            # Verify entry hash
            content = f"{entry.timestamp}:{entry.actor_id}:{entry.actor_type}:{entry.action}:{entry.resource_type}:{entry.resource_id}:{entry.result}:{entry.safety_level}:{entry.prev_hash}:{str(entry.metadata)}"
            expected_hash = hashlib.sha256(content.encode()).hexdigest()
            if entry.entry_hash != expected_hash:
                logger.error("Hash mismatch at entry %s", entry.id[:8])
                return False

            expected_prev_hash = entry.entry_hash

        return True

    def count(self) -> int:
        return len(self._entries)

    def count_by_safety_level(self, safety_level: str) -> int:
        return sum(1 for e in self._entries.values() if e.safety_level == safety_level)

    def count_by_result(self, result: str) -> int:
        return sum(1 for e in self._entries.values() if e.result == result)

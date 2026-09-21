"""Relationship Service — Directed, typed, bidirectional sync."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_RELATIONSHIP_TYPES = {"contains", "feeds", "controls", "monitors", "supplies", "depends_on"}
VALID_DIRECTIONS = {"directed", "bidirectional"}
CASCADE_OPTIONS = {"none", "delete", "detach"}


@dataclass
class Relationship:
    """Relationship entity matching Universal Contract v1.0."""
    id: str
    source_id: str
    target_id: str
    type: str
    direction: str
    cascade_option: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RelationshipService:
    """
    Relationship Service: directed, typed, bidirectional sync.
    NO business rules.
    """

    def __init__(self) -> None:
        self._relationships: dict[str, Relationship] = {}

    def create(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        direction: str = "directed",
        cascade_option: str = "none",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Relationship:
        """Create a relationship."""
        if rel_type not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid relationship type: {rel_type}")
        if direction not in VALID_DIRECTIONS:
            raise ValueError(f"Invalid direction: {direction}")
        if cascade_option not in CASCADE_OPTIONS:
            raise ValueError(f"Invalid cascade option: {cascade_option}")
        if source_id == target_id:
            raise ValueError("Relationship cannot reference the same asset")

        rel_id = f"rel-{source_id}-{target_id}-{rel_type}"
        relationship = Relationship(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            type=rel_type,
            direction=direction,
            cascade_option=cascade_option,
            metadata=metadata or {},
        )
        self._relationships[rel_id] = relationship
        logger.info("Created relationship: %s (%s: %s → %s)", rel_id, rel_type, source_id, target_id)
        return relationship

    def get(self, rel_id: str) -> Optional[Relationship]:
        """Get relationship by ID."""
        return self._relationships.get(rel_id)

    def get_by_source(self, source_id: str) -> list[Relationship]:
        """Get all relationships from a source asset."""
        return [r for r in self._relationships.values() if r.source_id == source_id]

    def get_by_target(self, target_id: str) -> list[Relationship]:
        """Get all relationships to a target asset."""
        return [r for r in self._relationships.values() if r.target_id == target_id]

    def delete(self, rel_id: str) -> bool:
        """Delete a relationship."""
        if rel_id not in self._relationships:
            return False
        rel = self._relationships.pop(rel_id)
        logger.info("Deleted relationship: %s", rel_id)
        return True

    def sync_bidirectional(self, rel_id: str) -> Optional[Relationship]:
        """
        Create bidirectional sync relationship.
        When direction=bidirectional, create reverse relationship.
        """
        rel = self._relationships.get(rel_id)
        if not rel:
            return None
        if rel.direction != "bidirectional":
            return rel

        # Create reverse relationship
        reverse_id = f"rel-{rel.target_id}-{rel.source_id}-{rel.type}"
        if reverse_id not in self._relationships:
            self._relationships[reverse_id] = Relationship(
                id=reverse_id,
                source_id=rel.target_id,
                target_id=rel.source_id,
                type=rel.type,
                direction="bidirectional",
                cascade_option=rel.cascade_option,
                metadata={**rel.metadata, "synced_from": rel_id},
            )
            logger.info("Created bidirectional sync: %s ↔ %s", rel_id, reverse_id)
        return rel

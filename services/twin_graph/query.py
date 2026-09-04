"""TwinQueryEngine — Graph traversal for semantic queries.

Provides neighbor and path-finding capabilities using
service-layer BFS/DFS traversal over PostgreSQL-stored relationships.
No external graph database required.
"""
from collections import deque
from typing import Any, Optional
from uuid import UUID


class TwinQueryEngine:
    """Provides graph traversal and query capabilities over twin relationships.

    All queries are tenant-scoped — no cross-tenant traversal is possible.
    """

    def __init__(self, repository):
        self._repo = repository

    async def get_neighbors(
        self,
        twin_id: UUID,
        tenant_id: UUID,
        relationship_type: Optional[str] = None,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """Get all neighbor twin entities connected to the given entity.

        Args:
            twin_id: The center twin entity ID.
            tenant_id: Current tenant.
            relationship_type: Optional filter by relationship type.
            direction: 'outgoing', 'incoming', or 'both'.

        Returns:
            List of dicts with 'twin_id', 'relationship_type', 'direction'.
        """
        neighbors = []

        if direction in ("outgoing", "both"):
            out_rels = await self._repo.list_source_relationships(twin_id, tenant_id)
            if relationship_type:
                out_rels = [r for r in out_rels if r.relationship_type == relationship_type]
            for rel in out_rels:
                if rel.target_twin_id != twin_id:
                    neighbors.append({
                        "twin_id": rel.target_twin_id,
                        "relationship_type": rel.relationship_type,
                        "direction": "outgoing",
                    })

        if direction in ("incoming", "both"):
            in_rels = await self._repo.list_target_relationships(twin_id, tenant_id)
            if relationship_type:
                in_rels = [r for r in in_rels if r.relationship_type == relationship_type]
            for rel in in_rels:
                if rel.source_twin_id != twin_id:
                    neighbors.append({
                        "twin_id": rel.source_twin_id,
                        "relationship_type": rel.relationship_type,
                        "direction": "incoming",
                    })

        return neighbors

    async def find_path(
        self,
        source_id: UUID,
        target_id: UUID,
        tenant_id: UUID,
        max_depth: int = 5,
    ) -> Optional[list[dict[str, Any]]]:
        """Find a path from source to target using BFS traversal.

        Args:
            source_id: Starting entity ID.
            target_id: Destination entity ID.
            tenant_id: Current tenant (isolates search).
            max_depth: Maximum traversal depth.

        Returns:
            List of path steps, or None if no path exists.
        """
        if source_id == target_id:
            return [{"entity_id": source_id, "relationship_type": None, "direction": "start"}]

        visited: set[UUID] = set()
        queue: deque[tuple[UUID, list[dict[str, Any]]]] = deque()
        queue.append((source_id, [{"entity_id": source_id, "relationship_type": None, "direction": "start"}]))
        visited.add(source_id)

        while queue:
            current_id, path = queue.popleft()

            if len(path) - 1 >= max_depth:
                continue

            outgoing = await self._repo.list_source_relationships(current_id, tenant_id)
            for rel in outgoing:
                next_id = rel.target_twin_id
                if next_id in visited:
                    continue
                if next_id == target_id:
                    return path + [{
                        "entity_id": next_id,
                        "relationship_type": rel.relationship_type,
                        "direction": "forward",
                    }]
                visited.add(next_id)
                queue.append((next_id, path + [{
                    "entity_id": next_id,
                    "relationship_type": rel.relationship_type,
                    "direction": "forward",
                }]))

            incoming = await self._repo.list_target_relationships(current_id, tenant_id)
            for rel in incoming:
                next_id = rel.source_twin_id
                if next_id in visited:
                    continue
                if next_id == target_id:
                    return path + [{
                        "entity_id": next_id,
                        "relationship_type": rel.relationship_type,
                        "direction": "reverse",
                    }]
                visited.add(next_id)
                queue.append((next_id, path + [{
                    "entity_id": next_id,
                    "relationship_type": rel.relationship_type,
                    "direction": "reverse",
                }]))

        return None

"""TwinStateManager — Runtime state management for TwinEntities.

This service manages the current runtime state of TwinEntity objects.
State is derived from telemetry events (NormalizedTelemetry) and
maintained in memory only.

Architecture:
  TelemetryEvent → TwinStateManager → TwinEntity.state

Does NOT:
  - Replace telemetry storage (Task 7)
  - Perform analytics or prediction
  - Implement AI reasoning
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from services.iota.contracts import NormalizedTelemetry
from services.twin.exceptions import TwinEntityNotFoundError
from services.twin.registry import TwinEntityRegistry

logger = logging.getLogger(__name__)


class TwinStateManager:
    """Manages runtime state for TwinEntity objects.

    State is derived from NormalizedTelemetry events and maintained
    in-memory per entity. No persistence layer is involved.

    State structure example:
        {
            "temperature": 25.5,
            "unit": "degC",
            "quality": "GOOD",
            "last_updated": "2026-09-02T12:00:00Z"
        }
    """

    def __init__(self, registry: TwinEntityRegistry) -> None:
        """Initialize with a TwinEntityRegistry instance.

        Args:
            registry: The shared twin entity registry.
        """
        self._registry = registry

    def update_state(
        self,
        entity_id: UUID,
        telemetry: NormalizedTelemetry,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Update a TwinEntity's state from a telemetry event.

        Args:
            entity_id: The target TwinEntity ID.
            telemetry: NormalizedTelemetry from the adapter pipeline.
            tenant_id: Current tenant from JWT context.

        Returns:
            Updated state dictionary.

        Raises:
            TwinEntityNotFoundError: If entity doesn't exist for tenant.
            TwinStateError: If state update fails.
        """
        entity = self._registry.get(entity_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(entity_id)

        # Build state from telemetry
        state_snapshot = self._build_state_snapshot(telemetry)

        # Apply to entity
        entity.update_runtime_state(state_snapshot)

        logger.info(
            "Updated state for TwinEntity=%s tenant=%s key=%s value=%s",
            entity_id,
            tenant_id,
            telemetry.datapoint_id,
            telemetry.value,
        )

        return dict(entity.state)

    def get_state(self, entity_id: UUID, tenant_id: UUID) -> Optional[dict[str, Any]]:
        """Get the current state of a TwinEntity.

        Args:
            entity_id: The target TwinEntity ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            Current state dictionary, or None if entity not found.
        """
        entity = self._registry.get(entity_id, tenant_id)
        if entity is None:
            return None
        return dict(entity.state)

    def clear_state(self, entity_id: UUID, tenant_id: UUID) -> bool:
        """Clear all state for a TwinEntity.

        Args:
            entity_id: The target TwinEntity ID.
            tenant_id: Current tenant from JWT context.

        Returns:
            True if state was cleared, False if entity not found.
        """
        entity = self._registry.get(entity_id, tenant_id)
        if entity is None:
            return False

        entity.runtime_state = {}
        entity.updated_at = datetime.now(timezone.utc)
        logger.info("Cleared state for TwinEntity=%s tenant=%s", entity_id, tenant_id)
        return True

    def list_states(self, tenant_id: UUID, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List all TwinEntity states for a tenant.

        Args:
            tenant_id: Current tenant from JWT context.
            limit: Maximum number of entities.
            offset: Pagination offset.

        Returns:
            List of {entity_id, name, type, state} dictionaries.
        """
        entities = self._registry.list(tenant_id, limit=limit, offset=offset)
        return [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "state": dict(e.state),
                "updated_at": e.updated_at.isoformat(),
            }
            for e in entities
        ]

    @staticmethod
    def _build_state_snapshot(telemetry: NormalizedTelemetry) -> dict[str, Any]:
        """Build a state snapshot from normalized telemetry.

        Args:
            telemetry: NormalizedTelemetry event.

        Returns:
            State dictionary with value, quality, timestamp.
        """
        return {
            "value": telemetry.value,
            "data_type": telemetry.data_type,
            "quality": telemetry.quality,
            "unit": telemetry.unit,
            "event_time": telemetry.event_time.isoformat() if telemetry.event_time else None,
            "ingested_at": telemetry.ingested_at.isoformat() if telemetry.ingested_at else None,
        }

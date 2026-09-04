"""TwinEntity runtime model — Digital twin representation.

IMPORTANT: TwinEntity is NOT a database model.

  Device (Task 5): Physical asset definition
      - Connected to protocol adapter
      - Has DataPoints (input/output channels)
      - Stored in PostgreSQL devices table

  TwinEntity (Task 8): Digital runtime representation
      - Mirrors Device for visualization/analytics
      - Has dynamic runtime state
      - In-memory only (runtime concept)
      - Can have multiple twins per device (e.g., different views)
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4


def _now_utc() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class TwinEntity:
    """Runtime representation of a digital twin entity.

    This is an in-memory model — it does NOT map to a database table.
    Persistence is managed externally via TwinEntityRegistry and
    TwinStateManager.

    Attributes:
        id: Unique identifier for this twin entity.
        tenant_id: Tenant ownership (from JWT context).
        name: Human-readable name.
        entity_type: Category (e.g., "pump", "valve", "sensor").
        template: Optional template reference for type-specific behavior.
        device_id: Linked physical device (nullable — unbound twins allowed).
        state: Current runtime state dictionary.
        created_at: Registry creation timestamp.
        updated_at: Last state update timestamp.
    """
    id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    name: str = ""
    entity_type: str = ""
    template: dict[str, Any] = field(default_factory=dict)
    device_id: Optional[UUID] = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now_utc)
    updated_at: datetime = field(default_factory=_now_utc)

    def update_runtime_state(self, new_state: dict[str, Any]) -> None:
        """Merge new runtime state values into current state."""
        self.runtime_state.update(new_state)
        self.updated_at = _now_utc()

    def get_runtime_state(self, key: Optional[str] = None) -> Any:
        """Get a specific runtime state value or the full state dict."""
        if key is None:
            return dict(self.runtime_state)
        return self.runtime_state.get(key)

    @property
    def state(self) -> dict[str, Any]:
        """Backward compatibility property for runtime_state."""
        return self.runtime_state

    @state.setter
    def state(self, value: dict[str, Any]) -> None:
        """Backward compatibility setter for runtime_state."""
        self.runtime_state = value

    def __repr__(self) -> str:
        return (
            f"<TwinEntity(id={self.id}, tenant_id={self.tenant_id}, "
            f"name={self.name!r}, type={self.entity_type!r}, "
            f"device_id={self.device_id})>"
        )

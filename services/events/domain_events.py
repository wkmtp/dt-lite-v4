"""Domain Events - Foundation for event-driven architecture.

Events are defined here but NOT connected to MQTT/Kafka in this phase.
Service layer raises events, external adapters can subscribe later.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event."""
    event_type: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EntityCreated(DomainEvent):
    """Event raised when an entity is created."""
    entity_id: UUID = field(default=None)  # type: ignore
    entity_type: str = ""
    name: str = ""
    tenant_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'entity.created')


@dataclass(frozen=True)
class EntityUpdated(DomainEvent):
    """Event raised when an entity is updated."""
    entity_id: UUID = field(default=None)  # type: ignore
    changes: dict[str, Any] = field(default_factory=dict)
    tenant_id: UUID | None = None

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'entity.updated')


@dataclass(frozen=True)
class EntityDeleted(DomainEvent):
    """Event raised when an entity is soft-deleted."""
    entity_id: UUID = field(default=None)  # type: ignore
    tenant_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'entity.deleted')


@dataclass(frozen=True)
class AssetCreated(DomainEvent):
    """Event raised when an asset is created."""
    asset_id: UUID = field(default=None)  # type: ignore
    asset_code: str = ""
    entity_id: UUID = field(default=None)  # type: ignore
    tenant_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'asset.created')


@dataclass(frozen=True)
class AssetBound(DomainEvent):
    """Event raised when an asset is bound to an entity."""
    asset_id: UUID = field(default=None)  # type: ignore
    entity_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'asset.bound')


@dataclass(frozen=True)
class AssetUnbound(DomainEvent):
    """Event raised when an asset is unbound from an entity."""
    asset_id: UUID = field(default=None)  # type: ignore
    entity_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'asset.unbound')


@dataclass(frozen=True)
class PropertyDefined(DomainEvent):
    """Event raised when a property definition is created."""
    definition_id: UUID = field(default=None)  # type: ignore
    entity_type: str = ""
    key: str = ""
    data_type: str = ""
    tenant_id: UUID | None = None

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'property.defined')


@dataclass(frozen=True)
class PropertyChanged(DomainEvent):
    """Event raised when a property value is set or updated."""
    entity_id: UUID = field(default=None)  # type: ignore
    definition_id: UUID = field(default=None)  # type: ignore
    key: str = ""
    new_value: Any = None
    old_value: Any | None = None

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'property.changed')


@dataclass(frozen=True)
class RelationshipCreated(DomainEvent):
    """Event raised when a relationship is created."""
    relationship_id: UUID = field(default=None)  # type: ignore
    source_entity_id: UUID = field(default=None)  # type: ignore
    target_entity_id: UUID = field(default=None)  # type: ignore
    relation_type: str = ""
    tenant_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'relationship.created')


@dataclass(frozen=True)
class RelationshipDeleted(DomainEvent):
    """Event raised when a relationship is deleted."""
    relationship_id: UUID = field(default=None)  # type: ignore
    tenant_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'relationship.deleted')


@dataclass(frozen=True)
class TenantCreated(DomainEvent):
    """Event raised when a tenant is created."""
    tenant_id: UUID = field(default=None)  # type: ignore
    tenant_code: str = ""
    tenant_name: str = ""

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'tenant.created')


@dataclass(frozen=True)
class UserCreated(DomainEvent):
    """Event raised when a user is created."""
    user_id: UUID = field(default=None)  # type: ignore
    username: str = ""
    tenant_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'user.created')


@dataclass(frozen=True)
class RoleAssigned(DomainEvent):
    """Event raised when a role is assigned to a user."""
    user_id: UUID = field(default=None)  # type: ignore
    role_id: UUID = field(default=None)  # type: ignore
    role_code: str = ""
    tenant_id: UUID = field(default=None)  # type: ignore

    def __post_init__(self):
        object.__setattr__(self, 'event_type', 'role.assigned')

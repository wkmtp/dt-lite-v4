"""Property Service - Domain application service for Property definitions and values.

Responsible for:
- PropertyDefinition CRUD operations
- PropertyValue type validation (STRING, INTEGER, FLOAT, BOOLEAN, JSON)
- Preventing invalid type assignments
- Domain event preparation
"""
from typing import Any, Optional
from uuid import UUID

from services.core.models.models import PropertyDefinition, PropertyValue
from services.core.schemas.property import (
    VALID_PROPERTY_TYPES,
    PropertyDefinitionCreate,
    PropertyDefinitionResponse,
    PropertyListResponse,
    PropertyValueResponse,
)
from services.core.unit_of_work import UnitOfWork
from services.events.domain_events import PropertyChanged, PropertyDefined
from services.exceptions.base import EntityNotFound, InvalidPropertyType
from services.exceptions.entity import ValidationError


def _to_definition_response(defn: PropertyDefinition) -> PropertyDefinitionResponse:
    """Convert PropertyDefinition to DTO."""
    return PropertyDefinitionResponse(
        id=defn.id,
        tenant_id=defn.tenant_id,
        entity_type=defn.entity_type,
        key=defn.key,
        data_type=defn.data_type,
        unit=defn.unit,
        required=defn.required,
        writable=defn.writable,
        metadata=defn.extra_data,
        created_at=defn.created_at,
        updated_at=defn.updated_at,
        deleted_at=defn.deleted_at,
    )


def _to_value_response(pv: PropertyValue) -> PropertyValueResponse:
    """Convert PropertyValue to DTO."""
    return PropertyValueResponse(
        entity_id=pv.entity_id,
        definition_id=pv.property_definition_id,
        value=pv.value,
        updated_at=pv.updated_at,
    )


class PropertyService:
    """Domain service for Property operations.

    Type validation rules (strict):
    - STRING: any non-null string/bytes
    - INTEGER: int only (not bool), or numeric string like "123"
    - FLOAT: int/float only (not bool), or numeric string like "123.5"
    - BOOLEAN: bool only, or string "true"/"false"/"1"/"0"/"yes"/"no"
    - JSON: dict or list
    """

    # Strict type validators (applied after coercion)
    TYPE_VALIDATORS = {
        "STRING": lambda v: isinstance(v, (str, bytes)),
        "INTEGER": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "FLOAT": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "BOOLEAN": lambda v: isinstance(v, bool),
        "JSON": lambda v: isinstance(v, (dict, list)),
    }

    def __init__(self, uow: UnitOfWork):
        self._uow = uow

    async def define_property(
        self, data: PropertyDefinitionCreate, tenant_id: Optional[UUID] = None
    ) -> tuple[PropertyDefinitionResponse, PropertyDefined]:
        """Create a property definition with type validation."""
        if data.data_type not in VALID_PROPERTY_TYPES:
            raise InvalidPropertyType(data.data_type, data.data_type)

        # Check uniqueness
        existing = await self._uow.properties.get_definition_by_key(
            data.entity_type, data.key, tenant_id
        )
        if existing is not None:
            raise ValidationError(
                field="key",
                message=(
                    f"Property definition '{data.key}' "
                    f"already exists for entity_type '{data.entity_type}'"
                )
            )

        defn = PropertyDefinition(
            tenant_id=tenant_id,
            entity_type=data.entity_type.strip(),
            key=data.key.strip(),
            data_type=data.data_type,
            unit=data.unit,
            required=data.required,
            writable=data.writable,
            extra_data=data.metadata,
        )

        defn = await self._uow.properties.create_definition(defn)
        await self._uow.commit()

        event = PropertyDefined(
            definition_id=defn.id,
            entity_type=defn.entity_type,
            key=defn.key,
            data_type=defn.data_type,
            tenant_id=defn.tenant_id,
        )

        return _to_definition_response(defn), event

    async def get_definition(
        self, definition_id: UUID, tenant_id: Optional[UUID] = None
    ) -> Optional[PropertyDefinitionResponse]:
        """Get property definition by ID."""
        defn = await self._uow.properties.get_definition(definition_id, tenant_id)
        if defn is None:
            return None
        return _to_definition_response(defn)

    async def get_definition_by_key(
        self, entity_type: str, key: str, tenant_id: Optional[UUID] = None
    ) -> Optional[PropertyDefinitionResponse]:
        """Get property definition by entity_type and key."""
        defn = await self._uow.properties.get_definition_by_key(entity_type, key, tenant_id)
        if defn is None:
            return None
        return _to_definition_response(defn)

    async def list_definitions(
        self,
        entity_type: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PropertyListResponse:
        """List property definitions."""
        if entity_type:
            items = await self._uow.properties.list_definitions(
                entity_type, tenant_id, limit, offset
            )
        else:
            items = await self._uow.properties.list(
                tenant_id=tenant_id, limit=limit, offset=offset
            )

        return PropertyListResponse(
            items=[_to_definition_response(d) for d in items],
            total=len(items),
            limit=limit,
            offset=offset,
        )

    async def set_property(
        self,
        entity_id: UUID,
        definition_id: UUID,
        value: Any,
    ) -> tuple[PropertyValueResponse, PropertyChanged]:
        """Set a property value with type validation.

        Validates:
        - Definition exists
        - Value type matches definition's data_type
        """
        # Get definition
        defn = await self._uow.properties.get_definition(definition_id)
        if defn is None:
            raise EntityNotFound(definition_id, "PropertyDefinition")

        # Validate entity exists
        entity = await self._uow.entities.get_by_id(entity_id)
        if entity is None:
            raise EntityNotFound(entity_id, "Entity")

        # Type validation and coercion
        validated_value = self._validate_type(value, defn.data_type)

        # Get or create property value
        pv = await self._uow.properties.set_property(entity_id, definition_id, validated_value)
        await self._uow.commit()

        event = PropertyChanged(
            entity_id=entity_id,
            definition_id=definition_id,
            key=defn.key,
            new_value=validated_value,
            old_value=pv.value if pv else None,
        )

        return _to_value_response(pv), event

    async def get_property(
        self, entity_id: UUID, definition_id: UUID
    ) -> Optional[PropertyValueResponse]:
        """Get a single property value."""
        pv = await self._uow.properties.get_property(entity_id, definition_id)
        if pv is None:
            return None
        return _to_value_response(pv)

    async def get_properties(self, entity_id: UUID) -> list[PropertyValueResponse]:
        """Get all properties for an entity."""
        pvs = await self._uow.properties.get_properties(entity_id)
        return [_to_value_response(pv) for pv in pvs]

    async def delete_definition(self, definition_id: UUID) -> bool:
        """Soft delete a property definition."""
        deleted = await self._uow.properties.soft_delete_definition(definition_id)
        if deleted:
            await self._uow.commit()
        return deleted

    def _validate_type(self, value: Any, data_type: str) -> Any:
        """Validate and coerce value to expected type.

        Returns validated value or raises InvalidPropertyType.
        Coercion order:
        1. String → int (INTEGER)
        2. String → float (FLOAT)
        3. String → bool (BOOLEAN)
        4. Strict type check on coerced value
        """
        # String coercion for INTEGER
        if data_type == "INTEGER" and isinstance(value, str):
            try:
                coerced = int(value)
            except (ValueError, TypeError):
                raise InvalidPropertyType(data_type, value)
            # Ensure no fractional part (e.g., "123.5" → fail)
            if "." in value:
                raise InvalidPropertyType(data_type, value)
            return coerced

        # String coercion for FLOAT
        if data_type == "FLOAT" and isinstance(value, str):
            try:
                coerced = float(value)
            except (ValueError, TypeError):
                raise InvalidPropertyType(data_type, value)
            return coerced

        # String coercion for BOOLEAN (case-insensitive)
        if data_type == "BOOLEAN" and isinstance(value, str):
            lower = value.lower()
            if lower in ("true", "1", "yes"):
                return True
            if lower in ("false", "0", "no"):
                return False
            raise InvalidPropertyType(data_type, value)

        # Strict type validation on coerced/original value
        validator = self.TYPE_VALIDATORS.get(data_type)
        if validator is None:
            raise InvalidPropertyType(data_type, value)

        if not validator(value):
            raise InvalidPropertyType(data_type, value)

        return value

    @property
    def events(self):
        return {
            "property_defined": PropertyDefined,
            "property_changed": PropertyChanged,
        }

"""Entity-specific exceptions."""
from services.exceptions.base import (
    EntityNotFound,
    ValidationError,
)


class EntityNameRequired(EntityNotFound):
    """Entity name is required."""

    def __init__(self):
        super().__init__(entity_id="N/A", entity_type="Entity")
        self.message = "Entity name is required"
        self.code = "ENTITY_NAME_REQUIRED"


class EntityTypeRequired(EntityNotFound):
    """Entity type is required."""

    def __init__(self):
        super().__init__(entity_id="N/A", entity_type="Entity")
        self.message = "Entity type is required"
        self.code = "ENTITY_TYPE_REQUIRED"


class EntityDuplicateName(ValidationError):
    """Entity with same name already exists."""

    def __init__(self, name: str, tenant_id: str):
        super().__init__(
            field="name",
            message=f"Entity with name '{name}' already exists in tenant {tenant_id}"
        )
        self.code = "ENTITY_DUPLICATE_NAME"

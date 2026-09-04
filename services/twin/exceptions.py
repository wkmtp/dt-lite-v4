"""Twin Runtime custom exceptions."""
from uuid import UUID


class TwinError(Exception):
    """Base exception for all Twin Runtime errors."""

    def __init__(self, message: str, code: str = "TWIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TwinEntityNotFoundError(TwinError):
    """TwinEntity not found for the given ID and tenant."""

    def __init__(self, entity_id: UUID):
        super().__init__(
            f"TwinEntity {entity_id} not found",
            code="TWIN_ENTITY_NOT_FOUND",
        )


class TwinEntityAlreadyExistsError(TwinError):
    """TwinEntity already exists for the given ID and tenant."""

    def __init__(self, entity_id: UUID):
        super().__init__(
            f"TwinEntity {entity_id} already exists",
            code="TWIN_ENTITY_ALREADY_EXISTS",
        )


class TwinStateError(TwinError):
    """Error in state management operations."""

    def __init__(self, message: str, entity_id: UUID | None = None):
        code = "TWIN_STATE_ERROR"
        if entity_id:
            code = f"TWIN_STATE_ERROR_{entity_id}"
        super().__init__(message, code=code)


class TwinBindingError(TwinError):
    """Error in entity binding operations."""

    def __init__(self, message: str, code: str = "TWIN_BINDING_ERROR"):
        super().__init__(message, code=code)


class TwinTenantMismatchError(TwinError):
    """Cross-tenant access attempt detected."""

    def __init__(self, requested_tenant: UUID, actual_tenant: UUID | None = None):
        msg = (
            f"Tenant mismatch: requested={requested_tenant}"
            f"{f', actual={actual_tenant}' if actual_tenant else ''}"
        )
        super().__init__(msg, code="TWIN_TENANT_MISMATCH")


# Task 9 New Exceptions

class TwinDefinitionNotFoundError(TwinError):
    """TwinDefinition not found for the given ID and tenant."""

    def __init__(self, definition_id: UUID):
        super().__init__(
            f"TwinDefinition {definition_id} not found",
            code="TWIN_DEFINITION_NOT_FOUND",
        )


class TwinDefinitionCodeExistsError(TwinError):
    """TwinDefinition code already exists for tenant."""

    def __init__(self, code: str):
        super().__init__(
            f"TwinDefinition code '{code}' already exists",
            code="TWIN_DEFINITION_CODE_EXISTS",
        )


class TwinDeviceNotFoundError(TwinError):
    """Device not found for the given ID and tenant."""

    def __init__(self, device_id: UUID):
        super().__init__(
            f"Device {device_id} not found",
            code="TWIN_DEVICE_NOT_FOUND",
        )


class TwinBindingNotFoundError(TwinError):
    """TwinBinding not found for the given ID and tenant."""

    def __init__(self, binding_id: UUID):
        super().__init__(
            f"TwinBinding {binding_id} not found",
            code="TWIN_BINDING_NOT_FOUND",
        )


class TwinBindingAlreadyExistsError(TwinError):
    """TwinBinding already exists for the given device and entity."""

    def __init__(self, device_id: UUID, entity_id: UUID):
        super().__init__(
            f"Binding already exists between device {device_id} and entity {entity_id}",
            code="TWIN_BINDING_ALREADY_EXISTS",
        )

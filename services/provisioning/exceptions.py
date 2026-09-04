"""Provisioning exceptions."""
from uuid import UUID


class ProvisioningError(Exception):
    """Base exception for provisioning operations."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class IdempotencyConflictError(ProvisioningError):
    """Entity already exists for this plan."""

    def __init__(self, entity_type: str, external_id: str):
        super().__init__(
            "IDEMPOTENCY_CONFLICT",
            f"Entity {entity_type} '{external_id}' already provisioned",
        )


class InvalidPlanStatusError(ProvisioningError):
    """Attempt to execute plan in wrong status."""

    def __init__(self, current_status: str):
        super().__init__(
            "INVALID_PLAN_STATUS",
            f"Cannot execute plan in status '{current_status}'",
        )


class MissingTemplateError(ProvisioningError):
    """Template not found for provisioning."""

    def __init__(self, template_id: UUID):
        super().__init__(
            "MISSING_TEMPLATE",
            f"Template {template_id} not found",
        )


class EntityTypeNotFoundError(ProvisioningError):
    """Entity type definition not found."""

    def __init__(self, entity_type_id: UUID):
        super().__init__(
            "ENTITY_TYPE_NOT_FOUND",
            f"EntityTypeDefinition {entity_type_id} not found",
        )


class CapabilityMismatchError(ProvisioningError):
    """Capability binding does not match entity type allowed capabilities."""

    def __init__(self, entity_type_code: str, capability_code: str):
        super().__init__(
            "CAPABILITY_MISMATCH",
            f"Capability '{capability_code}' not allowed for entity type '{entity_type_code}'",
        )


class PlanExecutionFailedError(ProvisioningError):
    """Plan execution failed with error details."""

    def __init__(self, plan_id: UUID, error_message: str):
        super().__init__(
            "EXECUTION_FAILED",
            f"Plan {plan_id} execution failed: {error_message}",
        )

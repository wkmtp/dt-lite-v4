"""DT-Lite Domain Exception System

All domain exceptions inherit from DomainException base class.
Services must raise domain exceptions, never generic Exception.
"""
from typing import Any


class DomainException(Exception):
    """Base exception for all DT-Lite domain errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR", details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class EntityNotFound(DomainException):
    """Entity not found exception."""

    def __init__(self, entity_id: Any, entity_type: str = "Entity"):
        super().__init__(
            message=f"{entity_type} with id {entity_id} not found",
            code="ENTITY_NOT_FOUND",
            details={"entity_id": str(entity_id), "entity_type": entity_type}
        )


class AssetAlreadyExists(DomainException):
    """Asset already exists exception."""

    def __init__(self, asset_code: str):
        super().__init__(
            message=f"Asset with code {asset_code} already exists",
            code="ASSET_ALREADY_EXISTS",
            details={"asset_code": asset_code}
        )


class InvalidPropertyType(DomainException):
    """Invalid property type exception."""

    def __init__(self, expected_type: str, actual_value: Any):
        super().__init__(
            message=f"Invalid property value type. Expected {expected_type}, got {type(actual_value).__name__}",
            code="INVALID_PROPERTY_TYPE",
            details={"expected_type": expected_type, "actual_value": str(actual_value)}
        )


class TenantAccessDenied(DomainException):
    """Tenant access denied exception."""

    def __init__(self, tenant_id: Any):
        super().__init__(
            message=f"Access denied for tenant {tenant_id}",
            code="TENANT_ACCESS_DENIED",
            details={"tenant_id": str(tenant_id)}
        )


class PermissionDenied(DomainException):
    """Permission denied exception."""

    def __init__(self, permission_code: str, user_id: Any | None = None):
        super().__init__(
            message=f"Permission denied: {permission_code}",
            code="PERMISSION_DENIED",
            details={"permission_code": permission_code, "user_id": str(user_id) if user_id else None}
        )


class ValidationError(DomainException):
    """Validation error exception."""

    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation error on {field}: {message}",
            code="VALIDATION_ERROR",
            details={"field": field, "message": message}
        )

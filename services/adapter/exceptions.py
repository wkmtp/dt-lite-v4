"""Adapter layer custom exceptions."""
from uuid import UUID


class AdapterError(Exception):
    """Base exception for all adapter errors."""

    def __init__(self, message: str, code: str = "ADAPTER_ERROR"):
        self.code = code
        self.message = message
        super().__init__(self.message)


class AdapterConnectionError(AdapterError):
    """Failed to connect to physical device."""

    def __init__(self, endpoint: str, reason: str):
        super().__init__(
            f"Connection to {endpoint} failed: {reason}",
            code="ADAPTER_CONNECTION_ERROR",
        )


class AdapterProtocolError(AdapterError):
    """Protocol-specific error during communication."""

    def __init__(self, protocol: str, operation: str, reason: str):
        super().__init__(
            f"Protocol {protocol} error during {operation}: {reason}",
            code="ADAPTER_PROTOCOL_ERROR",
        )


class AdapterNotFoundError(AdapterError):
    """Adapter not found for the given configuration."""

    def __init__(self, adapter_type: str, device_id: UUID):
        super().__init__(
            f"Adapter '{adapter_type}' not found for device {device_id}",
            code="ADAPTER_NOT_FOUND",
        )


class AdapterAlreadyExistsError(AdapterError):
    """Adapter already registered."""

    def __init__(self, adapter_id: UUID, tenant_id: UUID):
        super().__init__(
            f"Adapter {adapter_id} already exists for tenant {tenant_id}",
            code="ADAPTER_ALREADY_EXISTS",
        )


class AdapterNotConnectedError(AdapterError):
    """Adapter not connected, operation cannot proceed."""

    def __init__(self, adapter_id: UUID):
        super().__init__(
            f"Adapter {adapter_id} is not connected",
            code="ADAPTER_NOT_CONNECTED",
        )


class AdapterCapabilityMismatchError(AdapterError):
    """Adapter does not support the required capability."""

    def __init__(self, adapter_type: str, capability: str):
        super().__init__(
            f"Adapter '{adapter_type}' does not support capability '{capability}'",
            code="ADAPTER_CAPABILITY_MISMATCH",
        )

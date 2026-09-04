"""Adapter Runtime Exceptions.

All exceptions preserve security boundaries:
- Never expose endpoint, secret, or credential information
- Use generic error messages for external visibility
"""
from typing import Optional


class AdapterError(Exception):
    """Base exception for all adapter errors."""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "ADAPTER_ERROR"
        super().__init__(self.message)


class AdapterNotFoundError(AdapterError):
    """Adapter not found in registry."""

    def __init__(self, name: str):
        super().__init__(
            message=f"Adapter '{name}' not found in registry",
            code="ADAPTER_NOT_FOUND",
        )
        self.name = name


class AdapterConnectionError(AdapterError):
    """Connection failure to device endpoint."""

    def __init__(self, adapter_name: str, cause: Optional[Exception] = None):
        msg = f"Failed to connect adapter '{adapter_name}'"
        if cause:
            msg += f": {type(cause).__name__}"
        super().__init__(message=msg, code="ADAPTER_CONNECTION_ERROR")
        self.adapter_name = adapter_name
        self.cause = cause


class AdapterLifecycleError(AdapterError):
    """Invalid lifecycle state transition."""

    def __init__(self, adapter_name: str, from_state: str, to_state: str):
        super().__init__(
            message=f"Cannot transition adapter '{adapter_name}' "
                    f"from '{from_state}' to '{to_state}'",
            code="ADAPTER_LIFECYCLE_ERROR",
        )
        self.adapter_name = adapter_name
        self.from_state = from_state
        self.to_state = to_state


class AdapterCapabilityError(AdapterError):
    """Adapter does not support requested capability."""

    def __init__(self, adapter_name: str, capability: str):
        super().__init__(
            message=f"Adapter '{adapter_name}' does not support capability '{capability}'",
            code="ADAPTER_CAPABILITY_ERROR",
        )
        self.adapter_name = adapter_name
        self.capability = capability

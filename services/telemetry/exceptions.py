"""Telemetry Layer Exceptions."""
from typing import Optional


class TelemetryError(Exception):
    """Base exception for telemetry errors."""

    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "TELEMETRY_ERROR"
        super().__init__(self.message)


class TelemetryValidationError(TelemetryError):
    """Invalid telemetry data."""

    def __init__(self, errors: list[str]):
        super().__init__(
            message=f"Telemetry validation failed: {'; '.join(errors)}",
            code="TELEMETRY_VALIDATION_ERROR",
        )
        self.errors = errors


class TelemetryTenantMismatchError(TelemetryError):
    """Telemetry tenant_id does not match device ownership."""

    def __init__(self, expected_tenant: str, actual_tenant: Optional[str] = None):
        msg = f"Tenant mismatch: expected {expected_tenant}"
        if actual_tenant:
            msg += f", got {actual_tenant}"
        super().__init__(message=msg, code="TELEMETRY_TENANT_MISMATCH")
        self.expected_tenant = expected_tenant
        self.actual_tenant = actual_tenant


class TelemetryDeviceNotFoundError(TelemetryError):
    """Device not found for given ID."""

    def __init__(self, device_id: str):
        super().__init__(
            message=f"Device not found: {device_id}",
            code="TELEMETRY_DEVICE_NOT_FOUND",
        )
        self.device_id = device_id


class TelemetryDatapointNotFoundError(TelemetryError):
    """DataPoint not found for given ID."""

    def __init__(self, datapoint_id: str):
        super().__init__(
            message=f"DataPoint not found: {datapoint_id}",
            code="TELEMETRY_DATAPPOINT_NOT_FOUND",
        )
        self.datapoint_id = datapoint_id

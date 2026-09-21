"""Adapter Layer — Protocol-Independent Adapter Runtime.

This module provides the infrastructure for protocol adapters to connect
physical devices to the DT-Lite digital twin platform.

Architecture:
  Device (iota) -> Adapter -> NormalizedTelemetry -> TelemetryService (Task 7)
  TwinCommand -> Adapter -> Physical Device

Frozen boundary:
  - MUST NOT import services.telemetry directly
  - MUST NOT import services.adapter sub-modules (no recursive imports)
  - MUST use TenantAwareRepository for all database access
"""
from services.iota.contracts import (
    ProtocolAdapter,
    AdapterCapability,
    NormalizedTelemetry,
    DiscoveryResult,
    DataType,
    AccessMode,
    SamplingMode,
    DataQuality,
    SecretProvider,
)
from services.adapter.exceptions import (
    AdapterError,
    AdapterConnectionError,
    AdapterProtocolError,
    AdapterNotFoundError,
    AdapterAlreadyExistsError,
    AdapterNotConnectedError,
    AdapterCapabilityMismatchError,
)

__all__ = [
    "ProtocolAdapter",
    "AdapterCapability",
    "NormalizedTelemetry",
    "DiscoveryResult",
    "DataType",
    "AccessMode",
    "SamplingMode",
    "DataQuality",
    "SecretProvider",
    "AdapterError",
    "AdapterConnectionError",
    "AdapterProtocolError",
    "AdapterNotFoundError",
    "AdapterAlreadyExistsError",
    "AdapterNotConnectedError",
    "AdapterCapabilityMismatchError",
]

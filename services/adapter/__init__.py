"""Adapter Runtime Layer - DT-Lite V4.0

This module provides the Adapter Runtime Foundation:
- ProtocolAdapter contract (re-exported from iota.contracts)
- AdapterRegistry for runtime adapter management
- AdapterRuntime for lifecycle coordination
- Lifecycle state machine (CREATED → CONNECTED → RUNNING → STOPPED)
- Health monitoring
- SimulatorAdapter for validation

Security boundaries:
- Adapter Runtime has NO direct database access
- Adapter Runtime has NO tenant authority
- Adapter Runtime produces NormalizedTelemetry only
- Service layer bridges Adapter Runtime → IOTA persistence

Protocol independence:
- Zero protocol coupling (no BACnet, Modbus, OPC UA, MQTT in domain code)
- All adapters implement ProtocolAdapter ABC
- Real protocol adapters belong in plugins/protocol/ directory
"""
from services.iota.contracts import (
    AdapterCapability,
    DataQuality,
    DataType,
    DiscoveryResult,
    NormalizedTelemetry,
    ProtocolAdapter,
    SecretProvider,
)
from services.adapter.exceptions import (
    AdapterConnectionError,
    AdapterError,
    AdapterLifecycleError,
    AdapterNotFoundError,
    AdapterCapabilityError,
)
from services.adapter.registry import AdapterRegistry
from services.adapter.runtime import AdapterRuntime
from services.adapter.health import AdapterHealth, HealthMonitor
from services.adapter.lifecycle import AdapterLifecycle, LifecycleState
from services.adapter.simulator import SimulatorAdapter
from services.adapter.models import AdapterInstance

__all__ = [
    # Contracts (re-exported)
    "ProtocolAdapter",
    "SecretProvider",
    "AdapterCapability",
    "DataType",
    "DataQuality",
    "DiscoveryResult",
    "NormalizedTelemetry",
    # Exceptions
    "AdapterError",
    "AdapterConnectionError",
    "AdapterLifecycleError",
    "AdapterNotFoundError",
    "AdapterCapabilityError",
    # Registry & Runtime
    "AdapterRegistry",
    "AdapterRuntime",
    # Lifecycle
    "AdapterLifecycle",
    "LifecycleState",
    # Health
    "AdapterHealth",
    "HealthMonitor",
    # Simulator
    "SimulatorAdapter",
    # Models
    "AdapterInstance",
]

"""Twin Runtime Layer — Digital Twin entities and state management.

This module implements the runtime layer that transforms telemetry-backed
physical objects into digital twin runtime representations.

Architecture:
  Telemetry (Task 7) → TwinStateManager → TwinEntity Runtime State

Key concepts:
  - TwinEntity: Digital runtime representation (NOT a database model)
  - TwinEntityRegistry: In-memory runtime registry
  - TwinStateManager: Current state management per entity
  - EntityBindingService: Device ↔ TwinEntity binding relationships
"""
# Ruff: E402 - Dynamic module loading requires imports after exec_module
# flake8: noqa: E402
import importlib.util
import os
from services.twin.registry import TwinEntityRegistry
from services.twin.state import TwinStateManager
from services.twin.binding import EntityBindingService
from services.twin.models.definition import TwinDefinition
from services.twin.models.entity import PersistentTwinEntity
from services.twin.models.binding import TwinBinding
from services.twin.exceptions import (
    TwinError,
    TwinEntityNotFoundError,
    TwinEntityAlreadyExistsError,
    TwinStateError,
    TwinBindingError,
    TwinTenantMismatchError,
    TwinDefinitionNotFoundError,
    TwinDefinitionCodeExistsError,
    TwinDeviceNotFoundError,
    TwinBindingNotFoundError,
    TwinBindingAlreadyExistsError,
)

# Runtime models - loaded dynamically for backward compatibility
_spec = importlib.util.spec_from_file_location(
    "runtime_models",
    os.path.join(os.path.dirname(__file__), "models.py")
)
_runtime_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_runtime_module)
TwinEntity = _runtime_module.TwinEntity

__all__ = [
    # Runtime
    "TwinEntity",
    "TwinEntityRegistry",
    "TwinStateManager",
    "EntityBindingService",
    # Persistent
    "TwinDefinition",
    "PersistentTwinEntity",
    "TwinBinding",
    # Exceptions
    "TwinError",
    "TwinEntityNotFoundError",
    "TwinEntityAlreadyExistsError",
    "TwinStateError",
    "TwinBindingError",
    "TwinTenantMismatchError",
    "TwinDefinitionNotFoundError",
    "TwinDefinitionCodeExistsError",
    "TwinDeviceNotFoundError",
    "TwinBindingNotFoundError",
    "TwinBindingAlreadyExistsError",
]

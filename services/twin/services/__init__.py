"""Twin Services — Business logic layer for twin persistence.

This module provides the business logic for managing:
- Twin definitions (type schemas)
- Persistent twin entities (instances)
- Twin bindings (device-to-twin relationships)
"""
from services.twin.services.definition_service import DefinitionService
from services.twin.services.entity_service import EntityService
from services.twin.services.binding_service import BindingService

# Re-export TwinService from Task 8 for backward compatibility
import os as _os
import importlib.util as _importlib_util
_twinsvc_path = _os.path.join(_os.path.dirname(__file__), '..', 'services.py')
if _os.path.exists(_twinsvc_path):
    _spec = _importlib_util.spec_from_file_location("twin_services_module", _twinsvc_path)
    _twinsvc_mod = _importlib_util.module_from_spec(_spec)
    _spec.loader.exec_module(_twinsvc_mod)
    TwinService = _twinsvc_mod.TwinService
else:
    TwinService = None

__all__ = [
    "DefinitionService",
    "EntityService",
    "BindingService",
    "TwinService",
]

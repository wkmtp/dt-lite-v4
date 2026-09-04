"""Twin Persistent Models — Database-backed twin definitions and entities.

These models provide persistence for the Twin Runtime (Task 8).
The runtime registry remains in-memory; this layer handles identity,
type definitions, and lifecycle management.
"""
from services.twin.models.definition import TwinDefinition
from services.twin.models.entity import PersistentTwinEntity
from services.twin.models.binding import TwinBinding

# Re-export TwinEntity from runtime module for backward compatibility
import os
_runtime_module_path = os.path.join(os.path.dirname(__file__), '..', 'models.py')
if os.path.exists(_runtime_module_path):
    import importlib.util
    _spec = importlib.util.spec_from_file_location("runtime_models", _runtime_module_path)
    _runtime_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_runtime_mod)
    TwinEntity = _runtime_mod.TwinEntity
else:
    TwinEntity = None

__all__ = [
    # Runtime (backward compatible)
    "TwinEntity",
    # Persistent
    "TwinDefinition",
    "PersistentTwinEntity",
    "TwinBinding",
]

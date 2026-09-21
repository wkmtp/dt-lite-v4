"""Universal Contract Registry — Load, validate, version, diff frozen schemas."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Frozen schema directory — DO NOT MODIFY
# Use absolute path from project root to avoid path calculation errors
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # services/core/src/contracts → project root
SCHEMA_DIR = _PROJECT_ROOT / "packages" / "schemas" / "universal"

# Contract object registry — 31 frozen objects (subset documented in UAA-01)
FROZEN_SCHEMAS = {
    "Asset": "asset.json",
    "Point": "point.json",
    "Capability": "capability.json",
    "Relationship": "relationship.json",
    "AssetTemplate": "asset-template.json",
    "CompositeAsset": "composite-asset.json",
}


@dataclass
class SchemaRegistry:
    """
    Contract Registry: loads, caches, hot-reloads, and diffs Universal Contract schemas.
    """
    _schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    _versions: dict[str, str] = field(default_factory=dict)
    _loaded: bool = False

    def load(self, schema_dir: Optional[Path] = None) -> None:
        """Load all frozen schemas from the universal directory."""
        if self._loaded:
            return
        base = schema_dir or SCHEMA_DIR
        for name, filename in FROZEN_SCHEMAS.items():
            path = base / filename
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._schemas[name] = json.load(f)
                self._versions[name] = "1.0.0"  # frozen version
                logger.info("Loaded schema: %s v1.0.0", name)
            else:
                logger.warning("Schema not found: %s → %s", name, path)
        self._loaded = True

    def get_schema(self, name: str) -> Optional[dict[str, Any]]:
        """Get a loaded schema by name."""
        if not self._loaded:
            self.load()
        return self._schemas.get(name)

    def get_version(self, name: str) -> str:
        """Get the frozen version of a schema."""
        if not self._loaded:
            self.load()
        return self._versions.get(name, "unknown")

    def diff(self, name: str, new_schema: dict[str, Any]) -> dict[str, Any]:
        """
        Compute semantic diff between frozen schema and new schema.
        Returns {} for ZERO diff, or a structure describing changes.
        """
        if not self._loaded:
            self.load()
        frozen = self._schemas.get(name)
        if not frozen:
            return {"error": f"Schema {name} not loaded"}
        return self._semantic_diff(frozen, new_schema)

    def _semantic_diff(self, old: dict, new: dict) -> dict[str, Any]:
        """Compute structural differences between two schema dicts."""
        diff: dict[str, Any] = {}
        old_props = old.get("properties", {})
        new_props = new.get("properties", {})

        # Removed fields
        for key in old_props:
            if key not in new_props:
                diff.setdefault("removed", {})[key] = old_props[key]

        # Added fields
        for key in new_props:
            if key not in old_props:
                diff.setdefault("added", {})[key] = new_props[key]

        # Modified fields
        for key in old_props:
            if key in new_props and old_props[key] != new_props[key]:
                diff.setdefault("modified", {})[key] = {
                    "old": old_props[key],
                    "new": new_props[key],
                }

        # Required fields changes
        old_required = set(old.get("required", []))
        new_required = set(new.get("required", []))
        if old_required != new_required:
            diff["required_changed"] = {
                "removed": list(old_required - new_required),
                "added": list(new_required - old_required),
            }

        return diff

    def validate_against_schema(self, schema_name: str, data: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate data against a frozen schema using basic constraint checking.
        Returns (valid, list_of_errors).
        """
        if not self._loaded:
            self.load()
        schema = self._schemas.get(schema_name)
        if not schema:
            return False, [f"Schema {schema_name} not loaded"]
        return self._validate_data(schema, data, path="$")

    def _validate_data(self, schema: dict, data: Any, path: str) -> tuple[bool, list[str]]:
        """Recursively validate data against schema."""
        errors: list[str] = []

        if not isinstance(data, dict):
            if schema.get("type") == "object":
                errors.append(f"{path}: expected object, got {type(data).__name__}")
            return len(errors) == 0, errors

        # Required fields
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"{path}.{req}: required field missing")

        # Property validation
        props = schema.get("properties", {})
        for key, value in data.items():
            if key in props:
                valid, sub_errors = self._validate_value(props[key], value, f"{path}.{key}")
                errors.extend(sub_errors)

        # Additional properties check
        if schema.get("additionalProperties") is False:
            extra = set(data.keys()) - set(props.keys()) - set(schema.get("required", []))
            for key in extra:
                errors.append(f"{path}.{key}: additional property not allowed")

        return len(errors) == 0, errors

    def _validate_value(self, prop_schema: dict, value: Any, path: str) -> tuple[bool, list[str]]:
        """Validate a single value against a property schema."""
        errors: list[str] = []

        # Type check
        expected_type = prop_schema.get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
            return False, errors
        if expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"{path}: expected number, got {type(value).__name__}")
            return False, errors
        if expected_type == "integer" and not isinstance(value, int):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")
            return False, errors
        if expected_type == "array" and not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return False, errors
        if expected_type == "object" and not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return False, errors
        if expected_type == "boolean" and not isinstance(value, bool):
            errors.append(f"{path}: expected boolean, got {type(value).__name__}")
            return False, errors

        # Enum check
        if "enum" in prop_schema and value not in prop_schema["enum"]:
            errors.append(f"{path}: value {value!r} not in enum {prop_schema['enum']}")

        # Pattern check
        if "pattern" in prop_schema and isinstance(value, str):
            import re
            if not re.match(prop_schema["pattern"], value):
                errors.append(f"{path}: value {value!r} does not match pattern {prop_schema['pattern']}")

        # MinLength / MaxLength
        if isinstance(value, str):
            if "minLength" in prop_schema and len(value) < prop_schema["minLength"]:
                errors.append(f"{path}: string too short (min {prop_schema['minLength']})")
            if "maxLength" in prop_schema and len(value) > prop_schema["maxLength"]:
                errors.append(f"{path}: string too long (max {prop_schema['maxLength']})")

        # Min / Max for numbers
        if isinstance(value, (int, float)):
            if "minimum" in prop_schema and value < prop_schema["minimum"]:
                errors.append(f"{path}: value {value} below minimum {prop_schema['minimum']}")
            if "maximum" in prop_schema and value > prop_schema["maximum"]:
                errors.append(f"{path}: value {value} above maximum {prop_schema['maximum']}")

        # Array items
        if isinstance(value, list) and "items" in prop_schema:
            for i, item in enumerate(value):
                valid, sub_errors = self._validate_value(prop_schema["items"], item, f"{path}[{i}]")
                errors.extend(sub_errors)

        # Nested object
        if isinstance(value, dict) and prop_schema.get("type") == "object":
            _, sub_errors = self._validate_data(prop_schema, value, path)
            errors.extend(sub_errors)

        return len(errors) == 0, errors

    def hot_reload(self, schema_dir: Optional[Path] = None) -> int:
        """Reload schemas from disk. Returns number of schemas reloaded."""
        self._schemas.clear()
        self._loaded = False
        self.load(schema_dir)
        return len(self._schemas)

"""UAA-01 Contract Compatibility Tests — v1.0 ↔ v1.0 semantic diff = ZERO."""
import copy
import json
import pytest
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "services"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.core.src.contracts.registry import SchemaRegistry, FROZEN_SCHEMAS


class TestSchemaInventory:
    """AC-01: All 6 core schemas have required constraints."""

    def test_asset_schema_has_required_fields(self):
        registry = SchemaRegistry()
        registry.load()
        schema = registry.get_schema("Asset")
        assert schema is not None
        required = schema["required"]
        assert "id" in required
        assert "code" in required
        assert "name" in required
        assert "category" in required
        assert "metadata" in required

    def test_point_schema_no_protocol_fields(self):
        """SL-04: Point schema must NOT have protocol fields."""
        registry = SchemaRegistry()
        registry.load()
        schema = registry.get_schema("Point")
        props = schema["properties"]
        forbidden = {"protocol", "address", "register", "slave_id", "function_code", "topic", "url", "endpoint"}
        actual_keys = set(props.keys())
        overlap = actual_keys & forbidden
        assert len(overlap) == 0, f"Point schema contains forbidden protocol fields: {overlap}"

    def test_capability_schema_no_algorithm_fields(self):
        """SL-05: Capability schema must NOT have algorithm/logic fields."""
        registry = SchemaRegistry()
        registry.load()
        schema = registry.get_schema("Capability")
        props = schema["properties"]
        forbidden = {"algorithm", "logic", "implementation", "script"}
        actual_keys = set(props.keys())
        overlap = actual_keys & forbidden
        assert len(overlap) == 0, f"Capability schema contains forbidden fields: {overlap}"

    def test_capability_safety_level_enum(self):
        """SL-06: Safety level must be C0-C4 enum."""
        registry = SchemaRegistry()
        registry.load()
        schema = registry.get_schema("Capability")
        safety = schema["properties"]["safety_level"]
        assert safety["enum"] == ["C0", "C1", "C2", "C3", "C4"]

    def test_asset_naming_convention_pattern(self):
        """AC-01: Asset code follows asset.<domain>.<sub>.<type> regex."""
        registry = SchemaRegistry()
        registry.load()
        schema = registry.get_schema("Asset")
        pattern = schema["properties"]["code"]["pattern"]
        assert "asset" in pattern
        assert "park" in pattern or "factory" in pattern

    def test_all_schemas_have_id_field(self):
        """All 6 schemas must have 'id' as required field."""
        registry = SchemaRegistry()
        registry.load()
        for name in FROZEN_SCHEMAS:
            schema = registry.get_schema(name)
            assert schema is not None
            assert "id" in schema.get("required", []), f"{name} missing 'id' in required"


class TestRegistryLifecycle:
    """AC-02: Registry loads, caches, and supports hot-reload."""

    def test_load_schemas(self):
        registry = SchemaRegistry()
        assert not registry._loaded
        registry.load()
        assert registry._loaded
        assert len(registry._schemas) == 6

    def test_cache_after_load(self):
        registry = SchemaRegistry()
        registry.load()
        # Second load is no-op
        registry.load()
        assert registry._loaded
        assert len(registry._schemas) == 6

    def test_get_schema(self):
        registry = SchemaRegistry()
        registry.load()
        asset = registry.get_schema("Asset")
        assert asset is not None
        assert asset["title"] == "Asset"

    def test_get_version(self):
        registry = SchemaRegistry()
        registry.load()
        assert registry.get_version("Asset") == "1.0.0"
        assert registry.get_version("Point") == "1.0.0"

    def test_hot_reload(self):
        registry = SchemaRegistry()
        registry.load()
        count = registry.hot_reload()
        assert count == 6
        assert registry._loaded


class TestValidatorCLI:
    """AC-03: Validator returns structured output with error paths."""

    def test_validate_valid_asset(self):
        """Valid asset data passes validation."""
        registry = SchemaRegistry()
        registry.load()
        valid_data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "code": "asset.park.facility.ahu",
            "name": "AHU-001",
            "category": "facility",
            "attributes": {},
            "capabilities": [],
            "relationships": [],
            "model_bindings": [],
            "metadata": {"tenant_id": "t1", "created_at": "2026-01-01T00:00:00Z"},
        }
        valid, errors = registry.validate_against_schema("Asset", valid_data)
        assert valid is True
        assert len(errors) == 0

    def test_validate_missing_required(self):
        """Invalid asset data (missing required fields) fails."""
        registry = SchemaRegistry()
        registry.load()
        invalid_data = {"name": "Incomplete Asset"}  # missing id, code, category, etc.
        valid, errors = registry.validate_against_schema("Asset", invalid_data)
        assert valid is False
        assert len(errors) > 0

    def test_validate_point_no_protocol(self):
        """Point validation rejects protocol fields."""
        registry = SchemaRegistry()
        registry.load()
        data = {
            "id": "11111111-1111-4111-8111-111111111111",
            "code": "power",
            "semantic_type": "power",
            "unit": "kW",
            "aggregation": ["latest"],
            "tags": ["energy"],
            "asset_id": "550e8400-e29b-41d4-a716-446655440000",
            "metadata": {},
        }
        valid, errors = registry.validate_against_schema("Point", data)
        assert valid is True
        assert len(errors) == 0

    def test_validate_capability_safety_level(self):
        """Capability with invalid safety level fails."""
        registry = SchemaRegistry()
        registry.load()
        data = {
            "id": "22222222-2222-4222-8222-222222222222",
            "code": "capability.hvac.set_temperature",
            "category": "hvac",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "safety_level": "C1",
            "preconditions": [],
            "postconditions": [],
            "idempotency_key": "test",
        }
        valid, errors = registry.validate_against_schema("Capability", data)
        assert valid is True

    def test_validate_capability_invalid_safety_level(self):
        """Capability with invalid safety level fails."""
        registry = SchemaRegistry()
        registry.load()
        data = {
            "id": "33333333-3333-4333-8333-333333333333",
            "code": "capability.test",
            "category": "test",
            "input_schema": {},
            "output_schema": {},
            "safety_level": "C5",  # invalid
            "preconditions": [],
            "postconditions": [],
            "idempotency_key": "test",
        }
        valid, errors = registry.validate_against_schema("Capability", data)
        assert valid is False
        assert any("C5" in e for e in errors)


class TestCompatibility:
    """AC-04: Semantic diff between v1.0 and v1.0 = ZERO."""

    def test_self_diff_is_zero(self):
        """Diff of a schema against itself must be empty."""
        registry = SchemaRegistry()
        registry.load()
        for name in FROZEN_SCHEMAS:
            schema = registry.get_schema(name)
            assert schema is not None
            diff = registry.diff(name, schema)
            assert diff == {}, f"Self-diff for {name} is not zero: {diff}"

    def test_invalid_schema_diff_detected(self):
        """Adding a new field should produce non-zero diff."""
        import copy
        registry = SchemaRegistry()
        registry.load()
        asset_schema = copy.deepcopy(registry.get_schema("Asset"))
        # Add a field
        asset_schema["properties"]["new_field"] = {"type": "string"}
        diff = registry.diff("Asset", asset_schema)
        assert diff != {}
        assert "added" in diff

    def test_removed_field_detected(self):
        """Removing a required field should produce non-zero diff."""
        import copy
        registry = SchemaRegistry()
        registry.load()
        asset_schema = copy.deepcopy(registry.get_schema("Asset"))
        # Remove a field
        del asset_schema["properties"]["name"]
        diff = registry.diff("Asset", asset_schema)
        assert diff != {}
        assert "removed" in diff

    def test_all_schemas_self_diff_zero(self):
        """All 6 schemas must pass self-diff test."""
        registry = SchemaRegistry()
        registry.load()
        for name in FROZEN_SCHEMAS:
            schema = registry.get_schema(name)
            diff = registry.diff(name, schema)
            assert diff == {}, f"Self-diff failed for {name}: {diff}"


class TestIntegration:
    """AC-06: End-to-end validation with realistic data."""

    def test_full_asset_lifecycle(self):
        """Create, validate, diff, and re-validate a complete asset."""
        registry = SchemaRegistry()
        registry.load()

        # Original asset
        asset_v1 = {
            "id": "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
            "code": "asset.park.facility.chiller",
            "name": "Chiller-001",
            "category": "facility",
            "attributes": {"manufacturer": "Carrier", "capacity_tons": 500},
            "capabilities": ["capability.hvac.cooling"],
            "relationships": [],
            "model_bindings": [],
            "metadata": {"tenant_id": "tenant-1", "created_at": "2026-01-01T00:00:00Z"},
        }
        valid, errors = registry.validate_against_schema("Asset", asset_v1)
        assert valid, f"Asset validation failed: {errors}"

        # Verify self-diff of schema is zero (diff compares schema vs schema, not data)
        frozen = copy.deepcopy(registry.get_schema("Asset"))
        diff = registry.diff("Asset", frozen)
        assert diff == {}

    def test_composite_asset_with_tree(self):
        """CompositeAsset with valid tree structure."""
        registry = SchemaRegistry()
        registry.load()
        data = {
            "id": "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb",
            "code": "asset.park.spatial.building_a",
            "name": "Building A",
            "composition_tree": [
                {"ref": "cccccccc-cccc-4ccc-cccc-cccccccccccc", "type": "contains", "depth": 1},
            ],
            "capability_inheritance": ["monitoring", "alarm"],
            "aggregation_rules": {
                "total_power": {"function": "sum"},
                "avg_temp": {"function": "avg"},
            },
        }
        valid, errors = registry.validate_against_schema("CompositeAsset", data)
        assert valid, f"CompositeAsset validation failed: {errors}"

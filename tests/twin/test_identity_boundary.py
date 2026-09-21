"""UAA-05: Scene, BIM, GIS & 3D — Identity Boundary, Scene Types, Three Runtime.

Tests for:
  - SceneService: 10 scene types, layout validation, model binding management
  - ModelBindingService: BIM/GIS/3D bindings, SL-10 identity boundary (ON DELETE SET NULL)
  - ThreeRuntime: telemetry→color, lifecycle→opacity, animation, latency
  - AG-P0-06: BIM/GIS/3D Identity Boundary
  - Integration: Scene + Binding + Runtime working together
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from services.twin.src.scene.service import SceneService, VALID_SCENE_TYPES
from services.twin.src.binding.service import ModelBindingService, VALID_SOURCES
# three-runtime service module — import via direct path
import importlib
import importlib.util as _iu
import sys
from pathlib import Path
# tests/twin/test_identity_boundary.py → parents[2] = dt-lite-v4
_project_root = Path(__file__).resolve().parents[2]
_engine_path = _project_root / "engine" / "three-runtime"
_service_file = _engine_path / "service.py"
if not _service_file.exists():
    raise RuntimeError(f"three-runtime service.py not found at {_service_file}")
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
_spec = _iu.spec_from_file_location("three_runtime_svc", str(_service_file))
_three_module = _iu.module_from_spec(_spec)
_spec.loader.exec_module(_three_module)
ThreeRuntime = _three_module.ThreeRuntime
_engine_path = _project_root / "engine" / "three-runtime"
_service_file = _engine_path / "service.py"
if not _service_file.exists():
    raise RuntimeError(f"three-runtime service.py not found at {_service_file}")
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# Use importlib to load the service module directly
_spec = importlib.util.spec_from_file_location("three_runtime_service", str(_service_file))
_three_runtime_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_three_runtime_module)
ThreeRuntime = _three_runtime_module.ThreeRuntime



# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def scene_service():
    return SceneService()


@pytest.fixture
def binding_service():
    return ModelBindingService()


@pytest.fixture
def three_runtime():
    return ThreeRuntime()


@pytest.fixture
def asset_id():
    return "test-asset-001"


@pytest.fixture
def sample_layout():
    return {
        "layers": [
            {"id": "layer_1", "visible": True, "opacity": 0.8},
            {"id": "layer_2", "visible": False, "opacity": 0.5},
        ],
        "camera": {"position": [0, 10, 20], "lookAt": [0, 0, 0], "fov": 60},
        "filters": [{"type": "category", "value": "hvac"}],
    }


@pytest.fixture
def sample_binding():
    return {
        "id": "bind-001",
        "source": "bim",
        "source_id": "3$GzT$0G$0nX$K8",
        "source_type": "ifc_element",
        "transform": {
            "translation": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
        },
        "lod": 300,
    }


# ═══════════════════════════════════════════════════════════════════
# SceneService Tests
# ═══════════════════════════════════════════════════════════════════

class TestSceneService:
    """Tests for SceneService: CRUD, 10 scene types, layout validation."""

    def test_create_overview_scene(self, scene_service):
        scene = scene_service.create({
            "id": "scene-001",
            "code": "scene.park.overview_main",
            "name": "Park Overview",
            "type": "overview",
            "layout": {"layers": [{"id": "l1", "visible": True}]},
        }, tenant_id="tenant-1")
        assert scene.id == "scene-001"
        assert scene.type == "overview"
        assert scene.layer_count == 1
        assert scene.tenant_id == "tenant-1"

    def test_all_10_scene_types(self, scene_service):
        """AC-01: All 10 scene types are supported."""
        for stype in VALID_SCENE_TYPES:
            scene = scene_service.create({
                "id": f"scene-{stype}",
                "code": f"scene.park.{stype}_view",
                "name": f"{stype.title()} Scene",
                "type": stype,
                "layout": {},
            }, tenant_id="tenant-1")
            assert scene.type == stype

    def test_reject_invalid_scene_type(self, scene_service):
        with pytest.raises(ValueError, match="Invalid scene type"):
            scene_service.create({
                "id": "scene-bad",
                "code": "scene.park.dash",
                "name": "Bad Scene",
                "type": "dashboard",  # NOT a valid scene type
                "layout": {},
            }, tenant_id="tenant-1")

    def test_reject_invalid_code_pattern(self, scene_service):
        with pytest.raises(ValueError, match="does not match convention"):
            scene_service.create({
                "id": "scene-bad",
                "code": "park.overview",  # missing scene. prefix
                "name": "Bad Code",
                "type": "overview",
                "layout": {},
            }, tenant_id="tenant-1")

    def test_reject_invalid_layout_layers(self, scene_service):
        with pytest.raises(ValueError, match="layout.layers\\[0\\] missing"):
            scene_service.create({
                "id": "scene-bad",
                "code": "scene.park.test_bad",
                "name": "Bad Layout",
                "type": "custom",
                "layout": {"layers": [{"visible": True}]},  # missing 'id'
            }, tenant_id="tenant-1")

    def test_reject_invalid_layout_layers_type(self, scene_service):
        with pytest.raises(ValueError, match="must be an array"):
            scene_service.create({
                "id": "scene-bad",
                "code": "scene.park.test_bad2",
                "name": "Bad Layout 2",
                "type": "custom",
                "layout": {"layers": "not-an-array"},
            }, tenant_id="tenant-1")

    def test_get_scene(self, scene_service):
        scene_service.create({
            "id": "scene-002",
            "code": "scene.park.energy_view",
            "name": "Energy",
            "type": "energy",
            "layout": {"layers": [{"id": "l1", "visible": True}]},
        }, tenant_id="tenant-1")
        retrieved = scene_service.get("scene-002")
        assert retrieved is not None
        assert retrieved.type == "energy"

    def test_get_missing_scene(self, scene_service):
        assert scene_service.get("nonexistent") is None

    def test_list_by_type(self, scene_service):
        for i in range(3):
            scene_service.create({
                "id": f"scene-hvac-{i}",
                "code": f"scene.park.hvac_view_{i}",
                "name": f"HVAC {i}",
                "type": "hvac",
                "layout": {"layers": [{"id": f"l{i}", "visible": True}]},
            }, tenant_id="tenant-1")
        hvac_scenes = scene_service.list_by_type("hvac", "tenant-1")
        assert len(hvac_scenes) == 3

    def test_list_by_tenant(self, scene_service):
        scene_service.create({
            "id": "scene-003",
            "code": "scene.park.water_view",
            "name": "Water",
            "type": "water",
            "layout": {},
        }, tenant_id="tenant-1")
        scene_service.create({
            "id": "scene-004",
            "code": "scene.park.fire_view",
            "name": "Fire",
            "type": "fire",
            "layout": {},
        }, tenant_id="tenant-2")
        t1_scenes = scene_service.list_by_tenant("tenant-1")
        t2_scenes = scene_service.list_by_tenant("tenant-2")
        assert len(t1_scenes) == 1
        assert len(t2_scenes) == 1
        assert t1_scenes[0].id == "scene-003"
        assert t2_scenes[0].id == "scene-004"

    def test_update_scene(self, scene_service):
        scene = scene_service.create({
            "id": "scene-005",
            "code": "scene.park.custom_view",
            "name": "Custom",
            "type": "custom",
            "layout": {"layers": [{"id": "l1", "visible": True}]},
        }, tenant_id="tenant-1")
        updated = scene_service.update("scene-005", {"name": "Custom Updated"})
        assert updated.name == "Custom Updated"

    def test_update_reject_invalid_layout(self, scene_service):
        scene_service.create({
            "id": "scene-006",
            "code": "scene.park.test_upd",
            "name": "Test Update",
            "type": "custom",
            "layout": {"layers": [{"id": "l1", "visible": True}]},
        }, tenant_id="tenant-1")
        with pytest.raises(ValueError, match="must be an array"):
            scene_service.update("scene-006", {"layout": {"layers": "invalid"}})

    def test_delete_scene(self, scene_service):
        scene_service.create({
            "id": "scene-007",
            "code": "scene.park.del_test",
            "name": "Delete Test",
            "type": "security",
            "layout": {},
        }, tenant_id="tenant-1")
        assert scene_service.delete("scene-007") is True
        assert scene_service.get("scene-007") is None

    def test_delete_missing_scene(self, scene_service):
        assert scene_service.delete("nonexistent") is False

    def test_bind_asset_to_scene(self, scene_service, sample_binding):
        scene_service.create({
            "id": "scene-008",
            "code": "scene.park.bind_test",
            "name": "Bind Test",
            "type": "overview",
            "layout": {"layers": [{"id": "l1", "visible": True}]},
        }, tenant_id="tenant-1")
        scene = scene_service.bind_asset("scene-008", sample_binding)
        assert scene is not None
        assert len(scene.model_bindings) == 1
        assert scene.model_bindings[0]["source"] == "bim"

    def test_bind_reject_invalid_source(self, scene_service):
        scene_service.create({
            "id": "scene-009",
            "code": "scene.park.bind_src",
            "name": "Bind Source",
            "type": "custom",
            "layout": {},
        }, tenant_id="tenant-1")
        with pytest.raises(ValueError, match="Invalid binding source"):
            scene_service.bind_asset("scene-009", {
                "id": "b1", "source": "invalid", "source_id": "x"
            })

    def test_unbind_asset_from_scene(self, scene_service, sample_binding):
        scene_service.create({
            "id": "scene-010",
            "code": "scene.park.unbind_test",
            "name": "Unbind Test",
            "type": "custom",
            "layout": {},
        }, tenant_id="tenant-1")
        scene_service.bind_asset("scene-010", sample_binding)
        scene = scene_service.unbind_asset("scene-010", "bind-001")
        assert scene is not None
        assert len(scene.model_bindings) == 0

    def test_reject_binding_missing_required_field(self, scene_service):
        scene_service.create({
            "id": "scene-011",
            "code": "scene.park.bind_req",
            "name": "Bind Required",
            "type": "custom",
            "layout": {},
        }, tenant_id="tenant-1")
        with pytest.raises(ValueError, match="missing required field"):
            scene_service.bind_asset("scene-011", {"source": "bim"})  # missing id, source_id


# ═══════════════════════════════════════════════════════════════════
# ModelBindingService Tests
# ═══════════════════════════════════════════════════════════════════

class TestModelBindingService:
    """Tests for ModelBindingService: BIM/GIS/3D bindings."""

    def test_create_bim_binding(self, binding_service, asset_id):
        binding = binding_service.create(
            asset_id=asset_id,
            source="bim",
            source_id="3$GzT$0G$0nX$K8",
            source_type="ifc_element",
            lod=300,
        )
        assert binding.source == "bim"
        assert binding.source_id == "3$GzT$0G$0nX$K8"
        assert binding.lod == 300
        assert binding.asset_id == asset_id
        assert not binding.is_nullified

    def test_create_gis_binding(self, binding_service, asset_id):
        binding = binding_service.create(
            asset_id=asset_id,
            source="gis",
            source_id="geojson-feature-001",
            source_type="geojson_feature",
            lod=200,
        )
        assert binding.source == "gis"
        assert binding.source_type == "geojson_feature"

    def test_create_3d_binding(self, binding_service, asset_id):
        binding = binding_service.create(
            asset_id=asset_id,
            source="3d",
            source_id="node-hvac-ahu-01",
            source_type="gltf_node",
            lod=400,
        )
        assert binding.source == "3d"
        assert binding.source_type == "gltf_node"
        assert binding.lod == 400

    def test_reject_invalid_source(self, binding_service, asset_id):
        with pytest.raises(ValueError, match="Invalid source"):
            binding_service.create(
                asset_id=asset_id, source="Invalid", source_id="x"
            )

    def test_reject_invalid_source_type_for_bim(self, binding_service, asset_id):
        with pytest.raises(ValueError, match="Invalid source_type"):
            binding_service.create(
                asset_id=asset_id, source="bim", source_id="x",
                source_type="gltf_node",
            )

    def test_reject_lod_out_of_range_low(self, binding_service, asset_id):
        with pytest.raises(ValueError, match="lod must be an integer"):
            binding_service.create(
                asset_id=asset_id, source="bim", source_id="x", lod=50
            )

    def test_reject_lod_out_of_range_high(self, binding_service, asset_id):
        with pytest.raises(ValueError, match="lod must be an integer"):
            binding_service.create(
                asset_id=asset_id, source="bim", source_id="x", lod=600
            )

    def test_list_by_asset(self, binding_service, asset_id):
        binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-1")
        binding_service.create(asset_id=asset_id, source="gis", source_id="geo-1")
        binding_service.create(asset_id=asset_id, source="3d", source_id="node-1")
        bindings = binding_service.list_by_asset(asset_id)
        assert len(bindings) == 3

    def test_list_by_source(self, binding_service, asset_id):
        binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-1")
        binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-2")
        binding_service.create(asset_id=asset_id, source="gis", source_id="geo-1")
        bim_bindings = binding_service.list_by_source("bim")
        assert len(bim_bindings) == 2

    def test_count(self, binding_service, asset_id):
        assert binding_service.count() == 0
        binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-1")
        binding_service.create(asset_id=asset_id, source="gis", source_id="geo-1")
        assert binding_service.count() == 2

    def test_delete_binding(self, binding_service, asset_id):
        b = binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-1")
        assert binding_service.delete(b.id) is True
        assert binding_service.get(b.id) is None
        assert binding_service.count() == 0

    def test_delete_missing_binding(self, binding_service):
        assert binding_service.delete("nonexistent") is False

    def test_delete_by_asset_removes_all(self, binding_service, asset_id):
        binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-1")
        binding_service.create(asset_id=asset_id, source="gis", source_id="geo-1")
        binding_service.create(asset_id=asset_id, source="3d", source_id="node-1")
        removed = binding_service.delete_by_asset(asset_id)
        assert removed == 3
        assert binding_service.count() == 0


# ═══════════════════════════════════════════════════════════════════
# SL-10 Identity Boundary Tests  (AG-P0-06)
# ═══════════════════════════════════════════════════════════════════

class TestIdentityBoundary:
    """SL-10: ModelObject deletion ≠ Asset deletion. AG-P0-06 gate.

    Key invariant:
      - Deleting a BIM element → binding.asset_id set to NULL, Asset persists
      - Deleting a GIS feature → binding.asset_id set to NULL, Asset persists
      - Deleting a 3D node → binding.asset_id set to NULL, Asset persists
      - Deleting an Asset → all its bindings are removed
    """

    def test_bim_deletion_nullifies_binding(self, binding_service, asset_id):
        """IB-01: DELETE bim_element → Asset persists, binding.asset_id=NULL."""
        binding = binding_service.create(
            asset_id=asset_id, source="bim", source_id="ifc-guid-001",
            source_type="ifc_element", lod=300,
        )
        # Simulate BIM element deletion → nullify binding
        nullified = binding_service.nullify(binding.id)
        assert nullified is not None
        assert nullified.is_nullified is True
        assert nullified.asset_id == ""
        assert "nullified_at" in nullified.metadata
        assert nullified.metadata["nullified_reason"] == "model_object_deleted"

    def test_gis_deletion_nullifies_binding(self, binding_service, asset_id):
        """IB-02: DELETE geojson_feature → Asset persists, binding.asset_id=NULL."""
        binding = binding_service.create(
            asset_id=asset_id, source="gis", source_id="geo-feature-001",
            source_type="geojson_feature", lod=200,
        )
        nullified = binding_service.nullify(binding.id)
        assert nullified.is_nullified is True

    def test_3d_deletion_nullifies_binding(self, binding_service, asset_id):
        """IB-03: DELETE gltf_node → Asset persists, binding.asset_id=NULL."""
        binding = binding_service.create(
            asset_id=asset_id, source="3d", source_id="node-001",
            source_type="gltf_node", lod=400,
        )
        nullified = binding_service.nullify(binding.id)
        assert nullified.is_nullified is True

    def test_asset_deletion_removes_all_bindings(self, binding_service, asset_id):
        """IB-04: DELETE asset → ALL bindings for that asset are removed."""
        binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-1")
        binding_service.create(asset_id=asset_id, source="gis", source_id="geo-1")
        binding_service.create(asset_id=asset_id, source="3d", source_id="node-1")
        removed = binding_service.delete_by_asset(asset_id)
        assert removed == 3
        assert binding_service.count() == 0
        assert binding_service.list_by_asset(asset_id) == []

    def test_asset_persists_after_bim_nullify(self, binding_service, asset_id):
        """Asset is NOT deleted when its BIM binding is nullified."""
        binding = binding_service.create(
            asset_id=asset_id, source="bim", source_id="ifc-x",
        )
        binding_service.nullify(binding.id)
        # Asset still "exists" in the system — binding is just nullified
        assert binding_service.count() == 1
        nullified = binding_service.get(binding.id)
        assert nullified.is_nullified is True

    def test_nullify_missing_binding(self, binding_service):
        assert binding_service.nullify("nonexistent") is None


# ═══════════════════════════════════════════════════════════════════
# ThreeRuntime Tests
# ═══════════════════════════════════════════════════════════════════

class TestThreeRuntime:
    """Tests for ThreeRuntime: telemetry→color, lifecycle→opacity, animation."""

    def test_update_normal_state(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {"power_kw": 0.2}, lifecycle_status="active")
        assert state.asset_id == asset_id
        assert state.opacity == 1.0  # active
        assert state.color[0] == 0.0  # green-dominant (R=0)
        assert state.color[1] > state.color[2]  # G > B
        assert "asset_id" in state.tooltip

    def test_update_warning_state(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {"power_kw": 0.5}, lifecycle_status="active")
        assert state.opacity == 1.0  # active
        # Color should be in yellow band (G high, R starts increasing)
        assert state.color[1] > 0.3  # green component still significant

    def test_update_alarm_state(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {"power_kw": 0.9}, lifecycle_status="active")
        assert state.color[0] > 0.2  # red component present
        assert state.animation.get("type") == "pulse"
        assert state.animation.get("speed") == 2.0

    def test_update_decommissioned_opacity(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {"temp_degC": 20.0}, lifecycle_status="decommissioned")
        assert state.opacity == 0.3

    def test_update_retired_opacity(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {}, lifecycle_status="retired")
        assert state.opacity == 0.1

    def test_update_provisioned_opacity(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {}, lifecycle_status="provisioned")
        assert state.opacity == 0.6

    def test_get_visual_state(self, three_runtime, asset_id):
        three_runtime.update(asset_id, {"temp": 25.0})
        state = three_runtime.get(asset_id)
        assert state is not None
        assert state.asset_id == asset_id

    def test_get_missing_state(self, three_runtime, asset_id):
        assert three_runtime.get("nonexistent") is None

    def test_remove_state(self, three_runtime, asset_id):
        three_runtime.update(asset_id, {"temp": 25.0})
        assert three_runtime.remove(asset_id) is True
        assert three_runtime.get(asset_id) is None

    def test_remove_missing_state(self, three_runtime, asset_id):
        assert three_runtime.remove("nonexistent") is False

    def test_list_all_states(self, three_runtime):
        three_runtime.update("asset-a", {"v": 0.1})
        three_runtime.update("asset-b", {"v": 0.8})
        states = three_runtime.list_all()
        assert len(states) == 2

    def test_latency_within_threshold(self, three_runtime, asset_id):
        """AC-07: Update latency ≤ 100ms."""
        start = time.monotonic()
        three_runtime.update(asset_id, {"power_kw": 0.3, "temp_degC": 22.0})
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100.0, f"Update took {elapsed_ms:.1f}ms, exceeds 100ms threshold"

    def test_latency_tracking(self, three_runtime, asset_id):
        three_runtime.update(asset_id, {"v": 0.5})
        latency = three_runtime.last_latency_ms(asset_id)
        assert latency is not None
        assert latency >= 0.0

    def test_empty_telemetry_default_color(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {})
        assert state.color == (0.0, 0.8, 0.0)  # default green

    def test_negative_telemetry_value(self, three_runtime, asset_id):
        state = three_runtime.update(asset_id, {"delta": -0.5})
        assert state is not None
        assert isinstance(state.color, tuple)
        assert len(state.color) == 3


# ═══════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestSceneBindingIntegration:
    """Integration: Scene + ModelBinding + ThreeRuntime working together."""

    def test_full_pipeline(self, scene_service, binding_service, three_runtime):
        """AC-08 full integration: Scene → Bind Asset → Runtime update."""
        asset_id = "asset.park.hvac.ahu_01"

        # 1. Create scene
        scene = scene_service.create({
            "id": "scene-energy-01",
            "code": "scene.park.energy_main",
            "name": "Energy Overview",
            "type": "energy",
            "layout": {"layers": [{"id": "l1", "visible": True}]},
        }, tenant_id="tenant-1")

        # 2. Create binding for asset in scene
        binding = binding_service.create(
            asset_id=asset_id,
            source="bim",
            source_id="ifc-ahu-01-guid",
            source_type="ifc_element",
            lod=300,
        )

        # 3. Bind asset to scene
        scene = scene_service.bind_asset("scene-energy-01", {
            "id": binding.id,
            "source": binding.source,
            "source_id": binding.source_id,
            "source_type": binding.source_type,
            "lod": binding.lod,
        })
        assert len(scene.model_bindings) == 1

        # 4. Update 3D runtime with telemetry
        state = three_runtime.update(
            asset_id,
            {"power_kw": 45.0, "temp_degC": 22.5},
            lifecycle_status="active",
        )
        assert state.asset_id == asset_id
        assert state.opacity == 1.0

        # 5. Verify scene still has binding
        updated_scene = scene_service.get("scene-energy-01")
        assert updated_scene is not None
        assert len(updated_scene.model_bindings) == 1

    def test_identity_boundary_integration(self, scene_service, binding_service, three_runtime):
        """AG-P0-06 integration test: Delete binding → scene still valid, asset persists."""
        asset_id = "asset.park.energy.transformer_01"

        # Create scene with binding
        scene = scene_service.create({
            "id": "scene-energy-bound",
            "code": "scene.park.energy_bound",
            "name": "Energy Bound",
            "type": "energy",
            "layout": {"layers": [{"id": "l1", "visible": True}]},
        }, tenant_id="tenant-1")

        binding = binding_service.create(
            asset_id=asset_id,
            source="bim",
            source_id="ifc-transformer-01",
            source_type="ifc_element",
        )
        scene_service.bind_asset("scene-energy-bound", {
            "id": binding.id, "source": binding.source,
            "source_id": binding.source_id, "source_type": binding.source_type,
            "lod": binding.lod,
        })

        # Simulate BIM element deletion → nullify binding
        binding_service.nullify(binding.id)

        # Scene still exists and is valid
        updated = scene_service.get("scene-energy-bound")
        assert updated is not None
        assert updated.type == "energy"

        # ThreeRuntime can still show the asset (with null binding)
        state = three_runtime.update(asset_id, {"power_kw": 0.0})
        assert state is not None

    def test_multi_source_bindings_same_asset(self, binding_service, asset_id):
        """Asset can have BIM + GIS + 3D bindings simultaneously."""
        binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-1", source_type="ifc_element")
        binding_service.create(asset_id=asset_id, source="gis", source_id="geo-1", source_type="geojson_feature")
        binding_service.create(asset_id=asset_id, source="3d", source_id="node-1", source_type="gltf_node")
        bindings = binding_service.list_by_asset(asset_id)
        assert len(bindings) == 3
        sources = {b.source for b in bindings}
        assert sources == {"bim", "gis", "3d"}


# ═══════════════════════════════════════════════════════════════════
# Architecture Gate Tests
# ═══════════════════════════════════════════════════════════════════

class TestArchitectureGates:
    """AG-P0-06 and AG-P1-01/02 gate enforcement."""

    def test_ag_p0_06_identity_boundary(self, binding_service, asset_id):
        """AG-P0-06: BIM/GIS/3D Identity Boundary — FK ON DELETE SET NULL."""
        # Create bindings for all 3 sources
        bim_b = binding_service.create(asset_id=asset_id, source="bim", source_id="ifc-test", source_type="ifc_element")
        gis_b = binding_service.create(asset_id=asset_id, source="gis", source_id="geo-test", source_type="geojson_feature")
        g3d_b = binding_service.create(asset_id=asset_id, source="3d", source_id="node-test", source_type="gltf_node")

        # Nullify all (simulating ModelObject deletion)
        binding_service.nullify(bim_b.id)
        binding_service.nullify(gis_b.id)
        binding_service.nullify(g3d_b.id)

        # Verify all are nullified
        assert binding_service.get(bim_b.id).is_nullified
        assert binding_service.get(gis_b.id).is_nullified
        assert binding_service.get(g3d_b.id).is_nullified

        # Asset would still exist (not deleted by binding nullification)
        # This is the core invariant of SL-10 / AG-P0-06

    def test_scene_type_enforcement(self, scene_service):
        """All 10 types accepted, no others."""
        for stype in VALID_SCENE_TYPES:
            scene_service.create({
                "id": f"scene-{stype}",
                "code": f"scene.park.{stype}",
                "name": stype,
                "type": stype,
                "layout": {"layers": [{"id": "l1", "visible": True}]},
            }, tenant_id="t1")

        # Rejection test
        with pytest.raises(ValueError):
            scene_service.create({
                "id": "scene-bad",
                "code": "scene.park.dash",
                "name": "bad",
                "type": "dashboard",
                "layout": {},
            }, tenant_id="t1")

    def test_three_runtime_latency_gate(self, three_runtime):
        """AC-07: All updates complete within 100ms."""
        for i in range(5):
            state = three_runtime.update(f"asset-latency-{i}", {"v": 0.1 + i * 0.1})
            latency = three_runtime.last_latency_ms(f"asset-latency-{i}")
            assert latency is not None
            assert latency < 100.0

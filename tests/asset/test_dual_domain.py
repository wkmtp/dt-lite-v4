"""UAA-02 Asset, Template, CompositeAsset & Relationship Tests."""
import pytest

from services.core.src.asset.service import Asset, AssetService, ASSET_CODE_PATTERN
from services.core.src.asset.template.service import AssetTemplate, AssetTemplateService
from services.core.src.asset.composite.engine import (
    CompositeAsset, CompositeAssetEngine, MAX_TREE_DEPTH, MAX_GRAPH_EDGES
)
from services.core.src.asset.relationship.service import (
    RelationshipService, VALID_RELATIONSHIP_TYPES, VALID_DIRECTIONS
)


# ---------------------------------------------------------------------------
# AC-01: Asset CRUD with naming convention
# ---------------------------------------------------------------------------
class TestAssetCRUD:
    """AC-01: Asset CRUD with naming convention enforcement."""

    def test_create_valid_asset(self):
        service = AssetService()
        asset = service.create({
            "id": "asset-001",
            "code": "asset.park.facility.ahu",
            "name": "AHU-001",
            "category": "facility",
        }, tenant_id="tenant-1")
        assert asset.id == "asset-001"
        assert asset.code == "asset.park.facility.ahu"
        assert asset.category == "facility"
        assert asset.lifecycle_status == "provisioned"

    def test_create_asset_invalid_naming(self):
        """Invalid naming convention must be rejected."""
        service = AssetService()
        invalid_codes = [
            "building-ahu",
            "asset.park.ahu",
            "asset.industry.energy",
            "asset.park.facility.AHU",
            "asset.park.facility.ahu-1",
        ]
        for code in invalid_codes:
            with pytest.raises(ValueError):
                service.create({
                    "id": f"asset-{code}",
                    "code": code,
                    "name": "Test",
                    "category": "facility",
                }, tenant_id="t1")

    def test_create_asset_valid_factory(self):
        service = AssetService()
        asset = service.create({
            "id": "asset-factory-001",
            "code": "asset.factory.production.machine",
            "name": "CNC-001",
            "category": "production",
        }, tenant_id="tenant-factory")
        assert asset.code == "asset.factory.production.machine"
        assert asset.category == "production"

    def test_get_asset(self):
        service = AssetService()
        service.create({"id": "a1", "code": "asset.park.energy.transformer",
                        "name": "T1", "category": "energy"}, tenant_id="t1")
        asset = service.get("a1")
        assert asset is not None
        assert asset.code == "asset.park.energy.transformer"

    def test_list_by_code_prefix(self):
        service = AssetService()
        service.create({"id": "a1", "code": "asset.park.energy.t1",
                        "name": "T1", "category": "energy"}, tenant_id="t1")
        service.create({"id": "a2", "code": "asset.park.energy.t2",
                        "name": "T2", "category": "energy"}, tenant_id="t1")
        service.create({"id": "a3", "code": "asset.park.hvac.ahu",
                        "name": "AHU", "category": "facility"}, tenant_id="t1")
        results = service.list_by_code_prefix("asset.park.energy.", tenant_id="t1")
        assert len(results) == 2

    def test_list_by_category(self):
        service = AssetService()
        service.create({"id": "a1", "code": "asset.park.energy.t1",
                        "name": "T1", "category": "energy"}, tenant_id="t1")
        service.create({"id": "a2", "code": "asset.park.energy.t2",
                        "name": "T2", "category": "energy"}, tenant_id="t1")
        results = service.list_by_category("energy", tenant_id="t1")
        assert len(results) == 2

    def test_lifecycle_transition(self):
        service = AssetService()
        asset = service.create({"id": "a1", "code": "asset.park.hvac.ahu",
                                "name": "AHU", "category": "facility"}, tenant_id="t1")
        assert asset.lifecycle_status == "provisioned"
        asset.activate()
        assert asset.lifecycle_status == "active"
        asset.decommission()
        assert asset.lifecycle_status == "decommissioned"
        asset.retire()
        assert asset.lifecycle_status == "retired"

    def test_update_asset(self):
        service = AssetService()
        asset = service.create({"id": "a1", "code": "asset.park.hvac.ahu",
                                "name": "AHU", "category": "facility"}, tenant_id="t1")
        updated = service.update("a1", {"name": "AHU-Updated", "attributes": {"floor": 3}})
        assert updated.name == "AHU-Updated"
        assert updated.attributes["floor"] == 3

    def test_delete_asset(self):
        service = AssetService()
        service.create({"id": "a1", "code": "asset.park.hvac.ahu",
                        "name": "AHU", "category": "facility"}, tenant_id="t1")
        result = service.delete("a1")
        assert result is True
        asset = service.get("a1")
        assert asset.lifecycle_status == "retired"


# ---------------------------------------------------------------------------
# AC-02: AssetTemplate versioning and instantiation
# ---------------------------------------------------------------------------
class TestAssetTemplate:
    """AC-02: AssetTemplate versioning, instantiation with JSON Schema params."""

    def test_register_template(self):
        service = AssetTemplateService()
        template = AssetTemplate(
            id="tpl-001",
            code="asset.park.hvac.ahu",
            name="AHU Template",
            version="1.0.0",
            asset_schema={"type": "object"},
            capability_templates=[{"code": "capability.hvac.cooling"}],
            instantiation_params_schema={"required": ["name", "floor"]},
        )
        service.register(template)
        assert service.get("tpl-001") is not None

    def test_instantiate_template(self):
        service = AssetTemplateService()
        service.register(AssetTemplate(
            id="tpl-001",
            code="asset.park.hvac.ahu",
            name="AHU Template",
            version="1.0.0",
            asset_schema={"type": "object"},
            capability_templates=[{"code": "capability.hvac.cooling"}],
            instantiation_params_schema={"required": ["name"]},
        ))
        asset = service.instantiate("tpl-001", {"name": "AHU-001", "instance_id": "001"}, tenant_id="t1")
        assert asset.code == "asset.park.hvac.ahu"
        assert "capability.hvac.cooling" in asset.capabilities

    def test_instantiate_missing_param(self):
        service = AssetTemplateService()
        service.register(AssetTemplate(
            id="tpl-001",
            code="asset.park.hvac.ahu",
            name="AHU Template",
            version="1.0.0",
            asset_schema={"type": "object"},
            instantiation_params_schema={"required": ["name"]},
        ))
        with pytest.raises(ValueError):
            service.instantiate("tpl-001", {}, tenant_id="t1")


# ---------------------------------------------------------------------------
# AC-03/04/05: CompositeAsset tree+graph, inheritance, aggregation
# ---------------------------------------------------------------------------
class TestCompositeAsset:
    """AC-03: Tree+Graph composition; AC-04: Capability inheritance; AC-05: Aggregation."""

    def test_create_composite(self):
        engine = CompositeAssetEngine()
        composite = engine.create(
            id="comp-001",
            code="asset.park.spatial.building_a",
            name="Building A",
            children=[
                {"ref": "asset-1", "type": "contains", "depth": 1},
                {"ref": "asset-2", "type": "contains", "depth": 1},
            ],
            aggregation_rules={"total_power": {"function": "sum"}},
        )
        assert composite.id == "comp-001"
        assert len(composite.composition_tree) == 2

    def test_depth_limit(self):
        engine = CompositeAssetEngine()
        with pytest.raises(ValueError, match="depth"):
            engine.create(
                id="comp-deep",
                code="asset.park.spatial.deep",
                name="Deep",
                children=[{"ref": "a", "type": "contains", "depth": 11}],
            )

    def test_edge_limit(self):
        engine = CompositeAssetEngine()
        children = [{"ref": f"asset-{i}", "type": "contains"} for i in range(1001)]
        with pytest.raises(ValueError, match="1001"):
            engine.create(
                id="comp-many",
                code="asset.park.spatial.many",
                name="Many",
                children=children,
            )

    def test_capability_inheritance_lifo(self):
        engine = CompositeAssetEngine()
        engine.create(
            id="comp-002",
            code="asset.park.spatial.zone_1",
            name="Zone 1",
            children=[{"ref": "asset-a", "type": "contains"}, {"ref": "asset-b", "type": "contains"}],
        )
        caps, conflicts = engine.compute_capability_inheritance(
            "comp-002",
            {"asset-a": ["monitoring", "alarm"], "asset-b": ["monitoring", "climate"]},
        )
        assert "monitoring" in caps
        assert "alarm" in caps
        assert "climate" in caps
        assert len(conflicts) == 1
        assert conflicts[0]["capability_code"] == "monitoring"

    def test_aggregation_sum(self):
        engine = CompositeAssetEngine()
        engine.create(
            id="comp-sum",
            code="asset.park.energy.subpanel",
            name="Subpanel",
            children=[
                {"ref": "a1", "type": "contains", "weight": 1.0},
                {"ref": "a2", "type": "contains", "weight": 1.0},
            ],
            aggregation_rules={"total": {"function": "sum"}},
        )
        results = engine.compute_aggregation("comp-sum", {
            "a1": {"total": 100.0},
            "a2": {"total": 200.0},
        })
        assert results["total"] == 300.0

    def test_aggregation_avg(self):
        engine = CompositeAssetEngine()
        engine.create(
            id="comp-avg",
            code="asset.park.environment.floor",
            name="Floor",
            children=[{"ref": "a1", "type": "contains"}, {"ref": "a2", "type": "contains"}],
            aggregation_rules={"avg_temp": {"function": "avg"}},
        )
        results = engine.compute_aggregation("comp-avg", {
            "a1": {"avg_temp": 22.0},
            "a2": {"avg_temp": 26.0},
        })
        assert results["avg_temp"] == 24.0

    def test_aggregation_weighted_avg(self):
        engine = CompositeAssetEngine()
        engine.create(
            id="comp-wavg",
            code="asset.park.energy.distribution",
            name="Distribution",
            children=[
                {"ref": "a1", "type": "contains", "weight": 0.7},
                {"ref": "a2", "type": "contains", "weight": 0.3},
            ],
            aggregation_rules={"weighted_power": {"function": "weighted_avg"}},
        )
        results = engine.compute_aggregation("comp-wavg", {
            "a1": {"weighted_power": 100.0},
            "a2": {"weighted_power": 200.0},
        })
        assert abs(results["weighted_power"] - 130.0) < 0.01

    def test_aggregation_all_8_functions(self):
        """Verify all 8 aggregation functions are accepted."""
        engine = CompositeAssetEngine()
        engine.create(
            id="comp-funcs",
            code="asset.park.test.funcs",
            name="Functions",
            children=[{"ref": "a1", "type": "contains"}],
            aggregation_rules={
                "f_sum": {"function": "sum"},
                "f_avg": {"function": "avg"},
                "f_min": {"function": "min"},
                "f_max": {"function": "max"},
                "f_count": {"function": "count"},
                "f_latest": {"function": "latest"},
                "f_weighted": {"function": "weighted_avg"},
                "f_custom": {"function": "custom_expr"},
            },
        )
        results = engine.compute_aggregation("comp-funcs", {"a1": {"f_sum": 10.0, "f_avg": 5.0}})
        assert results["f_sum"] == 10.0

    def test_invalid_aggregation_function(self):
        engine = CompositeAssetEngine()
        with pytest.raises(ValueError, match="function"):
            engine.create(
                id="comp-bad",
                code="asset.park.test.bad",
                name="Bad",
                children=[],
                aggregation_rules={"x": {"function": "invalid_func"}},
            )

    def test_tree_acyclic(self):
        engine = CompositeAssetEngine()
        engine.create(
            id="comp-cycle",
            code="asset.park.test.cycle",
            name="Cycle",
            children=[{"ref": "a", "type": "contains"}],
        )
        # No cycle
        assert engine.validate_tree_acyclic("comp-cycle", {"a": []}) is True
        # Cycle: a → b → a
        assert engine.validate_tree_acyclic("comp-cycle", {"a": ["b"], "b": ["a"]}) is False


# ---------------------------------------------------------------------------
# AC-06: Relationship directed, typed, bidirectional sync
# ---------------------------------------------------------------------------
class TestRelationship:
    """AC-06: Relationship CRUD, cascade, bidirectional sync."""

    def test_create_relationship(self):
        service = RelationshipService()
        rel = service.create("asset-a", "asset-b", "contains", "directed")
        assert rel.source_id == "asset-a"
        assert rel.target_id == "asset-b"
        assert rel.type == "contains"
        assert rel.direction == "directed"

    def test_create_bidirectional(self):
        service = RelationshipService()
        rel = service.create("asset-a", "asset-b", "feeds", "bidirectional")
        synced = service.sync_bidirectional(rel.id)
        assert synced is not None
        # Reverse relationship should exist
        reverse = service.get(f"rel-asset-b-asset-a-{rel.type}")
        assert reverse is not None
        assert reverse.direction == "bidirectional"

    def test_invalid_type(self):
        service = RelationshipService()
        with pytest.raises(ValueError):
            service.create("a", "b", "invalid_type")

    def test_self_reference(self):
        service = RelationshipService()
        with pytest.raises(ValueError):
            service.create("a", "a", "contains")

    def test_cascade_option_none(self):
        service = RelationshipService()
        rel = service.create("a", "b", "contains", cascade_option="none")
        assert rel.cascade_option == "none"

    def test_cascade_option_delete(self):
        service = RelationshipService()
        rel = service.create("a", "b", "contains", cascade_option="delete")
        assert rel.cascade_option == "delete"


# ---------------------------------------------------------------------------
# AC-07: Dual-domain test — Building/HVAC + ProductionLine/Machine
# ---------------------------------------------------------------------------
class TestDualDomain:
    """AC-07: Building+HVAC and ProductionLine+Machine coexist with zero conflicts."""

    def test_building_and_production_coexist(self):
        """Park and factory assets must coexist in same runtime."""
        asset_svc = AssetService()
        template_svc = AssetTemplateService()
        rel_svc = RelationshipService()
        comp_engine = CompositeAssetEngine()

        # Park domain: Building + HVAC
        building = asset_svc.create({
            "id": "building-1",
            "code": "asset.park.spatial.building_a",
            "name": "Building A",
            "category": "environment",
        }, tenant_id="park-tenant")
        ahu = asset_svc.create({
            "id": "ahu-1",
            "code": "asset.park.hvac.ahu",
            "name": "AHU-001",
            "category": "facility",
        }, tenant_id="park-tenant")

        # Factory domain: ProductionLine + Machine
        production_line = asset_svc.create({
            "id": "pline-1",
            "code": "asset.factory.production.line_a",
            "name": "Production Line A",
            "category": "production",
        }, tenant_id="factory-tenant")
        machine = asset_svc.create({
            "id": "machine-1",
            "code": "asset.factory.production.machine",
            "name": "CNC-001",
            "category": "production",
        }, tenant_id="factory-tenant")

        # Verify all assets exist and are isolated by tenant
        park_assets = asset_svc.all("park-tenant")
        factory_assets = asset_svc.all("factory-tenant")
        assert len(park_assets) == 2
        assert len(factory_assets) == 2

        # Template instantiation works in both domains
        template_svc.register(AssetTemplate(
            id="tpl-hvac", code="asset.park.hvac.ahu", name="AHU Template",
            version="1.0.0", asset_schema={"type": "object"},
            instantiation_params_schema={"required": ["name"]},
        ))
        instantiated = template_svc.instantiate("tpl-hvac", {"name": "AHU-002", "instance_id": "002"}, tenant_id="park-tenant")
        assert instantiated.code == "asset.park.hvac.ahu"

        # Composite asset with Building children
        comp = comp_engine.create(
            id="comp-building",
            code="asset.park.spatial.building_a",
            name="Building A Composite",
            children=[{"ref": "ahu-1", "type": "contains"}],
            aggregation_rules={"total_power": {"function": "sum"}},
        )
        assert comp is not None

        # Relationships across domains
        rel = rel_svc.create("building-1", "ahu-1", "contains")
        assert rel is not None
        rel2 = rel_svc.create("pline-1", "machine-1", "contains")
        assert rel2 is not None

        # Zero conflicts: all operations succeed
        assert True

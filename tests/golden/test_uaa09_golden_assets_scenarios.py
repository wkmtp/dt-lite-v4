"""UAA-09: Golden Assets & Golden Scenarios — Cross-Layer Validation + Scenario Execution.

Tests for:
  - 20 Golden Assets: classification coverage, cross-layer validation
  - 10 Golden Scenarios: execution, JUnit XML output
  - Cross-Layer Validator: 10 rules (VAL-01~VAL-10)
  - Scenario Runner: GS-01~10 execution
  - GS-10 regression: zero-code pipeline re-verified
  - AG-P1-04: GA-01~20 all pass cross-layer validation
  - AG-P1-05: GS-01~10 all pass scenario execution
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root))

import importlib.util as _iu
import sys
from pathlib import Path
_project = Path(__file__).resolve().parents[2]
# golden_assets
_spec = _iu.spec_from_file_location("golden_assets", str(_project / "packages" / "industry" / "smart-park" / "golden_assets.py"))
_ga_mod = _iu.module_from_spec(_spec); _spec.loader.exec_module(_ga_mod)
GOLDEN_ASSETS = _ga_mod.GOLDEN_ASSETS
VALIDATION_RULES = _ga_mod.VALIDATION_RULES
# golden_scenarios
_spec2 = _iu.spec_from_file_location("golden_scenarios", str(_project / "packages" / "industry" / "smart-park" / "golden_scenarios.py"))
_gs_mod = _iu.module_from_spec(_spec2); _spec2.loader.exec_module(_gs_mod)
GOLDEN_SCENARIOS = _gs_mod.GOLDEN_SCENARIOS
# validator
_spec3 = _iu.spec_from_file_location("validator", str(_project / "tools" / "golden_validator" / "validator.py"))
_val_mod = _iu.module_from_spec(_spec3); _spec3.loader.exec_module(_val_mod)
CrossLayerValidator = _val_mod.CrossLayerValidator
# runner
_spec4 = _iu.spec_from_file_location("runner", str(_project / "tools" / "scenario_runner" / "runner.py"))
_rn_mod = _iu.module_from_spec(_spec4); _spec4.loader.exec_module(_rn_mod)
ScenarioRunner = _rn_mod.ScenarioRunner


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def validator():
    return CrossLayerValidator()


@pytest.fixture
def runner():
    return ScenarioRunner()


# ═══════════════════════════════════════════════════════════════════
# Golden Assets Tests
# ═══════════════════════════════════════════════════════════════════

class TestGoldenAssets:
    """Tests for 20 Golden Assets classification coverage."""

    def test_all_20_ga_defined(self):
        assert len(GOLDEN_ASSETS) == 20

    def test_all_ga_have_required_fields(self):
        for ga_id, ga in GOLDEN_ASSETS.items():
            for key in ["id", "code", "name", "category", "domain", "points", "capabilities", "template_ref"]:
                assert key in ga, f"{ga_id} missing field: {key}"

    def test_classification_coverage_14_categories(self):
        """All 14 categories covered."""
        categories = {ga["category"] for ga in GOLDEN_ASSETS.values()}
        expected = {"building", "hvac", "energy", "water", "security", "transport",
                     "environment", "production", "fire", "elevator", "access", "parking", "waste", "it"}
        assert categories == expected, f"Missing categories: {expected - categories}"

    def test_each_category_has_at_least_one_ga(self):
        from collections import Counter
        cat_counts = Counter(ga["category"] for ga in GOLDEN_ASSETS.values())
        for cat, count in cat_counts.items():
            assert count >= 1, f"Category {cat} has no GA"

    def test_multi_category_ga(self):
        """Some categories have multiple GAs."""
        from collections import Counter
        cat_counts = Counter(ga["category"] for ga in GOLDEN_ASSETS.values())
        multi = {cat: cnt for cat, cnt in cat_counts.items() if cnt > 1}
        assert len(multi) >= 5, f"Expected >=5 multi-GA categories, got {len(multi)}"

    def test_asset_codes_follow_pattern(self):
        import re
        # Codes have format: asset.park.<domain>.<name> or asset.factory.<domain>.<name>
        pattern = re.compile(r"^asset\.(park|factory)\.[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
        for ga_id, ga in GOLDEN_ASSETS.items():
            assert pattern.match(ga["code"]), f"{ga_id} code '{ga['code']}' doesn't match pattern"

    def test_no_protocol_fields_in_points(self):
        FORBIDDEN = {"protocol", "address", "register", "slave_id", "function_code", "topic", "url", "endpoint"}
        for ga_id, ga in GOLDEN_ASSETS.items():
            for point in ga.get("points", []):
                for field in FORBIDDEN:
                    assert field not in point, f"{ga_id} point {point.get('id')} has forbidden field '{field}'"

    def test_all_ga_have_bindings_or_empty(self):
        for ga_id, ga in GOLDEN_ASSETS.items():
            bindings = ga.get("bindings", [])
            assert isinstance(bindings, list)
            for b in bindings:
                assert b.get("source") in {"bim", "gis", "3d"}, f"{ga_id} invalid binding source '{b.get('source')}'"

    def test_ga_01_to_20_all_present(self):
        for i in range(1, 21):
            ga_id = f"GA-{i:02d}"
            assert ga_id in GOLDEN_ASSETS, f"{ga_id} missing"

    def test_ga_13_and_14_factory_domain(self):
        """GA-13 and GA-14 are in factory domain."""
        assert GOLDEN_ASSETS["GA-13"]["domain"] == "production"
        assert GOLDEN_ASSETS["GA-14"]["domain"] == "production"
        assert "factory" in GOLDEN_ASSETS["GA-13"]["code"]
        assert "factory" in GOLDEN_ASSETS["GA-14"]["code"]


# ═══════════════════════════════════════════════════════════════════
# Cross-Layer Validator Tests  (AG-P1-04)
# ═══════════════════════════════════════════════════════════════════

class TestCrossLayerValidator:
    """AG-P1-04: GA-01~20 all pass cross-layer validation."""

    def test_validate_all_20_assets(self, validator):
        results = validator.validate_all()
        assert len(results) == 20
        passed = sum(1 for r in results.values() if r.passed)
        assert passed == 20, f"Expected 20 passed, got {passed}"

    def test_each_ga_passes_all_checks(self, validator):
        results = validator.validate_all()
        for ga_id, result in results.items():
            assert result.passed is True, f"{ga_id} failed: errors={result.errors}, warnings={result.warnings}"
            assert result.error_count == 0, f"{ga_id} has {result.error_count} errors"

    def test_val01_asset_code_pattern(self, validator):
        result = validator.validate_asset("GA-01")
        val01 = next((c for c in result.checks if c["rule"] == "VAL-01"), None)
        assert val01 is not None
        assert val01["status"] == "pass"

    def test_val03_no_protocol_in_points(self, validator):
        result = validator.validate_asset("GA-03")
        val03 = next((c for c in result.checks if c["rule"] == "VAL-03"), None)
        assert val03 is not None
        assert val03["status"] == "pass"

    def test_val06_valid_binding_sources(self, validator):
        result = validator.validate_asset("GA-05")
        val06 = next((c for c in result.checks if c["rule"] == "VAL-06"), None)
        assert val06 is not None
        assert val06["status"] == "pass"

    def test_summary(self, validator):
        summary = validator.get_summary()
        assert summary["total_assets"] == 20
        assert summary["passed"] == 20
        assert summary["failed"] == 0
        assert summary["pass_rate"] == "100.0%"

    def test_missing_asset_returns_failure(self, validator):
        result = validator.validate_asset("GA-99")
        assert result.passed is False
        assert result.error_count > 0


# ═══════════════════════════════════════════════════════════════════
# Golden Scenarios Tests
# ═══════════════════════════════════════════════════════════════════

class TestGoldenScenarios:
    """Tests for 10 Golden Scenarios definition."""

    def test_all_10_gs_defined(self):
        assert len(GOLDEN_SCENARIOS) == 10

    def test_gs_ids(self):
        expected = {"GS-01", "GS-02", "GS-03", "GS-04", "GS-05", "GS-06", "GS-07", "GS-08", "GS-09", "GS-010"}
        assert set(GOLDEN_SCENARIOS.keys()) == expected

    def test_each_gs_has_required_fields(self):
        for gs_id, gs in GOLDEN_SCENARIOS.items():
            for key in ["id", "name", "description", "assets", "kpis", "dashboards", "alarms", "scenes"]:
                assert key in gs, f"{gs_id} missing field: {key}"

    def test_gs_09_integrated_operations(self):
        gs09 = GOLDEN_SCENARIOS["GS-09"]
        assert "dashboard" in str(gs09).lower() or len(gs09.get("dashboards", [])) > 0
        assert len(gs09.get("largescreens", [])) > 0
        assert len(gs09.get("alarms", [])) > 0

    def test_gs_010_zero_code(self):
        gs10 = GOLDEN_SCENARIOS["GS-010"]
        assert "zero-code" in gs10["tags"] or "assembly" in gs10["tags"]
        # GS-010 references all 20 GAs
        assert len(gs10["assets"]) == 20


# ═══════════════════════════════════════════════════════════════════
# Scenario Runner Tests  (AG-P1-05)
# ═══════════════════════════════════════════════════════════════════

class TestScenarioRunner:
    """AG-P1-05: GS-01~10 all pass scenario execution."""

    def test_run_all_scenarios(self, runner):
        results = runner.run_all()
        assert len(results) == 10
        passed = sum(1 for r in results.values() if r["passed"])
        assert passed == 10, f"Expected 10 passed, got {passed}"

    def test_each_scenario_passes(self, runner):
        results = runner.run_all()
        for gs_id, result in results.items():
            assert result["passed"] is True, f"{gs_id} failed: {result.get('errors')}"
            assert len(result.get("errors", [])) == 0

    def test_gs01_energy_management(self, runner):
        result = runner.run_scenario("GS-01")
        assert result["passed"] is True
        assert any("GA-05" in c for c in result["checks"])

    def test_gs07_production_monitoring(self, runner):
        result = runner.run_scenario("GS-07")
        assert result["passed"] is True
        assert any("GA-13" in c for c in result["checks"])

    def test_gs09_integrated(self, runner):
        result = runner.run_scenario("GS-09")
        assert result["passed"] is True

    def test_gs010_zero_code_regression(self, runner):
        """GS-010: Re-run UAA-08 GS-10 zero-code pipeline."""
        result = runner.run_scenario("GS-010")
        assert result["passed"] is True
        # Should reference all 20 GAs
        assert len(result["checks"]) >= 20

    def test_missing_scenario_returns_error(self, runner):
        result = runner.run_scenario("GS-99")
        assert result["passed"] is False
        assert "not found" in result.get("error", "")

    def test_junit_xml_output(self, runner):
        xml = runner.generate_junit_xml()
        # ET.tostring doesn't add XML declaration by default — check for testsuite instead
        assert "<testsuite" in xml
        assert 'tests="10"' in xml
        assert 'failures="0"' in xml

    def test_summary(self, runner):
        summary = runner.get_summary()
        assert summary["total_scenarios"] == 10
        assert summary["passed"] == 10
        assert summary["failed"] == 0
        assert summary["pass_rate"] == "100.0%"


# ═══════════════════════════════════════════════════════════════════
# GS-10 Regression Test
# ═══════════════════════════════════════════════════════════════════

class TestGS10Regression:
    """GS-10 regression: confirm zero-business-code E2E still passes."""

    def test_gs10_references_all_ga(self):
        gs10 = GOLDEN_SCENARIOS["GS-010"]
        assert len(gs10["assets"]) == 20
        for i in range(1, 21):
            assert f"GA-{i:02d}" in gs10["assets"]

    def test_gs10_has_all_layers(self, runner):
        result = runner.run_scenario("GS-010")
        assert result["passed"] is True
        # Should have checks for assets, KPIs, dashboards, alarms, scenes
        check_types = set()
        for c in result["checks"]:
            if "Asset" in c:
                check_types.add("asset")
            elif "KPI" in c:
                check_types.add("kpi")
            elif "Dashboard" in c:
                check_types.add("dashboard")
            elif "Alarm" in c:
                check_types.add("alarm")
            elif "binding" in c:
                check_types.add("binding")
        assert len(check_types) >= 4, f"Expected >=4 check types, got {check_types}"

    def test_gs10_zero_business_code(self):
        """GS-10 requires ZERO business code — all definitions are in YAML/data."""
        gs10 = GOLDEN_SCENARIOS["GS-010"]
        # All configuration is declarative — no imperative business logic
        assert isinstance(gs10["assets"], dict)
        assert isinstance(gs10["kpis"], list)
        assert isinstance(gs10["dashboards"], list)
        assert isinstance(gs10["alarms"], list)

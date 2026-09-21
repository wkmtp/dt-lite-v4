"""Scenario Runner — executes Golden Scenarios and outputs JUnit XML report."""
import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_p = Path(__file__).resolve().parents[2]
if str(_p) not in sys.path: sys.path.insert(0, str(_p))
import importlib.util as _iu
_spec = _iu.spec_from_file_location("golden_scenarios", str(_p / "packages" / "industry" / "smart-park" / "golden_scenarios.py"))
_m = _iu.module_from_spec(_spec); _spec.loader.exec_module(_m)
GOLDEN_SCENARIOS = _m.GOLDEN_SCENARIOS
_spec2 = _iu.spec_from_file_location("validator", str(_p / "tools" / "golden_validator" / "validator.py"))
_m2 = _iu.module_from_spec(_spec2); _spec2.loader.exec_module(_m2)
CrossLayerValidator = _m2.CrossLayerValidator


class ScenarioRunner:
    """Runs Golden Scenarios, validates against expected state, outputs JUnit XML."""

    def __init__(self) -> None:
        self._results: dict[str, dict[str, Any]] = {}

    def run_scenario(self, scenario_id: str) -> dict[str, Any]:
        """Execute a single Golden Scenario."""
        scenario = GOLDEN_SCENARIOS.get(scenario_id)
        if not scenario:
            return {"id": scenario_id, "passed": False, "error": f"Scenario {scenario_id} not found"}

        result = {
            "id": scenario_id,
            "name": scenario["name"],
            "passed": True,
            "checks": [],
            "errors": [],
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Check 1: All referenced assets exist
        import importlib.util as _iu2
        _p2 = Path(__file__).resolve().parents[2]
        _spec_a = _iu2.spec_from_file_location("golden_assets", str(_p2 / "packages" / "industry" / "smart-park" / "golden_assets.py"))
        _m_a = _iu2.module_from_spec(_spec_a); _spec_a.loader.exec_module(_m_a)
        _GOLDEN_ASSETS = _m_a.GOLDEN_ASSETS
        for asset_id, role in scenario.get("assets", {}).items():
            if asset_id not in _GOLDEN_ASSETS:
                result["passed"] = False
                result["errors"].append(f"Asset {asset_id} not found")
            else:
                result["checks"].append(f"Asset {asset_id} ({role}) exists")

        # Check 2: KPIs are valid
        _kpi_defs = {"energy_intensity", "equipment_availability", "occupant_comfort", "water_usage_rate",
                      "security_incident_rate", "parking_occupancy", "hvac_efficiency", "fire_alarm_response_time",
                      "oee_total", "carbon_footprint", "light_level_compliance", "elevator_availability",
                      "access_control_pass_rate", "waste_collection_rate", "green_space_ratio", "it_uptime",
                      "network_latency_p95", "tenant_satisfaction", "emergency_evacuation_time", "cost_per_sqm"}
        for kpi in scenario.get("kpis", []):
            if kpi in _kpi_defs:
                result["checks"].append(f"KPI {kpi} defined")
            else:
                result["passed"] = False
                result["errors"].append(f"KPI {kpi} not found")

        # Check 3: Dashboard types are valid
        valid_dashboard_types = {"energy", "hvac", "water", "security", "transport",
                                  "environment", "production", "fire", "overview", "custom"}
        for dash in scenario.get("dashboards", []):
            if dash.get("type") in valid_dashboard_types:
                result["checks"].append(f"Dashboard type '{dash['type']}' valid")
            else:
                result["passed"] = False
                result["errors"].append(f"Invalid dashboard type '{dash.get('type')}'")

        # Check 4: Alarm severities are valid
        valid_severities = {"P1", "P2", "P3", "P4"}
        for alarm in scenario.get("alarms", []):
            if alarm.get("severity") in valid_severities:
                result["checks"].append(f"Alarm severity '{alarm['severity']}' valid")
            else:
                result["passed"] = False
                result["errors"].append(f"Invalid alarm severity '{alarm.get('severity')}'")

        # Check 5: Scene bindings are valid
        valid_sources = {"bim", "gis", "3d"}
        for scene in scenario.get("scenes", []):
            for binding in scene.get("bindings", []):
                if binding in valid_sources:
                    result["checks"].append(f"Scene binding '{binding}' valid")
                else:
                    result["passed"] = False
                    result["errors"].append(f"Invalid binding '{binding}'")

        self._results[scenario_id] = result
        return result

    def run_all(self) -> dict[str, dict[str, Any]]:
        """Run all 10 Golden Scenarios."""
        for scenario_id in GOLDEN_SCENARIOS:
            self.run_scenario(scenario_id)
        return self._results

    def generate_junit_xml(self) -> str:
        """Generate JUnit XML report."""
        results = self.run_all()

        suite = ET.Element("testsuite")
        suite.set("name", "UAA-09 Golden Scenarios")
        suite.set("tests", str(len(results)))
        suite.set("failures", str(sum(1 for r in results.values() if not r["passed"])))
        suite.set("errors", "0")
        suite.set("time", "1.0")
        suite.set("timestamp", datetime.now(timezone.utc).isoformat())

        for scenario_id, result in results.items():
            testcase = ET.SubElement(suite, "testcase")
            testcase.set("name", f"{scenario_id} {result['name']}")
            testcase.set("classname", "GoldenScenarios")

            if not result["passed"]:
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", "; ".join(result.get("errors", [])))
                failure.text = "; ".join(result.get("errors", []))

            # System out with checks
            if result.get("checks"):
                sysout = ET.SubElement(testcase, "system-out")
                sysout.text = "\n".join(result["checks"])

        return ET.tostring(suite, encoding="unicode")

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary."""
        results = self.run_all()
        total = len(results)
        passed = sum(1 for r in results.values() if r["passed"])
        return {
            "total_scenarios": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "0%",
        }

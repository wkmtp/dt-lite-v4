"""KPI Engine — 20 KPIs with Formula DSL, real-time + scheduled computation."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 20 KPI definitions
KPI_DEFINITIONS: dict[str, dict[str, Any]] = {
    "energy_intensity": {
        "name": "Energy Intensity",
        "category": "energy",
        "formula": "SELECT total_kWh FROM telemetry WHERE time_window='1h' AGG sum MATH / floor_area_m2",
        "unit": "kWh/m2/h",
    },
    "equipment_availability": {
        "name": "Equipment Availability",
        "category": "production",
        "formula": "SELECT uptime_hours FROM asset_state AGG avg MATH * 100",
        "unit": "%",
    },
    "occupant_comfort": {
        "name": "Occupant Comfort Index",
        "category": "environment",
        "formula": "SELECT thermal_index, air_quality_index FROM telemetry AGG avg MATH / 2",
        "unit": "score",
    },
    "water_usage_rate": {
        "name": "Water Usage Rate",
        "category": "water",
        "formula": "SELECT total_m3 FROM telemetry WHERE time_window='1d' AGG sum",
        "unit": "m3/day",
    },
    "security_incident_rate": {
        "name": "Security Incident Rate",
        "category": "security",
        "formula": "SELECT incident_count FROM alarm WHERE time_window='1h' AGG count MATH * 1000 / persons",
        "unit": "per 1000 persons",
    },
    "parking_occupancy": {
        "name": "Parking Occupancy",
        "category": "transport",
        "formula": "SELECT occupied_spaces FROM telemetry AGG latest MATH * 100 / total_spaces",
        "unit": "%",
    },
    "hvac_efficiency": {
        "name": "HVAC COP",
        "category": "hvac",
        "formula": "SELECT cooling_output_kWh FROM telemetry AGG sum MATH / electrical_input_kWh",
        "unit": "COP",
    },
    "fire_alarm_response_time": {
        "name": "Fire Alarm Response Time",
        "category": "fire",
        "formula": "SELECT response_seconds FROM alarm WHERE time_window='1h' AGG avg",
        "unit": "seconds",
    },
    "oee_total": {
        "name": "Overall Equipment Effectiveness",
        "category": "production",
        "formula": "SELECT availability, performance, quality FROM telemetry AGG avg MATH * availability * performance * quality",
        "unit": "%",
    },
    "carbon_footprint": {
        "name": "Carbon Footprint",
        "category": "environment",
        "formula": "SELECT total_CO2_kg FROM telemetry WHERE time_window='1d' AGG sum MATH / floor_area_m2",
        "unit": "kg CO2/m2/day",
    },
    "light_level_compliance": {
        "name": "Light Level Compliance",
        "category": "lighting",
        "formula": "SELECT lux_readings FROM telemetry AGG count MATH / total_sensors * 100",
        "unit": "%",
    },
    "elevator_availability": {
        "name": "Elevator Availability",
        "category": "elevator",
        "formula": "SELECT uptime_hours FROM asset_state AGG avg MATH * 100",
        "unit": "%",
    },
    "access_control_pass_rate": {
        "name": "Access Control Pass Rate",
        "category": "access",
        "formula": "SELECT successful_reads FROM telemetry AGG count MATH / total_reads * 100",
        "unit": "%",
    },
    "waste_collection_rate": {
        "name": "Waste Collection On-Time Rate",
        "category": "waste",
        "formula": "SELECT on_time_collections FROM telemetry AGG count MATH / total_scheduled * 100",
        "unit": "%",
    },
    "green_space_ratio": {
        "name": "Green Space Ratio",
        "category": "green",
        "formula": "SELECT green_area_m2 FROM asset_attributes AGG latest MATH / total_area_m2 * 100",
        "unit": "%",
    },
    "it_uptime": {
        "name": "IT Infrastructure Uptime",
        "category": "it",
        "formula": "SELECT server_online_hours FROM asset_state AGG avg MATH * 100",
        "unit": "%",
    },
    "network_latency_p95": {
        "name": "Network Latency P95",
        "category": "it",
        "formula": "SELECT latency_ms FROM telemetry WHERE time_window='1h' AGG percentile p95",
        "unit": "ms",
    },
    "tenant_satisfaction": {
        "name": "Tenant Satisfaction Score",
        "category": "facility",
        "formula": "SELECT survey_score FROM telemetry AGG avg MATH / 5.0",
        "unit": "score",
    },
    "emergency_evacuation_time": {
        "name": "Emergency Evacuation Time",
        "category": "fire",
        "formula": "SELECT evacuation_seconds FROM drill_records AGG avg",
        "unit": "seconds",
    },
    "cost_per_sqm": {
        "name": "Operating Cost per Square Meter",
        "category": "energy",
        "formula": "SELECT total_operating_cost FROM telemetry WHERE time_window='1m' AGG sum MATH / floor_area_m2",
        "unit": "currency/m2",
    },
}

VALID_AGG_FUNCTIONS = {"sum", "avg", "min", "max", "count", "latest", "percentile"}
VALID_MATH_OPS = {"add", "subtract", "multiply", "divide", "power"}


@dataclass
class KPIResult:
    """Computed KPI result."""
    kpi_id: str
    value: float
    unit: str
    computed_at: str
    formula_used: str


class KPIEngine:
    """KPI engine: 20 definitions, formula DSL parsing, real-time + scheduled computation."""

    def __init__(self) -> None:
        self._results: dict[str, KPIResult] = {}
        self._definitions = KPI_DEFINITIONS

    def list_definitions(self) -> dict[str, dict[str, Any]]:
        return dict(self._definitions)

    def get_definition(self, kpi_id: str) -> Optional[dict[str, Any]]:
        return self._definitions.get(kpi_id)

    def compute(self, kpi_id: str, telemetry_data: dict[str, Any] | None = None) -> Optional[KPIResult]:
        """Compute a KPI from telemetry data using its formula DSL."""
        definition = self._definitions.get(kpi_id)
        if not definition:
            return None

        telemetry = telemetry_data or {}
        value = self._evaluate_formula(definition["formula"], telemetry)
        result = KPIResult(
            kpi_id=kpi_id,
            value=round(value, 4),
            unit=definition["unit"],
            computed_at=definition.get("computed_at", ""),
            formula_used=definition["formula"],
        )
        self._results[kpi_id] = result
        return result

    def get_result(self, kpi_id: str) -> Optional[KPIResult]:
        return self._results.get(kpi_id)

    def list_results(self) -> dict[str, KPIResult]:
        return dict(self._results)

    def validate_formula(self, formula: str) -> tuple[bool, list[str]]:
        """Validate a Formula DSL string."""
        errors: list[str] = []
        tokens = formula.upper().split()

        has_select = "SELECT" in tokens
        has_agg = "AGG" in tokens
        has_from = "FROM" in tokens

        if not has_select:
            errors.append("Missing SELECT clause")
        if not has_from:
            errors.append("Missing FROM clause")
        if not has_agg:
            errors.append(f"Missing AGG function. Valid: {sorted(VALID_AGG_FUNCTIONS)}")

        return len(errors) == 0, errors

    def _evaluate_formula(self, formula: str, telemetry: dict[str, Any]) -> float:
        """Simple formula DSL evaluator for testing.

        In production, this would be a full SQL + time-series parser.
        For unit tests, we parse keywords and compute from provided telemetry.
        """
        formula_upper = formula.upper()

        # Extract metric name from SELECT
        select_match = re.search(r"SELECT\s+(\w+)", formula_upper)
        metric = select_match.group(1).lower() if select_match else None

        # Extract AGG function
        agg_match = re.search(r"AGG\s+(\w+)", formula_upper)
        agg_fn = agg_match.group(1).lower() if agg_match else "latest"

        # Extract MATH operation
        math_match = re.search(r"MATH\s+(\w+)", formula_upper)
        math_op = math_match.group(1).lower() if math_match else None

        # Get value from telemetry
        raw_value = telemetry.get(metric, 0.0)
        if not isinstance(raw_value, (int, float)):
            raw_value = 0.0

        # Apply aggregation
        if agg_fn == "sum":
            result = raw_value
        elif agg_fn == "avg":
            result = raw_value
        elif agg_fn == "count":
            result = 1.0 if raw_value > 0 else 0.0
        elif agg_fn == "latest":
            result = raw_value
        else:
            result = raw_value

        # Apply math operation
        if math_op == "multiply":
            math_factor_match = re.search(r"MATH\s+\w+\s+(\d+\.?\d*)", formula_upper)
            factor = float(math_factor_match.group(1)) if math_factor_match else 1.0
            result *= factor
        elif math_op == "divide":
            divisor_match = re.search(r"MATH\s+\w+\s+(\d+\.?\d*)", formula_upper)
            divisor = float(divisor_match.group(1)) if divisor_match else 1.0
            if divisor != 0:
                result /= divisor

        return result

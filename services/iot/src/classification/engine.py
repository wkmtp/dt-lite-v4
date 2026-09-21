"""Classification Engine — Rule-based + ML optional classification to Universal types."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default YAML-like classification rules (in production, loaded from YAML files)
DEFAULT_RULES: list[dict[str, Any]] = [
    {"pattern": "AHU", "asset_type": "asset.park.hvac.ahu", "point_semantic": "temperature"},
    {"pattern": "Chiller", "asset_type": "asset.park.facility.chiller", "point_semantic": "temperature"},
    {"pattern": "Pump", "asset_type": "asset.park.facility.pump", "point_semantic": "flow"},
    {"pattern": "VFD", "asset_type": "asset.park.energy.vfd", "point_semantic": "power"},
    {"pattern": "Sensor", "asset_type": "asset.park.environment.sensor", "point_semantic": "temperature"},
    {"pattern": "CNC", "asset_type": "asset.factory.production.cnc", "point_semantic": "position"},
    {"pattern": "Robot", "asset_type": "asset.factory.production.robot", "point_semantic": "position"},
    {"pattern": "AGV", "asset_type": "asset.factory.production.agv", "point_semantic": "position"},
    {"pattern": "Meter", "asset_type": "asset.park.energy.meter", "point_semantic": "power"},
]


class ClassificationEngine:
    """
    Classification Engine: external object name → Universal Asset type + Point semantic.
    Rule-based (YAML) with optional ML model fallback.
    """

    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        self._rules = rules or DEFAULT_RULES

    def classify(self, name: str, external_type: str = "") -> dict[str, str]:
        """
        Classify an external object into Universal Asset type + Point semantic.
        Returns {"asset_type": ..., "point_semantic": ...}.
        """
        name_upper = name.upper()
        for rule in self._rules:
            if rule["pattern"].upper() in name_upper:
                return {"asset_type": rule["asset_type"], "point_semantic": rule["point_semantic"]}

        # Fallback: infer from external_type
        type_map = {
            "Sensor": "asset.park.environment.sensor",
            "Meter": "asset.park.energy.meter",
            "Machine": "asset.factory.production.machine",
            "Valve": "asset.park.facility.valve",
            "Damper": "asset.park.hvac.damper",
            "Filter": "asset.park.hvac.filter",
            "Motor": "asset.park.facility.motor",
            "Fan": "asset.park.hvac.fan",
        }
        asset_type = type_map.get(external_type, "asset.park.facility.generic")
        return {"asset_type": asset_type, "point_semantic": "generic"}

    def classify_batch(self, objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Classify a batch of discovered objects."""
        results = []
        for obj in objects:
            classification = self.classify(obj.get("name", ""), obj.get("type", ""))
            results.append({**obj, **classification})
        return results

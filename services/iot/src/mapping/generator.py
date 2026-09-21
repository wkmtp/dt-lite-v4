"""Mapping Generator — Zero-code MappingProfile generation from discovered points."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

PROTOCOL_ADDRESS_PATTERNS = {
    "bacnet": "bacnet:{type}:{instance}:{property}",
    "modbus": "modbus:slave={slave}:fc={fc}:addr={addr}",
    "opcua": "opcua:ns={ns}:{idtype}={id}",
    "mqtt": "mqtt:{topic}",
}


class MappingGenerator:
    """
    Mapping Generator: discovered point → MappingProfile YAML.
    Produces protocol-specific address, scaling hints, polling interval.
    """

    def generate(self, discovered_point: dict[str, Any], protocol: str) -> dict[str, Any]:
        """Generate a MappingProfile from a discovered point."""
        mapping = {
            "protocol": protocol,
            "address": self._generate_address(discovered_point, protocol),
            "scaling": self._infer_scaling(discovered_point),
            "polling_interval": "1s",
            "deadband": 0.01,
            "transform_hints": self._generate_transform_hints(discovered_point),
        }
        logger.info("Generated mapping for %s (%s)", discovered_point.get("object_id"), protocol)
        return mapping

    def _generate_address(self, point: dict[str, Any], protocol: str) -> str:
        if "address" in point:
            return point["address"]
        if protocol == "bacnet":
            return f"bacnet:ai:{hash(point.get('object_id', '0')) % 1000}:presentValue"
        elif protocol == "modbus":
            return f"modbus:slave=1:fc=3:addr={hash(point.get('object_id', '0')) % 65535}"
        elif protocol == "opcua":
            return f"opcua:ns=2;i={hash(point.get('object_id', '0')) % 10000}"
        elif protocol == "mqtt":
            return f"dt-lite/external/{point.get('object_id', 'unknown')}"
        return f"{protocol}:{point.get('object_id', 'unknown')}"

    def _infer_scaling(self, point: dict[str, Any]) -> dict[str, float]:
        unit = point.get("unit", "")
        if unit in ("degC", "K"):
            return {"scale": 1.0, "offset": 0.0}
        if unit == "kW":
            return {"scale": 1.0, "offset": 0.0}
        return {"scale": 1.0, "offset": 0.0}

    def _generate_transform_hints(self, point: dict[str, Any]) -> dict[str, Any]:
        dtype = point.get("data_type", "float32")
        return {"transform_type": "linear", "input_range": self._infer_input_range(dtype),
                "output_range": [0.0, 100.0]}

    def _infer_input_range(self, data_type: str) -> list[float]:
        if data_type == "int16":
            return [-32768.0, 32767.0]
        elif data_type == "float32":
            return [-1e6, 1e6]
        elif data_type == "boolean":
            return [0.0, 1.0]
        return [0.0, 100.0]

    def generate_batch(self, discovered_points: list[dict[str, Any]],
                       protocol: str) -> list[dict[str, Any]]:
        return [self.generate(p, protocol) for p in discovered_points]

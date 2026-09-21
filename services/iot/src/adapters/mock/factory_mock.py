"""Mock Factory (MES/PLC) — 50+ points, OPC UA + Modbus TCP simulation."""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional

from services.iot.src.external.model import ExternalObjectService

logger = logging.getLogger(__name__)


class FactoryMockAdapter:
    """
    Factory Mock: simulates a Production Line with 50+ points.
    Uses the SAME External Object Model contract as BMS Mock.
    Covers MES, PLC, Quality, Recipes, OEE.
    """

    def __init__(self, system_id: str, service: ExternalObjectService) -> None:
        self.system_id = system_id
        self._svc = service
        self._points: dict[str, dict[str, Any]] = {}
        self._build_points()

    def _build_points(self) -> None:
        """Build 50+ realistic factory points."""
        points = [
            # PLC Tags (20 points)
            ("plc-vibration-motor-01", "Vibration Motor 01", "mm/s", "float32", 2.1),
            ("plc-temp-motor-01", "Temperature Motor 01", "degC", "float32", 65.0),
            ("plc-current-motor-01", "Current Motor 01", "A", "float32", 12.5),
            ("plc-voltage-motor-01", "Voltage Motor 01", "V", "float32", 380.0),
            ("plc-speed-conveyor-01", "Conveyor Speed", "m/min", "float32", 1.5),
            ("plc-position-cnc-01", "CNC Position X", "mm", "float32", 125.5),
            ("plc-position-cnc-02", "CNC Position Y", "mm", "float32", 78.3),
            ("plc-position-cnc-03", "CNC Position Z", "mm", "float32", 12.0),
            ("plc-pressure-hydraulic-01", "Hydraulic Pressure", "bar", "float32", 150.0),
            ("plc-flow-coolant-01", "Coolant Flow", "l/min", "float32", 25.0),
            ("plc-cycle-count-01", "Cycle Count", "count", "int16", 1250),
            ("plc-status-cnc-01", "CNC Status", "string", "string", "running"),
            ("plc-status-robot-01", "Robot Status", "string", "string", "running"),
            ("plc-alarm-agv-01", "AGV Alarm", "string", "string", "none"),
            ("plc-position-agv-01", "AGV Position", "string", "string", "station-3"),
            ("plc-temp-oven-01", "Oven Temperature", "degC", "float32", 180.0),
            ("plc-humidity-cleanroom", "Cleanroom Humidity", "%", "float32", 35.0),
            ("plc-power-line-01", "Line Power", "kW", "float32", 45.0),
            ("plc-pressure-pneumatic-01", "Pneumatic Pressure", "bar", "float32", 6.0),
            ("plc-part-count-01", "Part Count", "count", "int16", 320),
            # MES Work Orders (10 points)
            ("mes-wo-001", "Work Order WO-001", "string", "string", "in_progress"),
            ("mes-wo-002", "Work Order WO-002", "string", "string", "pending"),
            ("mes-wo-003", "Work Order WO-003", "string", "string", "completed"),
            ("mes-qty-wo-001", "WO-001 Target Qty", "int16", "int16", 500),
            ("mes-qty-wo-002", "WO-002 Target Qty", "int16", "int16", 300),
            ("mes-yield-01", "Yield Rate", "%", "float32", 97.5),
            ("mes-defect-rate", "Defect Rate", "%", "float32", 1.2),
            ("mes-schedule-start", "Schedule Start", "string", "string", "08:00"),
            ("mes-schedule-end", "Schedule End", "string", "string", "18:00"),
            ("mes-operator-01", "Operator On Shift", "string", "string", "Zhang Wei"),
            # Quality (10 points)
            ("quality-dimension-a", "Dimension A", "mm", "float32", 10.05),
            ("quality-dimension-b", "Dimension B", "mm", "float32", 5.02),
            ("quality-surface-r", "Surface Roughness", "um", "float32", 1.5),
            ("quality-weight", "Part Weight", "g", "float32", 245.0),
            ("quality-color-delta", "Color Delta", "ΔE", "float32", 0.8),
            ("quality-pass-01", "Quality Pass Count", "int16", "int16", 485),
            ("quality-fail-01", "Quality Fail Count", "int16", "int16", 15),
            ("quality-spca-status", "SPC Control Status", "string", "string", "in_control"),
            ("quality-cpk-value", "Cpk Value", "float32", "float32", 1.67),
            ("quality-gauge-id", "Gauge ID", "string", "string", "G-001"),
            # OEE (5 points)
            ("oee-availability", "Availability", "%", "float32", 92.0),
            ("oee-performance", "Performance", "%", "float32", 88.0),
            ("oee-quality", "Quality Rate", "%", "float32", 97.5),
            ("oee-score", "OEE Score", "%", "float32", 78.5),
            ("oee-downtime-min", "Downtime (min)", "int16", "int16", 45),
            # Recipe (5 points)
            ("recipe-name-01", "Recipe Name", "string", "string", "Standard-Part-A"),
            ("recipe-temp-set", "Recipe Temp Set", "degC", "float32", 180.0),
            ("recipe-time-set", "Recipe Time Set", "s", "int16", 300),
            ("recipe-pressure-set", "Recipe Pressure", "bar", "float32", 6.0),
            ("recipe-version", "Recipe Version", "string", "string", "v2.1"),
        ]
        for obj_id, name, unit, dtype, value in points:
            self._points[obj_id] = {
                "name": name, "unit": unit, "data_type": dtype,
                "value": value, "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def discover(self) -> list[dict[str, Any]]:
        """Return all discovered external objects with their points."""
        objects = []
        for obj_id, data in self._points.items():
            proto = "opcua" if any(k in obj_id for k in ["cnc", "robot", "agv"]) else "modbus"
            address = f"{proto}:{obj_id}" if proto == "modbus" else f"ns=2:{obj_id}"
            objects.append({
                "object_id": obj_id,
                "name": data["name"],
                "data_type": data["data_type"],
                "unit": data["unit"],
                "value": data["value"],
                "address": address,
            })
        return objects

    def read_point(self, object_id: str) -> Optional[dict[str, Any]]:
        point = self._points.get(object_id)
        if point:
            if isinstance(point["value"], (int, float)):
                point["value"] = round(point["value"] + random.uniform(-0.3, 0.3), 2)
            point["timestamp"] = datetime.now(timezone.utc).isoformat()
        return point

    def write_point(self, object_id: str, value: Any) -> bool:
        if object_id in self._points:
            self._points[object_id]["value"] = value
            return True
        return False

    def get_point_count(self) -> int:
        return len(self._points)

    def register_with_service(self, service: ExternalObjectService) -> None:
        objects = self.discover()
        for obj in objects:
            ext_obj = service.create_object({
                "id": f"ext-obj-{self.system_id}-{obj['object_id']}",
                "system_id": self.system_id,
                "object_id": obj["object_id"],
                "name": obj["name"],
                "type": self._infer_type(obj["object_id"]),
                "properties": {"unit": obj["unit"], "data_type": obj["data_type"]},
            })
            service.create_point({
                "id": f"ext-pt-{self.system_id}-{obj['object_id']}",
                "object_id": ext_obj.id,
                "name": obj["name"],
                "data_type": obj["data_type"],
                "unit": obj["unit"],
                "address": obj["address"],
            })

    def _infer_type(self, point_id: str) -> str:
        if any(k in point_id for k in ["vibration", "temp", "current", "voltage", "pressure", "flow"]):
            return "Sensor"
        if any(k in point_id for k in ["cnc", "robot", "agv", "conveyor"]):
            return "Machine"
        if any(k in point_id for k in ["wo", "mes", "schedule"]):
            return "WorkOrder"
        if any(k in point_id for k in ["quality", "defect", "yield", "spc", "cpk"]):
            return "Quality"
        if any(k in point_id for k in ["oee"]):
            return "OEE"
        if any(k in point_id for k in ["recipe"]):
            return "Recipe"
        return "Unknown"

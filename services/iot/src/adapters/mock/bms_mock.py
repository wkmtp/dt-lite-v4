"""Mock BMS (Building Management System) — 50+ points, BACnet/IP simulation."""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional

from services.iot.src.external.model import ExternalObjectService

logger = logging.getLogger(__name__)


class BMSMockAdapter:
    """
    BMS Mock: simulates a Building Management System with 50+ points.
    Uses External Object Model contract. Covers HVAC, Lighting, Access, Fire, Elevator.
    """

    def __init__(self, system_id: str, service: ExternalObjectService) -> None:
        self.system_id = system_id
        self._svc = service
        self._points: dict[str, dict[str, Any]] = {}
        self._build_points()

    def _build_points(self) -> None:
        """Build 50+ realistic building points."""
        base_time = datetime.now(timezone.utc)
        points = [
            # HVAC (15 points)
            ("temp-ahu-01", "Temperature AHU-01 Supply", "degC", "float32", 22.5),
            ("temp-ahu-02", "Temperature AHU-02 Supply", "degC", "float32", 23.1),
            ("temp-chiller-01", "Temperature Chiller-01 Out", "degC", "float32", 7.2),
            ("hum-ahu-01", "Humidity AHU-01", "%", "float32", 45.0),
            ("press-damper-01", "Damper Position AHU-01", "%", "float32", 65.0),
            ("flow-water-01", "Water Flow Chiller-01", "l/s", "float32", 12.5),
            ("power-ahu-01", "Power AHU-01", "kW", "float32", 15.2),
            ("power-ahu-02", "Power AHU-02", "kW", "float32", 12.8),
            ("setpoint-ahu-01", "Setpoint AHU-01", "degC", "float32", 22.0),
            ("status-ahu-01", "Status AHU-01", "string", "string", "running"),
            ("status-chiller-01", "Status Chiller-01", "string", "string", "running"),
            ("valve-open-01", "Valve Opening CHW", "%", "float32", 70.0),
            ("temp-return-01", "Return Air Temperature", "degC", "float32", 25.3),
            ("temp-outdoor-01", "Outdoor Air Temperature", "degC", "float32", 32.0),
            ("co2-01", "CO2 Level Zone-1", "ppm", "float32", 450.0),
            # Lighting (10 points)
            ("light-floor1", "Lighting Floor 1", "%", "float32", 80.0),
            ("light-floor2", "Lighting Floor 2", "%", "float32", 60.0),
            ("light-floor3", "Lighting Floor 3", "%", "float32", 0.0),
            ("power-light-01", "Lighting Power Total", "kW", "float32", 5.2),
            ("ctrl-light-01", "Lighting Control Mode", "string", "string", "auto"),
            # Access Control (8 points)
            ("door-main-entrance", "Main Entrance Door", "string", "string", "closed"),
            ("door-service-entrance", "Service Entrance Door", "string", "string", "closed"),
            ("access-card-reader-01", "Card Reader L1", "string", "string", "active"),
            ("access-card-reader-02", "Card Reader L2", "string", "string", "active"),
            ("access-turnstile-01", "Turnstile Main", "string", "string", "open"),
            ("access-badge-printer", "Badge Printer", "string", "string", "ready"),
            ("power-access-01", "Access System Power", "W", "float32", 120.0),
            ("alarm-access-01", "Access Alarm", "string", "string", "normal"),
            # Fire Alarm (8 points)
            ("fire-smoke-zone1", "Smoke Detector Zone 1", "string", "string", "normal"),
            ("fire-smoke-zone2", "Smoke Detector Zone 2", "string", "string", "normal"),
            ("fire-heat-zone1", "Heat Detector Zone 1", "string", "string", "normal"),
            ("fire-panel-status", "Fire Panel Status", "string", "string", "normal"),
            ("fire-siren-01", "Fire Siren", "string", "string", "off"),
            ("fire-extinguish-01", "Gas Extinguish System", "string", "string", "standby"),
            ("fire-evac-mode", "Evacuation Mode", "string", "string", "off"),
            ("power-fire-01", "Fire System Power", "W", "float32", 200.0),
            # Elevator (9 points)
            ("elev-status-1", "Elevator 1 Status", "string", "string", "running"),
            ("elev-floor-1", "Elevator 1 Current Floor", "int16", "int16", 3),
            ("elev-status-2", "Elevator 2 Status", "string", "string", "running"),
            ("elev-floor-2", "Elevator 2 Current Floor", "int16", "int16", 7),
            ("elev-door-1", "Elevator 1 Door", "string", "string", "closed"),
            ("elev-power-01", "Elevator System Power", "kW", "float32", 8.5),
            ("elev-alarm-1", "Elevator Alarm", "string", "string", "normal"),
            ("elev-maintenance-01", "Elevator Maintenance Due", "string", "string", "no"),
            ("elev-emergency-call", "Elevator Emergency Call", "string", "string", "none"),
            # Additional points to reach 50+
            ("power-hvac-total", "HVAC Total Power", "kW", "float32", 45.0),
            ("power-light-total", "Lighting Total Power", "kW", "float32", 8.5),
            ("power-elev-total", "Elevator Total Power", "kW", "float32", 12.0),
            ("energy-kwh-01", "Energy Meter kWh", "kWh", "float32", 1250.0),
            ("pf-01", "Power Factor", "ratio", "float32", 0.92),
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
            objects.append({
                "object_id": obj_id,
                "name": data["name"],
                "data_type": data["data_type"],
                "unit": data["unit"],
                "value": data["value"],
                "address": f"bacnet:ai:{hash(obj_id) % 1000}:presentValue",
            })
        return objects

    def read_point(self, object_id: str) -> Optional[dict[str, Any]]:
        """Simulate reading a point value."""
        point = self._points.get(object_id)
        if point:
            # Simulate slight value variation
            if isinstance(point["value"], (int, float)):
                point["value"] = round(point["value"] + random.uniform(-0.5, 0.5), 2)
            point["timestamp"] = datetime.now(timezone.utc).isoformat()
        return point

    def write_point(self, object_id: str, value: Any) -> bool:
        """Simulate writing a point value."""
        if object_id in self._points:
            self._points[object_id]["value"] = value
            return True
        return False

    def get_point_count(self) -> int:
        return len(self._points)

    def register_with_service(self, service: ExternalObjectService) -> None:
        """Register discovered objects with the ExternalObjectService."""
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
        """Infer external object type from point ID prefix."""
        if any(k in point_id for k in ["temp", "hum", "co2", "press", "flow"]):
            return "Sensor"
        if any(k in point_id for k in ["power", "energy"]):
            return "Meter"
        if "light" in point_id:
            return "Lighting"
        if "door" in point_id or "access" in point_id or "turnstile" in point_id:
            return "AccessControl"
        if "fire" in point_id or "smoke" in point_id or "heat" in point_id:
            return "FireAlarm"
        if "elev" in point_id:
            return "Elevator"
        return "Unknown"

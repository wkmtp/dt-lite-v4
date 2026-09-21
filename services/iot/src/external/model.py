"""External Object Model — 6 objects independent from Universal Ontology."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

EXTERNAL_SYSTEM_CATEGORIES = {
    "BMS", "SCADA", "PLC", "MES", "ERP", "IoT Gateway",
    "BuildingAutomation", "EnergyManagement", "SecuritySystem",
    "FireAlarm", "ElevatorControl", "AccessControl", "ParkingSystem",
    "WasteManagement", "WaterTreatment",
}

VALID_SEVERITIES = {"info", "warning", "critical", "emergency"}
VALID_RELATIONSHIP_TYPES = {"controls", "monitors", "feeds", "supplies", "depends_on"}


@dataclass
class ExternalSystem:
    """External system registry — separate from Universal Asset."""
    id: str
    code: str
    name: str
    category: str  # BMS, SCADA, PLC, MES, etc.
    protocol: str  # bacnet, modbus, opcua, mqtt, rest
    connection_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalObject:
    """External object — reference to a physical/logical entity in external system."""
    id: str
    system_id: str
    object_id: str  # external system's own ID
    name: str
    type: str  # "AHU", "Chiller", "Sensor", "Actuator", etc.
    properties: dict[str, Any] = field(default_factory=dict)
    asset_id: Optional[str] = None  # nullable — linked to Universal Asset


@dataclass
class ExternalPoint:
    """External point — data point from external system."""
    id: str
    object_id: str  # FK to ExternalObject.id
    name: str
    data_type: str  # "float32", "int16", "boolean", "string"
    unit: str  # UCUM
    address: str  # protocol-specific address
    point_id: Optional[str] = None  # nullable — FK to Universal Point.id
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExternalEvent:
    """External event — alarm/event from external system."""
    id: str
    system_id: str
    object_id: str
    event_type: str
    timestamp: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    severity: str = "info"

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity}")


@dataclass
class ExternalCommand:
    """External command — write command to external system."""
    id: str
    system_id: str
    object_id: str
    command_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""


@dataclass
class ExternalRelationship:
    """External relationship — link between two external objects."""
    id: str
    source_system_id: str
    source_object_id: str
    target_system_id: str
    target_object_id: str
    type: str  # controls, monitors, feeds, supplies, depends_on

    def __post_init__(self) -> None:
        if self.type not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(f"Invalid relationship type: {self.type}")


class ExternalObjectService:
    """
    External Object Service: CRUD for 6 External Objects.
    SL-11: NOT part of Universal Ontology.
    """

    def __init__(self) -> None:
        self._systems: dict[str, ExternalSystem] = {}
        self._objects: dict[str, ExternalObject] = {}
        self._points: dict[str, ExternalPoint] = {}
        self._events: list[ExternalEvent] = []
        self._commands: dict[str, ExternalCommand] = {}
        self._relationships: dict[str, ExternalRelationship] = {}

    # ---- ExternalSystem ----
    def create_system(self, data: dict[str, Any]) -> ExternalSystem:
        if data.get("category") not in EXTERNAL_SYSTEM_CATEGORIES:
            raise ValueError(f"Invalid category: {data.get('category')}")
        system = ExternalSystem(
            id=data["id"], code=data["code"], name=data["name"],
            category=data["category"], protocol=data["protocol"],
            connection_config=data.get("connection_config", {}),
            metadata=data.get("metadata", {}),
        )
        self._systems[system.id] = system
        logger.info("Registered external system: %s (%s)", system.id, system.category)
        return system

    def get_system(self, system_id: str) -> Optional[ExternalSystem]:
        return self._systems.get(system_id)

    def list_systems(self) -> list[ExternalSystem]:
        return list(self._systems.values())

    # ---- ExternalObject ----
    def create_object(self, data: dict[str, Any]) -> ExternalObject:
        obj = ExternalObject(
            id=data["id"], system_id=data["system_id"],
            object_id=data["object_id"], name=data["name"],
            type=data["type"], properties=data.get("properties", {}),
            asset_id=data.get("asset_id"),
        )
        self._objects[obj.id] = obj
        logger.info("Created external object: %s (system=%s, type=%s)", obj.id, obj.system_id, obj.type)
        return obj

    def get_object(self, obj_id: str) -> Optional[ExternalObject]:
        return self._objects.get(obj_id)

    def list_by_system(self, system_id: str) -> list[ExternalObject]:
        return [o for o in self._objects.values() if o.system_id == system_id]

    # ---- ExternalPoint ----
    def create_point(self, data: dict[str, Any]) -> ExternalPoint:
        point = ExternalPoint(
            id=data["id"], object_id=data["object_id"],
            point_id=data.get("point_id"), name=data["name"],
            data_type=data["data_type"], unit=data["unit"],
            address=data["address"], metadata=data.get("metadata", {}),
        )
        self._points[point.id] = point
        return point

    def get_point(self, point_id: str) -> Optional[ExternalPoint]:
        return self._points.get(point_id)

    def list_by_object(self, object_id: str) -> list[ExternalPoint]:
        return [p for p in self._points.values() if p.object_id == object_id]

    # ---- ExternalEvent ----
    def create_event(self, data: dict[str, Any]) -> ExternalEvent:
        event = ExternalEvent(
            id=data["id"], system_id=data["system_id"],
            object_id=data["object_id"], event_type=data["event_type"],
            timestamp=data.get("timestamp"), payload=data.get("payload", {}),
            severity=data.get("severity", "info"),
        )
        self._events.append(event)
        return event

    # ---- ExternalCommand ----
    def create_command(self, data: dict[str, Any]) -> ExternalCommand:
        cmd = ExternalCommand(
            id=data["id"], system_id=data["system_id"],
            object_id=data["object_id"], command_type=data["command_type"],
            parameters=data.get("parameters", {}),
            idempotency_key=data.get("idempotency_key", ""),
        )
        self._commands[cmd.id] = cmd
        return cmd

    # ---- ExternalRelationship ----
    def create_relationship(self, data: dict[str, Any]) -> ExternalRelationship:
        rel = ExternalRelationship(
            id=data["id"],
            source_system_id=data["source_system_id"],
            source_object_id=data["source_object_id"],
            target_system_id=data["target_system_id"],
            target_object_id=data["target_object_id"],
            type=data["type"],
        )
        self._relationships[rel.id] = rel
        return rel

    def list_by_object(self, object_id: str) -> list[ExternalRelationship]:
        return [r for r in self._relationships.values()
                if r.source_object_id == object_id or r.target_object_id == object_id]

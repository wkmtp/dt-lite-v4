"""MappingProfile Service — Protocol-specific address, transform, polling."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_PROTOCOLS = {"bacnet", "modbus", "opcua", "mqtt", "rest", "ocpp"}
VALID_TRANSFORMS = {"linear", "polynomial", "lookup_table", "script"}
VALID_POLLING_STRATEGIES = {"periodic", "report_on_change", "event_triggered"}


@dataclass
class MappingProfile:
    """MappingProfile — One Point ↔ Many Mappings (protocol-specific)."""
    id: str
    point_id: str
    protocol: str
    address: str
    register: Optional[int] = None
    function_code: Optional[int] = None
    scale: float = 1.0
    offset: float = 0.0
    polling_interval: Optional[str] = None
    timeout: Optional[int] = None
    retry_count: int = 3
    deadband: float = 0.0
    transform_expr: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def transform_value(self, raw_value: float) -> float:
        """Apply transform to raw value."""
        if self.transform_expr == "linear" or self.transform_expr is None:
            return raw_value * self.scale + self.offset
        # polynomial, lookup_table, script handled by separate transform engine
        return raw_value


class MappingProfileService:
    """
    MappingProfile Service: one Point ↔ many protocol mappings.
    NO semantic fields — those belong to Point.
    """

    def __init__(self) -> None:
        self._mappings: dict[str, MappingProfile] = {}

    def create(self, data: dict[str, Any]) -> MappingProfile:
        """Create a mapping profile."""
        for key in ["id", "point_id", "protocol", "address"]:
            if key not in data:
                raise ValueError(f"MappingProfile missing required field: {key}")

        if data["protocol"] not in VALID_PROTOCOLS:
            raise ValueError(f"Invalid protocol: {data['protocol']}")

        mapping = MappingProfile(
            id=data["id"],
            point_id=data["point_id"],
            protocol=data["protocol"],
            address=data["address"],
            register=data.get("register"),
            function_code=data.get("function_code"),
            scale=data.get("scale", 1.0),
            offset=data.get("offset", 0.0),
            polling_interval=data.get("polling_interval"),
            timeout=data.get("timeout"),
            retry_count=data.get("retry_count", 3),
            deadband=data.get("deadband", 0.0),
            transform_expr=data.get("transform_expr"),
            metadata=data.get("metadata", {}),
        )
        self._mappings[mapping.id] = mapping
        logger.info("Created mapping: %s (point=%s, protocol=%s)", mapping.id, mapping.point_id, mapping.protocol)
        return mapping

    def get(self, mapping_id: str) -> Optional[MappingProfile]:
        """Get mapping by ID."""
        return self._mappings.get(mapping_id)

    def list_by_point(self, point_id: str) -> list[MappingProfile]:
        """List all mappings for a point (multi-protocol)."""
        return [m for m in self._mappings.values() if m.point_id == point_id]

    def list_by_protocol(self, protocol: str) -> list[MappingProfile]:
        """List all mappings of a protocol."""
        return [m for m in self._mappings.values() if m.protocol == protocol]

    def delete(self, mapping_id: str) -> bool:
        """Remove mapping."""
        if mapping_id not in self._mappings:
            return False
        del self._mappings[mapping_id]
        return True

"""AI Tool Registry — Tool definition, I/O schema, capability binding, mutating flag."""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

TOOL_CODE_PATTERN = re.compile(r"^tool\.(park|factory)\.[a-z_][a-z0-9_]*$")
VALID_SAFETY_LEVELS = {"C0", "C1", "C2", "C3", "C4"}
SAFETY_LEVEL_ORDER = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4}


@dataclass
class Tool:
    """AI Tool definition bound to a CapabilityContract."""
    id: str
    code: str
    name: str
    capability_code: str  # binds to CapabilityContract
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    mutating: bool = False  # critical: true = state-changing
    permission_required: str = "viewer"
    safety_level: str = "C0"
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_safety(self) -> bool:
        return SAFETY_LEVEL_ORDER.get(self.safety_level, 0) >= 2

    @property
    def is_mutating_high_safety(self) -> bool:
        return self.mutating and SAFETY_LEVEL_ORDER.get(self.safety_level, 0) >= 2


class ToolRegistry:
    """Tool registry: CRUD, capability binding, safety validation.

    Key invariant: Tool MUST have capability_code; Agent MUST NOT have capability_code.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, data: dict[str, Any]) -> Tool:
        """Register a tool with validation."""
        for key in ["id", "code", "name", "capability_code"]:
            if key not in data:
                raise ValueError(f"Tool missing required field: {key}")

        if not TOOL_CODE_PATTERN.match(data["code"]):
            raise ValueError(
                f"Tool code '{data['code']}' does not match convention: "
                f"tool.<domain>.<type>"
            )

        if data.get("safety_level", "C0") not in VALID_SAFETY_LEVELS:
            raise ValueError(
                f"Invalid safety_level '{data.get('safety_level')}'. "
                f"Must be one of: {sorted(VALID_SAFETY_LEVELS)}"
            )

        # Mutating tools with C0 safety is a contradiction — enforce
        if data.get("mutating", False) and data.get("safety_level") == "C0":
            raise ValueError(
                "Mutating tools must have safety_level >= C1"
            )

        tool = Tool(
            id=data["id"],
            code=data["code"],
            name=data["name"],
            capability_code=data["capability_code"],
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            mutating=data.get("mutating", False),
            permission_required=data.get("permission_required", "viewer"),
            safety_level=data.get("safety_level", "C0"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )
        self._tools[tool.id] = tool
        logger.info("Registered tool: %s (%s) capability=%s mutating=%s safety=%s",
                     tool.id, tool.code, tool.capability_code, tool.mutating, tool.safety_level)
        return tool

    def get(self, tool_id: str) -> Optional[Tool]:
        return self._tools.get(tool_id)

    def get_by_code(self, tool_code: str) -> Optional[Tool]:
        return next((t for t in self._tools.values() if t.code == tool_code), None)

    def list_by_capability(self, capability_code: str) -> list[Tool]:
        return [t for t in self._tools.values() if t.capability_code == capability_code]

    def list_mutating(self) -> list[Tool]:
        return [t for t in self._tools.values() if t.mutating]

    def list_by_safety_level(self, level: str) -> list[Tool]:
        return [t for t in self._tools.values() if t.safety_level == level]

    def delete(self, tool_id: str) -> bool:
        if tool_id in self._tools:
            del self._tools[tool_id]
            return True
        return False

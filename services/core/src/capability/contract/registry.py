"""CapabilityContract Registry — I/O schema, safety level, pre/post conditions."""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_SAFETY_LEVELS = {"C0", "C1", "C2", "C3", "C4"}
SAFETY_DESCRIPTIONS = {
    "C0": "observe — auto-approve, log only",
    "C1": "adjust — single approver (role-based), 5min timeout",
    "C2": "command — dual approver (role-separated), 15min timeout",
    "C3": "override — emergency role + audit trail, 1hr retention",
    "C4": "interlock — hardware confirmation, permanent retention",
}


@dataclass
class CapabilityContract:
    """CapabilityContract — WHAT the capability does, NOT how."""
    id: str
    code: str
    category: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    safety_level: str
    preconditions: list[dict[str, Any]] = field(default_factory=list)
    postconditions: list[dict[str, Any]] = field(default_factory=list)
    idempotency_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_idempotency_key(self, input_params: dict[str, Any], window_seconds: int = 300) -> str:
        """Compute idempotency key: SHA256(capability_code + input_params + timestamp_window)."""
        import json
        windowed_params = {
            "code": self.code,
            "params": input_params,
            "window": int(datetime.now(timezone.utc).timestamp()) // window_seconds,
        }
        raw = json.dumps(windowed_params, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()


class CapabilityContractRegistry:
    """
    CapabilityContract Registry: I/O schema, safety level, pre/post conditions.
    NO algorithm/logic — that belongs in CapabilityPlugin.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, CapabilityContract] = {}

    def register(self, contract: CapabilityContract) -> None:
        """Register a capability contract."""
        if contract.safety_level not in VALID_SAFETY_LEVELS:
            raise ValueError(f"Invalid safety level: {contract.safety_level}")
        self._contracts[contract.code] = contract
        logger.info("Registered capability: %s (safety=%s)", contract.code, contract.safety_level)

    def get(self, code: str) -> Optional[CapabilityContract]:
        """Get capability contract by code."""
        return self._contracts.get(code)

    def list_by_safety_level(self, safety_level: str) -> list[CapabilityContract]:
        """List all capabilities with a given safety level."""
        return [c for c in self._contracts.values() if c.safety_level == safety_level]

    def validate_preconditions(self, contract: CapabilityContract, context: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate preconditions against current context."""
        errors = []
        for precondition in contract.preconditions:
            # Simple evaluation: check if required keys exist in context
            for key in precondition.get("required_keys", []):
                if key not in context:
                    errors.append(f"Precondition failed: missing key '{key}'")
        return len(errors) == 0, errors

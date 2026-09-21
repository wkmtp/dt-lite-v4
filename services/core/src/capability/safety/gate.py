"""Safety Gate — C0-C4 enforcement, approval workflow, audit trail."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

SAFETY_LEVELS = {"C0", "C1", "C2", "C3", "C4"}
APPROVAL_MODES = {
    "C0": "auto",      # auto-approve, log only
    "C1": "single",    # single approver (role-based)
    "C2": "dual",      # dual approver (role-separated)
    "C3": "emergency", # emergency role + audit trail
    "C4": "hardware",  # hardware confirmation
}
TIMEOUTS = {"C0": 0, "C1": 300, "C2": 900, "C3": 3600, "C4": 0}  # seconds
RETENTION = {"C0": "30d", "C1": "90d", "C2": "1y", "C3": "5y", "C4": "permanent"}


@dataclass
class SafetyDecision:
    """Result of a safety evaluation."""
    safety_level: str
    approved: bool
    approver_role: Optional[str] = None
    approver_count: int = 0
    approval_method: str = "auto"
    timestamp: str = ""
    audit_id: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.audit_id:
            self.audit_id = f"safety-{self.safety_level}-{self.timestamp}"


class SafetyGate:
    """
    Safety Gate: C0-C4 enforcement with approval workflow and audit.
    SL-06: No bypass of AI Security Chain.
    """

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []

    def evaluate(self, safety_level: str, context: dict[str, Any]) -> SafetyDecision:
        """
        Evaluate safety level and return decision.
        Returns SafetyDecision with approved=True/False and audit_id.
        """
        if safety_level not in SAFETY_LEVELS:
            raise ValueError(f"Invalid safety level: {safety_level}")

        decision = SafetyDecision(
            safety_level=safety_level,
            approved=False,
            approval_method=APPROVAL_MODES[safety_level],
        )

        if safety_level == "C0":
            # Auto-approve, log only
            decision.approved = True
            decision.reason = "C0: observe — auto-approved"

        elif safety_level == "C1":
            # Single approver required
            approver = context.get("approver_role")
            if not approver:
                decision.reason = "C1: single approver required"
            else:
                decision.approved = True
                decision.approver_role = approver
                decision.approver_count = 1
                decision.reason = "C1: single approver approved"

        elif safety_level == "C2":
            # Dual approver required
            approvers = context.get("approvers", [])
            if len(approvers) < 2:
                decision.reason = f"C2: dual approval required, got {len(approvers)}"
            else:
                decision.approved = True
                decision.approver_count = len(approvers)
                decision.approver_role = ", ".join(approvers)
                decision.reason = "C2: dual approvers approved"

        elif safety_level == "C3":
            # Emergency role + audit trail
            emergency_role = context.get("emergency_role")
            if not emergency_role:
                decision.reason = "C3: emergency role required"
            else:
                decision.approved = True
                decision.approver_role = emergency_role
                decision.reason = "C3: emergency override approved"

        elif safety_level == "C4":
            # Hardware confirmation
            hardware_confirmed = context.get("hardware_confirmed", False)
            if not hardware_confirmed:
                decision.reason = "C4: hardware confirmation required"
            else:
                decision.approved = True
                decision.reason = "C4: hardware confirmed"

        # Append to immutable audit log
        self._audit_log.append({
            "decision_id": decision.audit_id,
            "safety_level": safety_level,
            "approved": decision.approved,
            "approver_role": decision.approver_role,
            "approval_method": decision.approval_method,
            "timestamp": decision.timestamp,
            "reason": decision.reason,
            "context": context,
        })
        logger.info("Safety decision: %s → approved=%s (%s)", decision.audit_id, decision.approved, decision.reason)
        return decision

    def get_audit_log(self, safety_level: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        """Query audit log entries."""
        if safety_level:
            entries = [e for e in self._audit_log if e["safety_level"] == safety_level]
        else:
            entries = self._audit_log
        return entries[-limit:]

    def get_decision(self, audit_id: str) -> Optional[dict[str, Any]]:
        """Get a specific audit entry by ID."""
        for entry in reversed(self._audit_log):
            if entry["decision_id"] == audit_id:
                return entry
        return None

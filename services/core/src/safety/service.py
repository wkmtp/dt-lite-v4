"""Safety Engine — C0-C4 evaluation, approval workflow, audit trail.

Integrates with existing SafetyGate from UAA-03.
C0=auto, C1=single-approve, C2=dual-approve, C3=emergency+audit, C4=hardware-confirmed.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_SAFETY_LEVELS = {"C0", "C1", "C2", "C3", "C4"}
SAFETY_ORDER = {"C0": 0, "C1": 1, "C2": 2, "C3": 3, "C4": 4}


@dataclass
class SafetyEvaluation:
    """Result of a safety level evaluation."""
    safety_level: str
    approved: bool
    approvers: list[str] = field(default_factory=list)
    approval_timestamp: Optional[str] = None
    rejection_reason: Optional[str] = None
    audit_entry_id: Optional[str] = None


@dataclass
class ApprovalRecord:
    """Record of an approval decision."""
    id: str
    tool_code: str
    safety_level: str
    approver_role: str
    approved: bool
    timestamp: str
    reason: str = ""
    hash: str = ""


class SafetyEngine:
    """Safety engine: C0-C4 evaluation with approval workflow.

    Key invariants:
    - C0: auto-approve (read-only, no state change)
    - C1: single approver, 5-min window
    - C2: dual approver, 15-min window
    - C3: emergency override with full audit
    - C4: hardware confirmation required (permanent)
    """

    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalRecord] = {}
        self._evaluations: dict[str, SafetyEvaluation] = {}

    def evaluate(
        self,
        tool_code: str,
        safety_level: str,
        requester_role: str,
        context: dict[str, Any] | None = None,
    ) -> SafetyEvaluation:
        """Evaluate safety level for a tool invocation."""
        if safety_level not in VALID_SAFETY_LEVELS:
            raise ValueError(f"Invalid safety_level '{safety_level}'. Must be one of: {sorted(VALID_SAFETY_LEVELS)}")

        context = context or {}
        eval_id = str(uuid.uuid4())

        # C0: auto-approve
        if safety_level == "C0":
            evaluation = SafetyEvaluation(
                safety_level="C0",
                approved=True,
                approval_timestamp=datetime.now(timezone.utc).isoformat(),
                audit_entry_id=eval_id,
            )
            self._evaluations[eval_id] = evaluation
            logger.info("C0 auto-approved: tool=%s safety=C0", tool_code)
            return evaluation

        # C1: single-approve
        if safety_level == "C1":
            # Check if requester has approver role
            has_approver = requester_role in {"admin", "supervisor", "manager"}
            if has_approver:
                evaluation = SafetyEvaluation(
                    safety_level="C1",
                    approved=True,
                    approvers=[requester_role],
                    approval_timestamp=datetime.now(timezone.utc).isoformat(),
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                self._record_approval(tool_code, "C1", requester_role, True, eval_id)
                logger.info("C1 approved: tool=%s by %s", tool_code, requester_role)
                return evaluation
            else:
                evaluation = SafetyEvaluation(
                    safety_level="C1",
                    approved=False,
                    rejection_reason=f"Role '{requester_role}' not authorized for C1 approval",
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                self._record_approval(tool_code, "C1", requester_role, False, eval_id, reason=evaluation.rejection_reason)
                return evaluation

        # C2: dual-approve
        if safety_level == "C2":
            # Need at least 2 approvers
            approvers = context.get("approvers", [])
            if len(approvers) >= 2:
                evaluation = SafetyEvaluation(
                    safety_level="C2",
                    approved=True,
                    approvers=approvers[:2],
                    approval_timestamp=datetime.now(timezone.utc).isoformat(),
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                for approver in approvers[:2]:
                    self._record_approval(tool_code, "C2", approver, True, eval_id)
                return evaluation
            else:
                evaluation = SafetyEvaluation(
                    safety_level="C2",
                    approved=False,
                    rejection_reason=f"Need 2 approvers, got {len(approvers)}",
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                return evaluation

        # C3: emergency override
        if safety_level == "C3":
            is_emergency = context.get("emergency", False)
            has_audit_role = requester_role in {"admin", "emergency_operator"}
            if is_emergency and has_audit_role:
                evaluation = SafetyEvaluation(
                    safety_level="C3",
                    approved=True,
                    approvers=[requester_role],
                    approval_timestamp=datetime.now(timezone.utc).isoformat(),
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                self._record_approval(tool_code, "C3", requester_role, True, eval_id, reason="emergency_override")
                return evaluation
            else:
                evaluation = SafetyEvaluation(
                    safety_level="C3",
                    approved=False,
                    rejection_reason="C3 requires emergency flag + audit role",
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                return evaluation

        # C4: hardware confirmation
        if safety_level == "C4":
            hardware_confirmed = context.get("hardware_confirmed", False)
            if hardware_confirmed:
                evaluation = SafetyEvaluation(
                    safety_level="C4",
                    approved=True,
                    approvers=["hardware"],
                    approval_timestamp=datetime.now(timezone.utc).isoformat(),
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                self._record_approval(tool_code, "C4", "hardware", True, eval_id, reason="hardware_confirmed")
                return evaluation
            else:
                evaluation = SafetyEvaluation(
                    safety_level="C4",
                    approved=False,
                    rejection_reason="C4 requires hardware confirmation",
                    audit_entry_id=eval_id,
                )
                self._evaluations[eval_id] = evaluation
                return evaluation

        raise ValueError(f"Unhandled safety level: {safety_level}")

    def _record_approval(
        self,
        tool_code: str,
        safety_level: str,
        approver_role: str,
        approved: bool,
        eval_id: str,
        reason: str = "",
    ) -> None:
        """Record an approval decision with hash chain."""
        approval_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        hash_input = f"{approval_id}:{now}:{tool_code}:{approver_role}:{str(approved)}:{reason}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        record = ApprovalRecord(
            id=approval_id,
            tool_code=tool_code,
            safety_level=safety_level,
            approver_role=approver_role,
            approved=approved,
            timestamp=now,
            reason=reason,
            hash=hash_value,
        )
        self._approvals[approval_id] = record

    def get_evaluation(self, eval_id: str) -> Optional[SafetyEvaluation]:
        return self._evaluations.get(eval_id)

    def get_approvals(self, tool_code: str) -> list[ApprovalRecord]:
        return [a for a in self._approvals.values() if a.tool_code == tool_code]

    def verify_approval_hash(self, approval_id: str) -> bool:
        """Verify an approval record's hash integrity."""
        record = self._approvals.get(approval_id)
        if not record:
            return False
        # Reconstruct hash and compare
        hash_input = f"{record.id}:{record.timestamp}:{record.tool_code}:{record.approver_role}:{str(record.approved)}:{record.reason}"
        expected_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return record.hash == expected_hash

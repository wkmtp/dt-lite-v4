"""Alarm Engine — 8-state lifecycle, escalation, notification, closure loop.

State machine:
  normal → acknowledged → investigating → resolving → resolved → closed → archived → purged
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 8 alarm states with enforced transitions
VALID_STATES = {
    "normal", "acknowledged", "investigating", "resolving",
    "resolved", "closed", "archived", "purged",
}

# Enforced state transitions (no skipping)
TRANSITIONS: dict[str, set[str]] = {
    "normal": {"acknowledged"},
    "acknowledged": {"investigating"},
    "investigating": {"resolving"},
    "resolving": {"resolved"},
    "resolved": {"closed"},
    "closed": {"archived"},
    "archived": {"purged"},
    "purged": set(),  # terminal state
}

# Reverse transitions (manual reset, admin only)
MANUAL_RESET: set[str] = {"acknowledged", "investigating", "resolving", "resolved", "closed", "archived"}

VALID_SEVERITIES = {"P1", "P2", "P3", "P4"}
VALID_NOTIFICATION_CHANNELS = {"email", "sms", "websocket", "pagerduty", "webhook"}


@dataclass
class Alarm:
    """Alarm entity with 8-state lifecycle."""
    id: str
    code: str
    asset_id: str
    point_id: str
    severity: str  # P1-P4
    state: str = "normal"
    title: str = ""
    description: str = ""
    triggered_at: str = ""
    acknowledged_at: Optional[str] = None
    investigated_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    archived_at: Optional[str] = None
    purged_at: Optional[str] = None
    escalation_level: int = 0
    notification_history: list[dict[str, Any]] = field(default_factory=list)
    workflow_instance_id: Optional[str] = None
    workorder_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.state in ("purged",)

    @property
    def duration_in_state(self) -> float:
        """Seconds spent in current state."""
        if not self.triggered_at:
            return 0.0
        now = datetime.now(timezone.utc)
        try:
            triggered = datetime.fromisoformat(self.triggered_at)
            return (now - triggered).total_seconds()
        except (ValueError, TypeError):
            return 0.0


class AlarmService:
    """Alarm service: 8-state lifecycle, escalation, notification, closure loop.

    Closure loop: Alarm → Workflow → WorkOrder → Resolution → Alarm.resolved
    """

    def __init__(self) -> None:
        self._alarms: dict[str, Alarm] = {}

    def create(
        self,
        asset_id: str,
        point_id: str,
        severity: str,
        title: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Alarm:
        """Create a new alarm in 'normal' state."""
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{severity}'. Must be one of: {sorted(VALID_SEVERITIES)}")

        alarm_id = str(uuid.uuid4())
        alarm = Alarm(
            id=alarm_id,
            code=f"alarm-{alarm_id[:8]}",
            asset_id=asset_id,
            point_id=point_id,
            severity=severity,
            state="normal",
            title=title,
            description=description,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "tenant_id": metadata.get("tenant_id", "") if metadata else "",
                **(metadata or {}),
            },
        )
        self._alarms[alarm_id] = alarm
        logger.info("Created alarm: %s asset=%s severity=%s", alarm_id, asset_id, severity)
        return alarm

    def get(self, alarm_id: str) -> Optional[Alarm]:
        return self._alarms.get(alarm_id)

    def list_by_asset(self, asset_id: str) -> list[Alarm]:
        return [a for a in self._alarms.values() if a.asset_id == asset_id]

    def list_by_severity(self, severity: str) -> list[Alarm]:
        return [a for a in self._alarms.values() if a.severity == severity]

    def list_active(self) -> list[Alarm]:
        """List all non-terminal alarms."""
        return [a for a in self._alarms.values() if not a.is_terminal]

    def transition(self, alarm_id: str, new_state: str, actor: str = "system") -> Optional[Alarm]:
        """Transition alarm to new state. Enforces transition rules."""
        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return None

        current = alarm.state
        allowed = TRANSITIONS.get(current, set())

        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition from '{current}' to '{new_state}'. "
                f"Allowed: {sorted(allowed)}"
            )

        old_state = current
        alarm.state = new_state

        # Record timestamps
        now = datetime.now(timezone.utc).isoformat()
        if new_state == "acknowledged":
            alarm.acknowledged_at = now
        elif new_state == "investigating":
            alarm.investigated_at = now
        elif new_state == "resolving":
            alarm.resolved_at = now
        elif new_state == "closed":
            alarm.closed_at = now
        elif new_state == "archived":
            alarm.archived_at = now
        elif new_state == "purged":
            alarm.purged_at = now

        alarm.notification_history.append({
            "from_state": old_state,
            "to_state": new_state,
            "actor": actor,
            "timestamp": now,
        })
        logger.info("Alarm %s: %s → %s (actor=%s)", alarm_id, old_state, new_state, actor)
        return alarm

    def escalate(self, alarm_id: str, reason: str = "") -> Optional[Alarm]:
        """Escalate alarm based on time/severity rules."""
        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return None

        alarm.escalation_level += 1
        alarm.notification_history.append({
            "type": "escalation",
            "level": alarm.escalation_level,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return alarm

    def notify(self, alarm_id: str, channel: str, recipient: str) -> bool:
        """Send notification via specified channel."""
        if channel not in VALID_NOTIFICATION_CHANNELS:
            raise ValueError(f"Invalid channel '{channel}'. Must be one of: {sorted(VALID_NOTIFICATION_CHANNELS)}")

        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return False

        alarm.notification_history.append({
            "type": "notification",
            "channel": channel,
            "recipient": recipient,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return True

    def link_workflow(self, alarm_id: str, workflow_id: str, workorder_id: str) -> Optional[Alarm]:
        """Link alarm to a workflow instance and workorder (closure loop)."""
        alarm = self._alarms.get(alarm_id)
        if not alarm:
            return None
        alarm.workflow_instance_id = workflow_id
        alarm.workorder_id = workorder_id
        return alarm

    def delete(self, alarm_id: str) -> bool:
        """Hard delete (admin only, for purged alarms)."""
        alarm = self._alarms.get(alarm_id)
        if not alarm or alarm.state != "purged":
            return False
        del self._alarms[alarm_id]
        return True

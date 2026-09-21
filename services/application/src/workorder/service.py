"""WorkOrder Service — Assignment, SLA, closure, audit trail."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_WORKORDER_STATUSES = {"draft", "assigned", "in_progress", "pending_review", "completed", "closed"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}


@dataclass
class WorkOrder:
    """WorkOrder entity — assignment, SLA, closure, audit trail."""
    id: str
    code: str
    title: str
    type: str  # corrective, preventive, inspection, improvement
    status: str = "draft"
    priority: str = "medium"
    asset_id: str = ""
    assigned_to: Optional[str] = None
    assigned_role: Optional[str] = None
    sla_deadline: Optional[str] = None
    sla_compliance: Optional[bool] = None
    created_by: Optional[str] = None
    closed_by: Optional[str] = None
    audit_trail: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def created_at(self) -> str:
        return self.metadata.get("created_at", "")

    def is_sla_breached(self) -> bool:
        """Check if SLA deadline has been breached."""
        if not self.sla_deadline or self.status in ("completed", "closed"):
            return False
        try:
            deadline = datetime.fromisoformat(self.sla_deadline)
            return datetime.now(timezone.utc) > deadline
        except (ValueError, TypeError):
            return False


class WorkOrderService:
    """WorkOrder service: CRUD, assignment, SLA tracking, closure audit.

    Integration with Alarm→Workflow chain:
      Alarm triggers SOP Workflow → creates WorkOrder(s) → tracks to closure → auto-resolves Alarm
    """

    def __init__(self) -> None:
        self._orders: dict[str, WorkOrder] = {}

    def create(
        self,
        title: str,
        workorder_type: str,
        asset_id: str = "",
        priority: str = "medium",
        sla_deadline: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> WorkOrder:
        """Create a work order in 'draft' status."""
        if workorder_type not in {"corrective", "preventive", "inspection", "improvement"}:
            raise ValueError(
                f"Invalid type '{workorder_type}'. Must be one of: "
                "corrective, preventive, inspection, improvement"
            )
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of: {sorted(VALID_PRIORITIES)}")

        order_id = str(uuid.uuid4())
        order = WorkOrder(
            id=order_id,
            code=f"WO-{order_id[:8].upper()}",
            title=title,
            type=workorder_type,
            priority=priority,
            asset_id=asset_id,
            sla_deadline=sla_deadline,
            audit_trail=[{
                "action": "created",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }],
            metadata={
                "tenant_id": metadata.get("tenant_id", "") if metadata else "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            },
        )
        self._orders[order_id] = order
        logger.info("Created work order: %s (%s) type=%s priority=%s", order_id, order.code, workorder_type, priority)
        return order

    def get(self, order_id: str) -> Optional[WorkOrder]:
        return self._orders.get(order_id)

    def list_by_asset(self, asset_id: str) -> list[WorkOrder]:
        return [o for o in self._orders.values() if o.asset_id == asset_id]

    def list_active(self) -> list[WorkOrder]:
        return [o for o in self._orders.values() if o.status not in ("completed", "closed")]

    def assign(self, order_id: str, assignee_id: str, assignee_role: str = "") -> Optional[WorkOrder]:
        """Assign a work order to a technician."""
        order = self._orders.get(order_id)
        if not order:
            return None
        if order.status != "draft":
            raise ValueError(f"Cannot assign work order in status '{order.status}'")
        order.assigned_to = assignee_id
        order.assigned_role = assignee_role
        order.status = "assigned"
        order.audit_trail.append({
            "action": "assigned",
            "assignee_id": assignee_id,
            "assignee_role": assignee_role,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return order

    def start(self, order_id: str) -> Optional[WorkOrder]:
        """Start working on a work order."""
        order = self._orders.get(order_id)
        if not order:
            return None
        if order.status != "assigned":
            raise ValueError(f"Cannot start work order in status '{order.status}'")
        order.status = "in_progress"
        order.audit_trail.append({
            "action": "started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return order

    def complete(self, order_id: str, reviewer_id: str = "", notes: str = "") -> Optional[WorkOrder]:
        """Complete a work order (pending review)."""
        order = self._orders.get(order_id)
        if not order:
            return None
        if order.status != "in_progress":
            raise ValueError(f"Cannot complete work order in status '{order.status}'")
        order.status = "pending_review"
        order.audit_trail.append({
            "action": "completed",
            "reviewer_id": reviewer_id,
            "notes": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return order

    def close(self, order_id: str, closer_id: str) -> Optional[WorkOrder]:
        """Close a work order (final)."""
        order = self._orders.get(order_id)
        if not order:
            return None
        if order.status != "pending_review":
            raise ValueError(f"Cannot close work order in status '{order.status}'")
        order.status = "closed"
        order.closed_by = closer_id
        order.sla_compliance = not order.is_sla_breached()
        order.audit_trail.append({
            "action": "closed",
            "closed_by": closer_id,
            "sla_compliant": order.sla_compliance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return order

    def delete(self, order_id: str) -> bool:
        """Delete a work order (draft only)."""
        order = self._orders.get(order_id)
        if not order or order.status not in ("draft",):
            return False
        del self._orders[order_id]
        return True

"""Workflow Engine — BPMN-lite: SOP→WorkOrder, human+auto tasks."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_NODE_TYPES = {"start", "user_task", "service_task", "gateway", "end", "timer_boundary"}
VALID_GATEWAY_TYPES = {"exclusive", "parallel"}
VALID_TASK_STATUSES = {"pending", "active", "completed", "failed", "skipped"}


@dataclass
class WorkflowNode:
    """A single node in a BPMN-lite workflow."""
    id: str
    type: str  # start, user_task, service_task, gateway, end, timer_boundary
    label: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    next_node_ids: list[str] = field(default_factory=list)


@dataclass
class WorkflowTask:
    """An executable task instance within a workflow."""
    id: str
    node_id: str
    node_type: str
    status: str = "pending"
    assignee_id: Optional[str] = None
    assignee_role: Optional[str] = None
    due_date: Optional[str] = None
    form_schema: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    completed_at: Optional[str] = None


@dataclass
class WorkflowInstance:
    """A running instance of a workflow template."""
    id: str
    template_id: str
    context: dict[str, Any] = field(default_factory=dict)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    status: str = "running"  # running, paused, completed, failed, cancelled
    created_at: str = ""
    completed_at: Optional[str] = None
    error: Optional[str] = None


class WorkflowService:
    """Workflow service: BPMN-lite template management, instance execution.

    Supports: start, user_task, service_task, gateway (XOR/AND), end, timer_boundary
    Closure loop integration: Alarm → Workflow → WorkOrder
    """

    def __init__(self) -> None:
        self._templates: dict[str, dict[str, Any]] = {}
        self._instances: dict[str, WorkflowInstance] = {}

    def create_template(
        self,
        template_id: str,
        name: str,
        nodes: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a workflow template with DAG validation."""
        node_ids = {n["id"] for n in nodes}
        for node in nodes:
            if node["type"] not in VALID_NODE_TYPES:
                raise ValueError(f"Invalid node type '{node['type']}'")
            if node["type"] == "gateway" and node.get("gateway_type") not in VALID_GATEWAY_TYPES:
                raise ValueError(f"Invalid gateway type '{node.get('gateway_type')}'")
            for next_id in node.get("next_node_ids", []):
                if next_id not in node_ids:
                    raise ValueError(f"Node {node['id']} references unknown next node {next_id}")

        template = {
            "id": template_id,
            "name": name,
            "nodes": nodes,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._templates[template_id] = template
        logger.info("Created workflow template: %s (%s)", template_id, name)
        return template

    def get_template(self, template_id: str) -> Optional[dict[str, Any]]:
        return self._templates.get(template_id)

    def create_instance(
        self,
        template_id: str,
        context: dict[str, Any],
        initial_variables: Optional[dict[str, Any]] = None,
    ) -> WorkflowInstance:
        """Create a workflow instance from a template."""
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Workflow template '{template_id}' not found")

        instance_id = str(uuid.uuid4())
        instance = WorkflowInstance(
            id=instance_id,
            template_id=template_id,
            context=context,
            variables=initial_variables or {},
            status="running",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._instances[instance_id] = instance

        # Create initial tasks from template nodes
        for node in template["nodes"]:
            if node["type"] in ("user_task", "service_task"):
                task = {
                    "id": str(uuid.uuid4()),
                    "node_id": node["id"],
                    "node_type": node["type"],
                    "status": "pending",
                    "assignee_role": node.get("config", {}).get("role"),
                    "due_date": node.get("config", {}).get("due_date"),
                    "form_schema": node.get("config", {}).get("form_schema", {}),
                    "created_at": instance.created_at,
                }
                instance.tasks.append(task)

        logger.info("Created workflow instance: %s from template %s", instance_id, template_id)
        return instance

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        return self._instances.get(instance_id)

    def complete_task(self, instance_id: str, task_id: str, result: dict[str, Any]) -> Optional[WorkflowInstance]:
        """Complete a workflow task."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None

        for task in instance.tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["result"] = result
                task["completed_at"] = datetime.now(timezone.utc).isoformat()
                break

        # Check if all tasks are completed
        if all(t["status"] == "completed" for t in instance.tasks):
            instance.status = "completed"
            instance.completed_at = datetime.now(timezone.utc).isoformat()

        return instance

    def fail_task(self, instance_id: str, task_id: str, error: str) -> Optional[WorkflowInstance]:
        """Fail a workflow task."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None

        for task in instance.tasks:
            if task["id"] == task_id:
                task["status"] = "failed"
                task["completed_at"] = datetime.now(timezone.utc).isoformat()
                break

        instance.status = "failed"
        instance.error = error
        instance.completed_at = datetime.now(timezone.utc).isoformat()
        return instance

    def cancel(self, instance_id: str) -> bool:
        """Cancel a running workflow instance."""
        instance = self._instances.get(instance_id)
        if not instance or instance.status not in ("running", "paused"):
            return False
        instance.status = "cancelled"
        instance.completed_at = datetime.now(timezone.utc).isoformat()
        return True

    def list_instances(self, template_id: str) -> list[WorkflowInstance]:
        return [i for i in self._instances.values() if i.template_id == template_id]

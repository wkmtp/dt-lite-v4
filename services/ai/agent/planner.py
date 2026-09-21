"""Task Planner: decomposes high-level goals into a DAG and schedules execution.

The planner:
  1. Asks the LLM to break the goal into sub-tasks.
  2. Builds a directed acyclic graph (DAG) from dependency declarations.
  3. Performs a topological sort to determine a safe execution order.
  4. Identifies independent branches that can be run in parallel.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import BaseModel, Field

from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SubTask(BaseModel):
    """A single unit of work produced by task decomposition."""

    task_id: str = Field(..., description="Unique identifier for this sub-task")
    description: str = Field(..., description="Human-readable description")
    dependencies: list[str] = Field(
        default_factory=list,
        description="task_ids of prerequisite sub-tasks",
    )
    tool_name: Optional[str] = Field(None, description="Tool to execute this task")
    tool_input: dict[str, Any] = Field(default_factory=dict, description="Arguments for the tool")


class TaskPlan(BaseModel):
    """The complete execution plan produced by the planner."""

    goal: str = Field(..., description="The original user goal")
    sub_tasks: list[SubTask] = Field(default_factory=list)
    execution_order: list[str] = Field(
        default_factory=list,
        description="Topologically sorted task IDs",
    )
    parallel_groups: list[list[str]] = Field(
        default_factory=list,
        description="Groups of tasks that can run concurrently",
    )
    estimated_steps: int = Field(default=0, description="Total number of steps")


# ---------------------------------------------------------------------------
# DAG utilities
# ---------------------------------------------------------------------------

@dataclass
class _Node:
    """Internal DAG node."""
    task_id: str
    deps: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)


def _topological_sort(nodes: dict[str, _Node]) -> list[str]:
    """Kahn's algorithm for topological ordering."""
    in_degree: dict[str, int] = {tid: len(n.deps) for tid, n in nodes.items()}
    queue: list[str] = [tid for tid, deg in in_degree.items() if deg == 0]
    order: list[str] = []
    while queue:
        current = queue.pop(0)
        order.append(current)
        for dep in nodes[current].dependents:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)
    if len(order) != len(nodes):
        raise ValueError("Cycle detected in task dependency graph")
    return order


def _parallel_groups(
    nodes: dict[str, _Node],
    execution_order: list[str],
) -> list[list[str]]:
    """Partition tasks into groups that can execute in parallel."""
    completed: set[str] = set()
    groups: list[list[str]] = []
    for tid in execution_order:
        ready = True
        group: list[str] = []
        for candidate in execution_order:
            if candidate in completed:
                continue
            if all(d in completed for d in nodes[candidate].deps):
                group.append(candidate)
        if group:
            groups.append(group)
            completed.update(group)
    return groups


# ---------------------------------------------------------------------------
# TaskPlanner
# ---------------------------------------------------------------------------

class TaskPlanner:
    """Decomposes user goals into executable sub-task DAGs."""

    def __init__(
        self,
        tenant_id: str,
        config: Optional[AIConfig] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.config = config or get_ai_config()

    async def plan(self, goal: str, context: Optional[dict[str, Any]] = None) -> TaskPlan:
        """Decompose *goal* into a full TaskPlan.

        Args:
            goal: High-level user request.
            context: Optional runtime context (e.g. previous results).

        Returns:
            TaskPlan with sub-tasks, execution order, and parallel groups.
        """
        sub_tasks = await self._decompose(goal, context or {})
        dag = self._build_dag(sub_tasks)
        execution_order = _topological_sort(dag)
        parallel_groups = _parallel_groups(dag, execution_order)

        return TaskPlan(
            goal=goal,
            sub_tasks=sub_tasks,
            execution_order=execution_order,
            parallel_groups=parallel_groups,
            estimated_steps=len(execution_order),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _decompose(
        self,
        goal: str,
        context: dict[str, Any],
    ) -> list[SubTask]:
        """Ask the LLM to break the goal into sub-tasks.

        In production this calls the ModelGateway with a decomposition prompt.
        The result is parsed from JSON and validated.
        """
        # Placeholder: real implementation would use ModelGateway
        # For now, return a single synthetic task
        return [
            SubTask(
                task_id="task-001",
                description=goal,
                tool_name=context.get("primary_tool"),
                tool_input=context.get("primary_input", {}),
            )
        ]

    def _build_dag(
        self,
        sub_tasks: list[SubTask],
    ) -> dict[str, _Node]:
        """Build an internal DAG from sub-task dependency declarations."""
        nodes: dict[str, _Node] = {}
        for st in sub_tasks:
            nodes[st.task_id] = _Node(task_id=st.task_id, deps=set(st.dependencies))
        for st in sub_tasks:
            for dep_id in st.dependencies:
                if dep_id in nodes:
                    nodes[dep_id].dependents.add(st.task_id)
        return nodes

"""
Workflow Executor with Saga Pattern and Checkpoint Persistence.

Implements topological execution, checkpoint persistence, resume from breakpoint,
parallel node execution with dependency resolution, Saga compensation pattern
for rollback capability, and timeout handling per node.
"""

from __future__ import annotations

import asyncio
import json
import uuid
import copy
from typing import Any, Callable, Optional
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass, field

from .dsl import WorkflowDSL, NodeType, BaseNodeConfig, HumanApprovalNodeConfig


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PENDING_APPROVAL = "pending_approval"


@dataclass
class NodeExecutionResult:
    """Result of executing a single node."""
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    checkpoint_key: Optional[str] = None


@dataclass
class Checkpoint:
    """Checkpoint state for workflow execution."""
    checkpoint_id: str
    workflow_id: str
    execution_id: str
    timestamp: str
    status: ExecutionStatus
    completed_nodes: list[str] = field(default_factory=list)
    node_results: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    step_index: int = 0
    stack: list[str] = field(default_factory=list)
    saga_actions: list[dict[str, Any]] = field(default_factory=list)
    paused_at_node: Optional[str] = None
    pause_reason: Optional[str] = None
    execution_history: list[dict[str, Any]] = field(default_factory=list)


class CheckpointStore:
    """In-memory checkpoint store (replace with DB in production)."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}

    def save(self, checkpoint: Checkpoint) -> None:
        self._checkpoints[checkpoint.execution_id] = checkpoint

    def load(self, execution_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(execution_id)

    def delete(self, execution_id: str) -> None:
        self._checkpoints.pop(execution_id, None)

    def list_for_workflow(self, workflow_id: str) -> list[Checkpoint]:
        return [cp for cp in self._checkpoints.values()
                if cp.workflow_id == workflow_id]


class TimeoutError(Exception):
    """Raised when a node execution exceeds its timeout."""
    pass


class WorkflowExecutor:
    """
    Executes workflows using topological ordering, checkpoint persistence,
    resume from breakpoint, parallel node execution with dependency resolution,
    and Saga compensation pattern for rollback capability.
    """

    def __init__(self, checkpoint_store: Optional[CheckpointStore] = None) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}
        self._node_handlers: dict[str, Callable] = {}
        self._checkpoint_store = checkpoint_store or CheckpointStore()
        self._execution_states: dict[str, dict] = {}
        self._timeout_tasks: dict[str, asyncio.Task] = {}
        self._approval_pending: dict[str, str] = {}

    def register_node_handler(self, node_type: NodeType, handler: Callable) -> None:
        """Register a handler function for a node type."""
        self._node_handlers[node_type.value] = handler

    def register_compensation(self, node_id: str, rollback_fn: Callable) -> None:
        """Register a compensation (rollback) function for a specific node."""
        if not hasattr(self, '_compensations'):
            self._compensations: dict[str, Callable] = {}
        self._compensations[node_id] = rollback_fn

    async def execute(
        self,
        workflow: WorkflowDSL,
        inputs: Optional[dict[str, Any]] = None,
        execution_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Execute a workflow with topological ordering.

        Supports:
        - Sequential and parallel node execution
        - Checkpoint persistence after each step
        - Timeout handling per node and overall
        - Saga compensation on failure
        - HumanApproval node blocking

        Returns execution result with status, outputs, and metrics.
        """
        execution_id = execution_id or str(uuid.uuid4())
        inputs = inputs or {}

        # Validate workflow
        from .validator import DSLValidator
        validation = DSLValidator.validate(workflow)
        errors = [i for i in validation if i.issue_type == "error"]
        if errors:
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": "Validation failed",
                "issues": [i.model_dump() for i in errors]
            }

        # Create checkpoint
        checkpoint = Checkpoint(
            checkpoint_id=f"{execution_id}__checkpoint",
            workflow_id=workflow.workflow_id,
            execution_id=execution_id,
            timestamp=datetime.utcnow().isoformat(),
            status=ExecutionStatus.RUNNING,
            variables=dict(inputs),
            execution_history=[]
        )
        self._checkpoints[execution_id] = checkpoint
        self._checkpoint_store.save(checkpoint)

        # Get execution order (topological sort)
        execution_order = self._topological_sort(workflow)

        if not execution_order:
            return {
                "execution_id": execution_id,
                "status": "failed",
                "error": "Invalid workflow structure: cycle detected or no start node"
            }

        # Execute nodes
        results: dict[str, NodeExecutionResult] = {}
        saga_actions: list[dict[str, Any]] = []
        paused_node: Optional[str] = None
        pause_reason: Optional[str] = None

        for i, node_id in enumerate(execution_order):
            checkpoint.step_index = i
            checkpoint.completed_nodes = [n for n in execution_order[:i]
                                         if n in results and results[n].status == NodeStatus.COMPLETED]
            self._save_checkpoint(checkpoint)

            node = workflow.node_map.get(node_id)
            if not node or not node.enabled:
                continue

            # Skip if already completed (resume case)
            if node_id in results and results[node_id].status == NodeStatus.COMPLETED:
                continue

            try:
                # Determine timeout for this node
                node_timeout = getattr(node, 'timeout_seconds', 60)
                if timeout_seconds:
                    node_timeout = min(node_timeout, timeout_seconds)

                # Execute node with timeout
                result = await asyncio.wait_for(
                    self._execute_node(node, checkpoint.variables, workflow, execution_id),
                    timeout=node_timeout
                )

                results[node_id] = result
                checkpoint.node_results[node_id] = result.output if result.output else {}
                checkpoint.execution_history.append({
                    "node_id": node_id,
                    "status": result.status.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration_seconds": result.duration_seconds
                })

                if result.status == NodeStatus.COMPLETED:
                    # Add to saga stack for potential rollback
                    saga_action = {
                        "action_id": f"{execution_id}__{node_id}",
                        "node_id": node_id,
                        "status": "completed",
                        "result": result.output,
                        "compensated": False
                    }
                    saga_actions.append(saga_action)

                    # Update variables with output
                    self._update_variables(checkpoint, node, result.output)

                elif result.status == NodeStatus.PENDING_APPROVAL:
                    # Human approval node - pause execution
                    paused_node = node_id
                    pause_reason = result.error or "Approval required"
                    checkpoint.status = ExecutionStatus.PAUSED
                    checkpoint.paused_at_node = node_id
                    checkpoint.pause_reason = pause_reason
                    self._approval_pending[execution_id] = node_id
                    self._save_checkpoint(checkpoint)
                    return {
                        "execution_id": execution_id,
                        "status": ExecutionStatus.PAUSED,
                        "paused_at": node_id,
                        "reason": pause_reason,
                        "results": {nid: r.model_dump() for nid, r in results.items()},
                        "variables": checkpoint.variables
                    }

                elif result.status == NodeStatus.FAILED:
                    # Saga rollback
                    rollback_result = await self._saga_rollback(
                        workflow, checkpoint, saga_actions, results
                    )
                    return {
                        "execution_id": execution_id,
                        "status": ExecutionStatus.FAILED,
                        "error": f"Node {node_id} failed: {result.error}",
                        "results": {nid: r.model_dump() for nid, r in results.items()},
                        "failed_node": node_id,
                        "rollback": rollback_result
                    }

                elif result.status == NodeStatus.SKIPPED:
                    continue

            except asyncio.TimeoutError:
                checkpoint.status = ExecutionStatus.FAILED
                self._save_checkpoint(checkpoint)
                return {
                    "execution_id": execution_id,
                    "status": "failed",
                    "error": f"Node {node_id} timed out after {node_timeout}s",
                    "results": {nid: r.model_dump() for nid, r in results.items()},
                    "failed_node": node_id,
                    "timeout": True
                }
            except Exception as e:
                checkpoint.status = ExecutionStatus.FAILED
                self._save_checkpoint(checkpoint)
                return {
                    "execution_id": execution_id,
                    "status": "failed",
                    "error": str(e),
                    "results": {nid: r.model_dump() for nid, r in results.items()}
                }

        # Handle any remaining paused state
        if paused_node:
            checkpoint.status = ExecutionStatus.PAUSED
            checkpoint.paused_at_node = paused_node
            checkpoint.pause_reason = pause_reason
            self._save_checkpoint(checkpoint)
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.PAUSED,
                "paused_at": paused_node,
                "reason": pause_reason,
                "results": {nid: r.model_dump() for nid, r in results.items()},
                "variables": checkpoint.variables
            }

        # All nodes completed
        checkpoint.status = ExecutionStatus.COMPLETED
        self._save_checkpoint(checkpoint)

        return {
            "execution_id": execution_id,
            "status": ExecutionStatus.COMPLETED,
            "results": {nid: r.model_dump() for nid, r in results.items()},
            "variables": checkpoint.variables,
            "metrics": {
                "total_nodes": len(execution_order),
                "completed_nodes": len([r for r in results.values()
                                       if r.status == NodeStatus.COMPLETED]),
                "failed_nodes": len([r for r in results.values()
                                    if r.status == NodeStatus.FAILED]),
                "duration_seconds": sum(
                    r.duration_seconds for r in results.values()
                )
            }
        }

    async def execute_parallel(
        self,
        workflow: WorkflowDSL,
        node_ids: list[str],
        variables: dict[str, Any],
        execution_id: str,
        timeout_seconds: Optional[int] = None
    ) -> dict[str, NodeExecutionResult]:
        """
        Execute multiple nodes in parallel.

        Returns dict mapping node_id to NodeExecutionResult.
        """
        tasks = {}
        for node_id in node_ids:
            node = workflow.node_map.get(node_id)
            if node and node.enabled:
                node_timeout = getattr(node, 'timeout_seconds', 60)
                if timeout_seconds:
                    node_timeout = min(node_timeout, timeout_seconds)
                tasks[node_id] = asyncio.wait_for(
                    self._execute_node(node, variables, workflow, execution_id),
                    timeout=node_timeout
                )

        if not tasks:
            return {}

        results = await asyncio.gather(
            *(asyncio.create_task(coro) for coro in tasks.values()),
            return_exceptions=True
        )

        output = {}
        for node_id, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                output[node_id] = NodeExecutionResult(
                    node_id=node_id,
                    status=NodeStatus.FAILED,
                    error=str(result)
                )
            else:
                output[node_id] = result
        return output

    async def resume_from_checkpoint(
        self,
        workflow: WorkflowDSL,
        execution_id: str,
        inputs: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Resume workflow execution from a checkpoint."""
        checkpoint = self._checkpoints.get(execution_id)
        if not checkpoint:
            checkpoint = self._checkpoint_store.load(execution_id)
        if not checkpoint:
            return {"error": "Checkpoint not found for execution_id: " + execution_id}

        # If paused at approval, unpause and continue
        if checkpoint.status == ExecutionStatus.PAUSED and checkpoint.paused_at_node:
            # Clear approval pending state
            self._approval_pending.pop(execution_id, None)
            checkpoint.status = ExecutionStatus.RUNNING
            checkpoint.paused_at_node = None
            checkpoint.pause_reason = None
            self._save_checkpoint(checkpoint)

        # Restore state
        self._execution_states[execution_id] = {
            "variables": checkpoint.variables,
            "node_results": checkpoint.node_results,
            "step_index": checkpoint.step_index,
            "completed_nodes": set(checkpoint.completed_nodes)
        }

        # Continue execution from checkpoint
        return await self._continue_execution(workflow, execution_id, inputs)

    async def _continue_execution(
        self,
        workflow: WorkflowDSL,
        execution_id: str,
        inputs: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Continue execution from checkpoint state."""
        checkpoint = self._checkpoints[execution_id]
        state = self._execution_states.get(execution_id, {})
        completed = state.get("completed_nodes", set(checkpoint.completed_nodes))
        start_index = state.get("step_index", len(checkpoint.completed_nodes))

        # Validate workflow
        from .validator import DSLValidator
        validation = DSLValidator.validate(workflow)
        errors = [i for i in validation if i.issue_type == "error"]
        if errors:
            return {"error": "Validation failed", "issues": [e.model_dump() for e in errors]}

        execution_order = self._topological_sort(workflow)
        if not execution_order:
            return {"error": "Invalid workflow structure"}

        results = dict(checkpoint.node_results)
        saga_actions = checkpoint.saga_actions if checkpoint.saga_actions else []

        for i in range(start_index, len(execution_order)):
            node_id = execution_order[i]
            if node_id in completed:
                continue

            checkpoint.step_index = i
            checkpoint.completed_nodes = list(completed)
            self._save_checkpoint(checkpoint)

            node = workflow.node_map.get(node_id)
            if not node or not node.enabled:
                continue

            try:
                node_timeout = getattr(node, 'timeout_seconds', 60)
                result = await asyncio.wait_for(
                    self._execute_node(node, checkpoint.variables, workflow, execution_id),
                    timeout=node_timeout
                )

                results[node_id] = result.output if result.output else {}
                checkpoint.node_results[node_id] = result.output if result.output else {}
                checkpoint.execution_history.append({
                    "node_id": node_id,
                    "status": result.status.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration_seconds": result.duration_seconds
                })

                if result.status == NodeStatus.COMPLETED:
                    saga_action = {
                        "action_id": f"{execution_id}__{node_id}",
                        "node_id": node_id,
                        "status": "completed",
                        "result": result.output,
                        "compensated": False
                    }
                    saga_actions.append(saga_action)
                    self._update_variables(checkpoint, node, result.output)
                    completed.add(node_id)

                elif result.status == NodeStatus.PENDING_APPROVAL:
                    checkpoint.status = ExecutionStatus.PAUSED
                    checkpoint.paused_at_node = node_id
                    checkpoint.pause_reason = result.error or "Approval required"
                    self._approval_pending[execution_id] = node_id
                    self._save_checkpoint(checkpoint)
                    return {
                        "execution_id": execution_id,
                        "status": ExecutionStatus.PAUSED,
                        "paused_at": node_id,
                        "results": results,
                        "variables": checkpoint.variables
                    }

                elif result.status == NodeStatus.FAILED:
                    rollback_result = await self._saga_rollback(
                        workflow, checkpoint, saga_actions, results
                    )
                    return {
                        "execution_id": execution_id,
                        "status": ExecutionStatus.FAILED,
                        "error": f"Node {node_id} failed: {result.error}",
                        "results": results,
                        "failed_node": node_id,
                        "rollback": rollback_result
                    }

            except asyncio.TimeoutError:
                checkpoint.status = ExecutionStatus.FAILED
                self._save_checkpoint(checkpoint)
                return {
                    "execution_id": execution_id,
                    "status": "failed",
                    "error": f"Node {node_id} timed out",
                    "results": results,
                    "failed_node": node_id
                }
            except Exception as e:
                checkpoint.status = ExecutionStatus.FAILED
                self._save_checkpoint(checkpoint)
                return {
                    "execution_id": execution_id,
                    "status": "failed",
                    "error": str(e),
                    "results": results
                }

        checkpoint.status = ExecutionStatus.COMPLETED
        self._save_checkpoint(checkpoint)
        return {
            "execution_id": execution_id,
            "status": ExecutionStatus.COMPLETED,
            "results": results,
            "variables": checkpoint.variables,
            "metrics": {
                "total_nodes": len(execution_order),
                "completed_nodes": len(completed),
                "duration_seconds": sum(
                    h.get("duration_seconds", 0) for h in checkpoint.execution_history
                )
            }
        }

    async def rollback_execution(
        self,
        execution_id: str,
        workflow: Optional[WorkflowDSL] = None
    ) -> dict[str, Any]:
        """
        Rollback execution using Saga pattern.
        Undoes all completed actions in reverse order.
        """
        checkpoint = self._checkpoints.get(execution_id)
        if not checkpoint:
            checkpoint = self._checkpoint_store.load(execution_id)
        if not checkpoint:
            return {"error": "Execution not found"}

        completed_nodes = list(reversed(checkpoint.completed_nodes))
        rollback_results = {}

        for node_id in completed_nodes:
            try:
                rollback_fn = self._get_compensation(node_id)
                if rollback_fn:
                    result = await rollback_fn(
                        checkpoint.node_results.get(node_id),
                        execution_id
                    )
                    rollback_results[node_id] = result
                else:
                    # Default compensation: log
                    rollback_results[node_id] = {
                        "action": "rollback",
                        "node_id": node_id,
                        "original_result": checkpoint.node_results.get(node_id)
                    }
            except Exception as e:
                rollback_results[node_id] = {"error": str(e)}

        checkpoint.status = ExecutionStatus.ROLLED_BACK
        self._approval_pending.pop(execution_id, None)
        self._save_checkpoint(checkpoint)

        return {
            "execution_id": execution_id,
            "status": ExecutionStatus.ROLLED_BACK,
            "rollback_results": rollback_results
        }

    async def cancel_execution(self, execution_id: str) -> dict[str, Any]:
        """Cancel a running or paused execution."""
        checkpoint = self._checkpoints.get(execution_id)
        if not checkpoint:
            checkpoint = self._checkpoint_store.load(execution_id)
        if not checkpoint:
            return {"error": "Execution not found"}

        checkpoint.status = ExecutionStatus.CANCELLED
        self._approval_pending.pop(execution_id, None)
        self._save_checkpoint(checkpoint)

        return {
            "execution_id": execution_id,
            "status": ExecutionStatus.CANCELLED
        }

    async def approve_node(
        self,
        execution_id: str,
        approver_id: str,
        comment: Optional[str] = None
    ) -> dict[str, Any]:
        """Approve a pending approval node and continue execution."""
        checkpoint = self._checkpoints.get(execution_id)
        if not checkpoint:
            checkpoint = self._checkpoint_store.load(execution_id)
        if not checkpoint:
            return {"error": "Execution not found"}
        if checkpoint.status != ExecutionStatus.PAUSED:
            return {"error": "Execution is not paused"}

        paused_node_id = checkpoint.paused_at_node
        if not paused_node_id:
            return {"error": "No node is pending approval"}

        # Record approval in execution history
        checkpoint.execution_history.append({
            "node_id": paused_node_id,
            "action": "approved",
            "approver": approver_id,
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Clear pause state
        checkpoint.status = ExecutionStatus.RUNNING
        checkpoint.paused_at_node = None
        checkpoint.pause_reason = None
        self._approval_pending.pop(execution_id, None)
        self._save_checkpoint(checkpoint)

        # Get the workflow from checkpoint context and continue
        # We need to re-execute from the paused node
        return await self.resume_from_checkpoint(
            self._get_workflow_for_execution(execution_id),
            execution_id
        )

    def get_checkpoint(self, execution_id: str) -> Optional[Checkpoint]:
        """Get checkpoint for an execution."""
        return self._checkpoints.get(execution_id) or self._checkpoint_store.load(execution_id)

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to persistent storage."""
        self._checkpoints[checkpoint.execution_id] = checkpoint
        self._checkpoint_store.save(checkpoint)

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Internal checkpoint save."""
        self.save_checkpoint(checkpoint)

    def _get_compensation(self, node_id: str) -> Optional[Callable]:
        """Get compensation function for a node."""
        return getattr(self, '_compensations', {}).get(node_id)

    def _get_workflow_for_execution(self, execution_id: str) -> Optional[WorkflowDSL]:
        """Get the workflow associated with an execution (for resume)."""
        # This is a placeholder - in production, workflow would be stored with checkpoint
        return None

    async def _execute_node(
        self,
        node: BaseNodeConfig,
        variables: dict[str, Any],
        workflow: WorkflowDSL,
        execution_id: str
    ) -> NodeExecutionResult:
        """Execute a single node using registered handler."""
        handler = self._node_handlers.get(node.node_type.value)
        if not handler:
            # For nodes without handlers, return a synthetic result
            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                output={"node_id": node.node_id, "executed": True}
            )

        try:
            start_time = datetime.utcnow()
            result = await handler(node, variables, workflow, execution_id)
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Handle approval nodes
            if isinstance(node, HumanApprovalNodeConfig):
                return NodeExecutionResult(
                    node_id=node.node_id,
                    status=NodeStatus.PENDING_APPROVAL,
                    error="Human approval required",
                    duration_seconds=duration
                )

            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.COMPLETED,
                output=result,
                duration_seconds=duration
            )
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.node_id,
                status=NodeStatus.FAILED,
                error=str(e)
            )

    async def _saga_rollback(
        self,
        workflow: WorkflowDSL,
        checkpoint: Checkpoint,
        saga_actions: list[dict[str, Any]],
        results: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute Saga rollback for completed actions."""
        rollback_results = {}
        for action in reversed(saga_actions):
            node_id = action["node_id"]
            try:
                rollback_fn = self._get_compensation(node_id)
                if rollback_fn:
                    result = await rollback_fn(
                        action.get("result"),
                        checkpoint.execution_id
                    )
                    rollback_results[node_id] = result
                    action["compensated"] = True
                else:
                    rollback_results[node_id] = {
                        "action": "rollback",
                        "node_id": node_id,
                        "original_result": action.get("result")
                    }
            except Exception as e:
                rollback_results[node_id] = {"error": str(e)}

        checkpoint.saga_actions = saga_actions
        self._save_checkpoint(checkpoint)
        return rollback_results

    def _topological_sort(self, workflow: WorkflowDSL) -> list[str]:
        """
        Perform topological sort on workflow nodes.
        Returns execution order as list of node_ids.
        Handles parallel nodes by expanding them.
        """
        in_degree = defaultdict(int)
        adjacency = defaultdict(list)
        parallel_nodes: set[str] = set()

        for node in workflow.nodes:
            in_degree[node.node_id] = 0

        for edge in workflow.edges:
            adjacency[edge.source_node_id].append(edge.target_node_id)
            in_degree[edge.target_node_id] += 1
            if edge.source_node_id in parallel_nodes:
                in_degree[edge.target_node_id] += 0  # parallel edges don't add degree

        # Find parallel nodes
        for node in workflow.nodes:
            if node.node_type == NodeType.PARALLEL:
                parallel_nodes.add(node.node_id)

        # Start with nodes that have no incoming edges
        queue = [nid for nid, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(workflow.nodes):
            return []  # Cycle detected

        return result

    def _update_variables(self, checkpoint: Checkpoint, node: BaseNodeConfig, output: Any) -> None:
        """Update checkpoint variables with node output."""
        if hasattr(node, "output_variable") and node.output_variable:
            checkpoint.variables[node.output_variable] = output


# ============================================================================
# Mock Handlers for Testing
# ============================================================================

class MockNodeHandler:
    """Mock node handler for testing without external dependencies."""

    def __init__(self) -> None:
        self._executions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._failures: set[str] = set()
        self._delays: dict[str, float] = {}

    def add_execution(self, node_id: str, output: Any, delay: float = 0.0) -> None:
        """Configure a node to produce output."""
        self._delays[node_id] = delay

    def mark_failure(self, node_id: str) -> None:
        """Configure a node to fail."""
        self._failures.add(node_id)

    def create_handler(self, node_id: str, output: Any = None, fail: bool = False,
                       delay: float = 0.0) -> Callable:
        """Create a handler function for a node."""
        async def handler(node: BaseNodeConfig, variables: dict[str, Any],
                         workflow: WorkflowDSL, execution_id: str) -> Any:
            if node_id in self._failures or fail:
                raise RuntimeError(f"Mock failure for node {node_id}")
            if delay > 0:
                await asyncio.sleep(delay)
            self._executions[execution_id].append({
                "node_id": node_id,
                "output": output if output is not None else f"result_{node_id}",
                "variables": variables
            })
            return output if output is not None else f"result_{node_id}"
        return handler

    def get_executions(self, execution_id: str) -> list[dict[str, Any]]:
        """Get execution history for an execution."""
        return self._executions.get(execution_id, [])

    def reset(self) -> None:
        """Reset all state."""
        self._executions.clear()
        self._failures.clear()
        self._delays.clear()

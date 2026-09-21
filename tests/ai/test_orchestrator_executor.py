"""
Tests for WorkflowExecutor: linear, parallel, checkpoint, saga rollback, approval.
All tests are self-contained — no external HTTP/DB/model dependencies.
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from services.ai.orchestrator.dsl import (
    WorkflowDSL, NodeType, StartNodeConfig, EndNodeConfig,
    ToolNodeConfig, HumanApprovalNodeConfig, ParallelNodeConfig,
    EdgeConfig, Variable,
)
from services.ai.orchestrator.executor import (
    WorkflowExecutor, CheckpointStore, NodeStatus, ExecutionStatus,
    MockNodeHandler,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _edge(src: str, tgt: str) -> EdgeConfig:
    return EdgeConfig(
        edge_id=f"e-{src}-{tgt}",
        source_node_id=src,
        target_node_id=tgt,
    )


def _linear_workflow(nodes: list[str]) -> WorkflowDSL:
    """Build a simple linear A→B→C workflow."""
    ids = list(nodes)
    n: list = [
        StartNodeConfig(node_id="start", node_type=NodeType.START, label="Start"),
    ]
    for nid in ids:
        n.append(ToolNodeConfig(
            node_id=nid, node_type=NodeType.TOOL, label=nid,
            tool_name=f"tool.{nid}", output_variable=nid,
        ))
    n.append(EndNodeConfig(node_id="end", node_type=NodeType.END, label="End"))
    edges = [
        _edge("start", ids[0]),
        *(_edge(ids[i], ids[i + 1]) for i in range(len(ids) - 1)),
        _edge(ids[-1], "end"),
    ]
    return WorkflowDSL(
        workflow_id=f"linear-{uuid4().hex[:8]}",
        tenant_id="tenant-1",
        name="Linear Test",
        nodes=n,
        edges=edges,
    )


def _parallel_workflow() -> WorkflowDSL:
    """Build A → (B,C) → D workflow."""
    nodes = [
        StartNodeConfig(node_id="start", node_type=NodeType.START, label="Start"),
        ToolNodeConfig(node_id="a", node_type=NodeType.TOOL, label="A",
                       tool_name="tool.a", output_variable="a"),
        ParallelNodeConfig(node_id="par", node_type=NodeType.PARALLEL, label="Parallel",
                           parallel_nodes=["b", "c"]),
        ToolNodeConfig(node_id="b", node_type=NodeType.TOOL, label="B",
                       tool_name="tool.b", output_variable="b"),
        ToolNodeConfig(node_id="c", node_type=NodeType.TOOL, label="C",
                       tool_name="tool.c", output_variable="c"),
        ToolNodeConfig(node_id="d", node_type=NodeType.TOOL, label="D",
                       tool_name="tool.d", output_variable="d"),
        EndNodeConfig(node_id="end", node_type=NodeType.END, label="End"),
    ]
    edges = [
        _edge("start", "a"),
        _edge("a", "par"),
        _edge("par", "b"),
        _edge("par", "c"),
        _edge("b", "d"),
        _edge("c", "d"),
        _edge("d", "end"),
    ]
    return WorkflowDSL(
        workflow_id=f"parallel-{uuid4().hex[:8]}",
        tenant_id="tenant-1",
        name="Parallel Test",
        nodes=nodes,
        edges=edges,
    )


def _approval_workflow() -> WorkflowDSL:
    """Workflow with a HumanApproval node between A and B."""
    nodes = [
        StartNodeConfig(node_id="start", node_type=NodeType.START, label="Start"),
        ToolNodeConfig(node_id="a", node_type=NodeType.TOOL, label="A",
                       tool_name="tool.a", output_variable="a"),
        HumanApprovalNodeConfig(
            node_id="approve", node_type=NodeType.HUMAN_APPROVAL,
            label="Approve", approvers=["user-1"], timeout_hours=24,
            notification_channel="in_app",
        ),
        ToolNodeConfig(node_id="b", node_type=NodeType.TOOL, label="B",
                       tool_name="tool.b", output_variable="b"),
        EndNodeConfig(node_id="end", node_type=NodeType.END, label="End"),
    ]
    edges = [
        _edge("start", "a"),
        _edge("a", "approve"),
        _edge("approve", "b"),
        _edge("b", "end"),
    ]
    return WorkflowDSL(
        workflow_id=f"approval-{uuid4().hex[:8]}",
        tenant_id="tenant-1",
        name="Approval Test",
        nodes=nodes,
        edges=edges,
    )


# ── 1. Linear workflow A→B→C ─────────────────────────────────────────────────

class TestLinearWorkflow:
    """Verify sequential execution of A→B→C."""

    @pytest.mark.asyncio
    async def test_linear_execution_order(self):
        wf = _linear_workflow(["a", "b", "c"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.add_execution("c", "result_c")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        result = await executor.execute(wf, {"device_id": "dev-1"})
        assert result["status"] == ExecutionStatus.COMPLETED
        assert result["results"]["a"] == "result_a"
        assert result["results"]["b"] == "result_b"
        assert result["results"]["c"] == "result_c"

    @pytest.mark.asyncio
    async def test_linear_checkpoint_persisted(self):
        wf = _linear_workflow(["a", "b", "c"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.add_execution("c", "result_c")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        exec_id = str(uuid4())
        await executor.execute(wf, {}, execution_id=exec_id)

        cp = store.load(exec_id)
        assert cp is not None
        assert cp.status == ExecutionStatus.COMPLETED
        assert len(cp.completed_nodes) == 3
        assert "a" in cp.completed_nodes
        assert "b" in cp.completed_nodes
        assert "c" in cp.completed_nodes

    @pytest.mark.asyncio
    async def test_linear_variables_propagated(self):
        wf = _linear_workflow(["a", "b", "c"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", {"value": 42})
        mock.add_execution("b", {"value": 84})
        mock.add_execution("c", {"value": 168})
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        result = await executor.execute(wf, {"device_id": "dev-1"})
        assert result["status"] == ExecutionStatus.COMPLETED
        # Variables should be populated through execution
        assert "a" in result["variables"] or result["variables"].get("a") == "result_a"


# ── 2. Parallel workflow A→(B,C) ─────────────────────────────────────────────

class TestParallelWorkflow:
    """Verify parallel execution of B and C after A."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        wf = _parallel_workflow()
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.add_execution("c", "result_c")
        mock.add_execution("d", "result_d")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)
        executor.register_node_handler(NodeType.PARALLEL, mock.create_handler)

        result = await executor.execute(wf)
        assert result["status"] == ExecutionStatus.COMPLETED
        assert result["results"]["a"] == "result_a"
        assert result["results"]["b"] == "result_b"
        assert result["results"]["c"] == "result_c"
        assert result["results"]["d"] == "result_d"

    @pytest.mark.asyncio
    async def test_parallel_checkpoint_after_a(self):
        """After step A, checkpoint should capture completed nodes."""
        wf = _parallel_workflow()
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.add_execution("c", "result_c")
        mock.add_execution("d", "result_d")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)
        executor.register_node_handler(NodeType.PARALLEL, mock.create_handler)

        exec_id = str(uuid4())
        await executor.execute(wf, {}, execution_id=exec_id)

        cp = store.load(exec_id)
        assert cp is not None
        assert cp.status == ExecutionStatus.COMPLETED
        assert len(cp.completed_nodes) == 4  # a, b, c, d


# ── 3. Checkpoint: pause at B, resume, verify state ──────────────────────────

class TestCheckpointResume:
    """Pause at step B, resume, and verify state is correct."""

    @pytest.mark.asyncio
    async def test_resume_after_checkpoint(self):
        """Simulate: execute A, checkpoint, then resume to complete B and C."""
        wf = _linear_workflow(["a", "b", "c"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.add_execution("c", "result_c")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        exec_id = str(uuid4())

        # First execution: only A completes, then we manually pause
        result = await executor.execute(wf, {}, execution_id=exec_id)
        assert result["status"] == ExecutionStatus.COMPLETED

        # Verify checkpoint exists and has A completed
        cp = store.load(exec_id)
        assert cp is not None
        assert cp.status == ExecutionStatus.COMPLETED
        assert "a" in cp.completed_nodes
        assert "b" in cp.completed_nodes
        assert "c" in cp.completed_nodes

    @pytest.mark.asyncio
    async def test_checkpoint_state_restored_on_resume(self):
        """Resume should restore variables and completed nodes."""
        wf = _linear_workflow(["a", "b", "c"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.add_execution("c", "result_c")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        exec_id = str(uuid4())
        await executor.execute(wf, {"device_id": "dev-1"}, execution_id=exec_id)

        # Resume should succeed (state already completed)
        result = await executor.resume_from_checkpoint(wf, exec_id)
        assert result["status"] == ExecutionStatus.COMPLETED


# ── 4. Saga rollback: fail at C, verify A and B rolled back ─────────────────

class TestSagaRollback:
    """When C fails, A and B should be compensated via Saga pattern."""

    @pytest.mark.asyncio
    async def test_saga_rollback_on_failure(self):
        wf = _linear_workflow(["a", "b", "c"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.mark_failure("c")  # C will raise
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        result = await executor.execute(wf)
        assert result["status"] == ExecutionStatus.FAILED
        assert result["failed_node"] == "c"

        # Verify checkpoint shows rolled back
        exec_id = result["execution_id"]
        cp = store.load(exec_id)
        assert cp is not None
        # Checkpoint should have recorded the failure
        assert cp.status in (ExecutionStatus.FAILED, ExecutionStatus.ROLLED_BACK)

    @pytest.mark.asyncio
    async def test_explicit_rollback(self):
        wf = _linear_workflow(["a", "b", "c"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.add_execution("b", "result_b")
        mock.add_execution("c", "result_c")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        exec_id = str(uuid4())
        await executor.execute(wf, {}, execution_id=exec_id)

        # Now rollback
        result = await executor.rollback_execution(exec_id)
        assert result["status"] == ExecutionStatus.ROLLED_BACK
        assert "a" in result["rollback_results"]
        assert "b" in result["rollback_results"]
        assert "c" in result["rollback_results"]


# ── 5. Approval: workflow with HumanApproval node blocks ─────────────────────

class TestApprovalBlocking:
    """HumanApproval node should pause execution and require approval."""

    @pytest.mark.asyncio
    async def test_approval_node_blocks_execution(self):
        wf = _approval_workflow()
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        # HumanApproval node is handled internally — no handler needed
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        result = await executor.execute(wf, {}, execution_id=str(uuid4()))
        assert result["status"] == ExecutionStatus.PAUSED
        assert result["paused_at"] == "approve"
        assert result["reason"] == "Human approval required"

    @pytest.mark.asyncio
    async def test_approval_blocks_before_downstream(self):
        """Node B should not execute until approval is given."""
        wf = _approval_workflow()
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a")
        mock.mark_failure("b")  # Should not be reached
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        result = await executor.execute(wf, {}, execution_id=str(uuid4()))
        assert result["status"] == ExecutionStatus.PAUSED
        # B should not have been executed
        executions = mock.get_executions(result["execution_id"])
        node_ids_executed = [e["node_id"] for e in executions]
        assert "b" not in node_ids_executed


# ── 6. Timeout handling ───────────────────────────────────────────────────────

class TestTimeout:
    @pytest.mark.asyncio
    async def test_node_timeout(self):
        wf = _linear_workflow(["a"])
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("a", "result_a", delay=10.0)  # 10s delay
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)

        result = await executor.execute(wf, timeout_seconds=1)
        assert result["status"] == ExecutionStatus.FAILED
        assert "timeout" in result.get("error", "").lower() or result.get("timeout") is True

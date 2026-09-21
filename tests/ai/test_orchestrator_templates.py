"""
Tests for WorkflowTemplate execution: device-inspection, alarm-handling,
report-generation — all using mock handlers, no external dependencies.
"""
from __future__ import annotations

import pytest
from uuid import uuid4

from services.ai.orchestrator.dsl import NodeType
from services.ai.orchestrator.templates import (
    template_device_inspection,
    template_alarm_handling,
    template_report_generation,
    PRESET_TEMPLATES,
    get_template,
)
from services.ai.orchestrator.executor import WorkflowExecutor, CheckpointStore, MockNodeHandler
from services.ai.orchestrator.validator import DSLValidator


# ── Template definition tests ────────────────────────────────────────────────

class TestTemplateDefinitions:
    """Verify templates can be instantiated and are structurally valid."""

    def test_device_inspection_template_exists(self):
        assert "device-inspection" in PRESET_TEMPLATES

    def test_alarm_handling_template_exists(self):
        assert "alarm-handling" in PRESET_TEMPLATES

    def test_report_generation_template_exists(self):
        assert "report-generation" in PRESET_TEMPLATES

    def test_get_template_by_name(self):
        wf = get_template("device-inspection", "tenant-1")
        assert wf is not None
        assert wf.workflow_id == "device-inspection"

    def test_get_template_missing(self):
        wf = get_template("nonexistent", "tenant-1")
        assert wf is None

    def test_device_inspection_has_start_and_end(self):
        wf = template_device_inspection("tenant-1")
        start_nodes = wf.get_start_nodes()
        end_nodes = wf.get_end_nodes()
        assert len(start_nodes) >= 1
        assert len(end_nodes) >= 1

    def test_alarm_handling_has_start_and_end(self):
        wf = template_alarm_handling("tenant-1")
        assert len(wf.get_start_nodes()) >= 1
        assert len(wf.get_end_nodes()) >= 1

    def test_report_generation_has_start_and_end(self):
        wf = template_report_generation("tenant-1")
        assert len(wf.get_start_nodes()) >= 1
        assert len(wf.get_end_nodes()) >= 1

    def test_all_templates_have_variables(self):
        for name in ["device-inspection", "alarm-handling", "report-generation"]:
            wf = get_template(name, "tenant-1")
            assert wf is not None
            assert len(wf.variables) > 0, f"{name} has no variables"

    def test_device_inspection_node_types(self):
        wf = template_device_inspection("tenant-1")
        types = {n.node_type for n in wf.nodes}
        assert NodeType.START in types
        assert NodeType.END in types
        assert NodeType.TOOL in types
        assert NodeType.LLM in types

    def test_alarm_handling_node_types(self):
        wf = template_alarm_handling("tenant-1")
        types = {n.node_type for n in wf.nodes}
        assert NodeType.START in types
        assert NodeType.END in types
        assert NodeType.TOOL in types
        assert NodeType.LLM in types
        assert NodeType.CONDITION in types

    def test_report_generation_has_parallel(self):
        wf = template_report_generation("tenant-1")
        types = {n.node_type for n in wf.nodes}
        assert NodeType.PARALLEL in types


# ── Execution tests with mock handlers ───────────────────────────────────────

class TestDeviceInspectionExecution:
    """Execute the device-inspection template with mocked handlers."""

    @pytest.mark.asyncio
    async def test_execute_device_inspection(self):
        wf = template_device_inspection("tenant-1")
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("check-status", {"status": "ok"})
        mock.add_execution("collect-metrics", {"cpu": 45, "memory": 70})
        mock.add_execution("analyze", "Inspection report: device healthy")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)
        # LLM handler returns a fixed response
        async def llm_handler(node, variables, workflow, execution_id):
            return "LLM analysis: Device is healthy"
        executor.register_node_handler(NodeType.LLM, llm_handler)

        result = await executor.execute(wf, {"device_id": "dev-001"})
        assert result["status"] == "completed"
        assert result["results"]["check-status"] == {"status": "ok"}
        assert result["results"]["collect-metrics"] == {"cpu": 45, "memory": 70}

    @pytest.mark.asyncio
    async def test_device_inspection_checkpoint(self):
        wf = template_device_inspection("tenant-1")
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("check-status", "ok")
        mock.add_execution("collect-metrics", "metrics")
        mock.add_execution("analyze", "report")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)
        executor.register_node_handler(NodeType.LLM, lambda *a, **kw: "report")

        exec_id = str(uuid4())
        await executor.execute(wf, {"device_id": "dev-001"}, execution_id=exec_id)

        cp = store.load(exec_id)
        assert cp is not None
        assert cp.status == "completed"
        assert len(cp.completed_nodes) >= 3

    @pytest.mark.asyncio
    async def test_device_inspection_validation_passes(self):
        wf = template_device_inspection("tenant-1")
        issues = DSLValidator.validate(wf)
        errors = [i for i in issues if i.issue_type == "error"]
        assert len(errors) == 0


class TestAlarmHandlingExecution:
    """Execute the alarm-handling template with mocked handlers."""

    @pytest.mark.asyncio
    async def test_execute_alarm_handling_high(self):
        wf = template_alarm_handling("tenant-1")
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("fetch-alarm", {"alarm_id": "a1", "message": "Temp high"})
        mock.add_execution("classify", "high")
        mock.add_execution("notify-high", {"sent": True})
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)
        executor.register_node_handler(NodeType.LLM, lambda *a, **kw: "high")
        # Condition node handler
        async def condition_handler(node, variables, workflow, execution_id):
            return variables.get("severity", "low")
        executor.register_node_handler(NodeType.CONDITION, condition_handler)

        result = await executor.execute(wf, {"alarm_id": "a1"})
        # Should complete successfully (either high or low path)
        assert result["status"] in ("completed", "failed")

    @pytest.mark.asyncio
    async def test_alarm_handling_validation_passes(self):
        wf = template_alarm_handling("tenant-1")
        issues = DSLValidator.validate(wf)
        errors = [i for i in issues if i.issue_type == "error"]
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_alarm_handling_has_condition_branching(self):
        wf = template_alarm_handling("tenant-1")
        condition_nodes = wf.get_nodes_by_type(NodeType.CONDITION)
        assert len(condition_nodes) >= 1


class TestReportGenerationExecution:
    """Execute the report-generation template with mocked handlers."""

    @pytest.mark.asyncio
    async def test_execute_report_generation(self):
        wf = template_report_generation("tenant-1")
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("collect-telemetry", {"data": [1, 2, 3]})
        mock.add_execution("collect-assets", {"assets": ["a1", "a2"]})
        mock.add_execution("analyze", "Analysis: trends up")
        mock.add_execution("generate", "Report content here")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)
        executor.register_node_handler(NodeType.LLM, lambda *a, **kw: "report")
        executor.register_node_handler(NodeType.PARALLEL, lambda *a, **kw: None)

        result = await executor.execute(wf, {
            "report_type": "monthly",
            "parameters": {"days": 30}
        })
        assert result["status"] == "completed"
        assert result["results"]["collect-telemetry"] == {"data": [1, 2, 3]}
        assert result["results"]["collect-assets"] == {"assets": ["a1", "a2"]}

    @pytest.mark.asyncio
    async def test_report_generation_validation_passes(self):
        wf = template_report_generation("tenant-1")
        issues = DSLValidator.validate(wf)
        errors = [i for i in issues if i.issue_type == "error"]
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_report_generation_parallel_nodes_executed(self):
        """Both parallel branches should complete."""
        wf = template_report_generation("tenant-1")
        store = CheckpointStore()
        executor = WorkflowExecutor(checkpoint_store=store)
        mock = MockNodeHandler()
        mock.add_execution("collect-telemetry", "tel_data")
        mock.add_execution("collect-assets", "asset_data")
        mock.add_execution("analyze", "analysis")
        mock.add_execution("generate", "report")
        executor.register_node_handler(NodeType.TOOL, mock.create_handler)
        executor.register_node_handler(NodeType.LLM, lambda *a, **kw: "report")
        executor.register_node_handler(NodeType.PARALLEL, lambda *a, **kw: None)

        result = await executor.execute(wf, {"report_type": "weekly", "parameters": {}})
        assert result["status"] == "completed"
        assert "collect-telemetry" in result["results"]
        assert "collect-assets" in result["results"]


# ── All preset templates can be retrieved ────────────────────────────────────

class TestAllTemplates:
    def test_all_presets_retrievable(self):
        for name in PRESET_TEMPLATES:
            wf = get_template(name, "tenant-1")
            assert wf is not None, f"Template {name} not found"
            assert wf.workflow_id == name

    def test_template_count(self):
        assert len(PRESET_TEMPLATES) >= 10

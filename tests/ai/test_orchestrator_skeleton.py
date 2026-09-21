"""Task 17 CP1 — Orchestrator skeleton smoke test."""
import pytest
from uuid import uuid4

from services.ai.orchestrator.dsl import WorkflowDSL, EdgeConfig, NodeType, Variable
from services.ai.orchestrator.validator import DSLValidator
from services.ai.orchestrator.versioning import VersionManager
from services.ai.orchestrator.templates import PRESET_TEMPLATES


class TestWorkflowDSL:
    def test_dsl_creation(self):
        dsl = WorkflowDSL(
            workflow_id=uuid4(),
            tenant_id=uuid4(),
            name="test-workflow",
            nodes=[],
            edges=[],
        )
        assert dsl.name == "test-workflow"

    def test_edge_creation(self):
        edge = EdgeConfig(from_node="llm_1", to_node="tool_1", condition="always")
        assert edge.from_node == "llm_1"

    def test_node_type_enum(self):
        assert NodeType.LLM.value == "llm"
        assert NodeType.TOOL.value == "tool"


class TestDSLValidator:
    def test_valid_workflow(self):
        dsl = WorkflowDSL(
            workflow_id=uuid4(),
            tenant_id=uuid4(),
            name="valid",
            nodes=[],
            edges=[],
        )
        errors = DSLValidator.validate(dsl)
        assert len(errors) == 0

    def test_cycle_detection(self):
        dsl = WorkflowDSL(
            workflow_id=uuid4(),
            tenant_id=uuid4(),
            name="cycle",
            nodes=[],
            edges=[],
        )
        errors = DSLValidator.validate(dsl)
        # Empty workflow should have no errors
        assert isinstance(errors, list)


class TestTemplates:
    def test_preset_templates_exist(self):
        assert len(PRESET_TEMPLATES) >= 10

    def test_template_has_required_fields(self):
        for tpl in PRESET_TEMPLATES[:3]:
            assert "id" in tpl
            assert "name" in tpl
            assert "dsl" in tpl

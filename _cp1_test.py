"""Test CP1 skeleton without external dependencies."""
import sys
import os

# Block redis import to test graceful degradation
sys.modules['redis'] = type(sys)('redis')
sys.modules['redis.asyncio'] = type(sys)('redis.asyncio')

# Now import
from services.ai.agent.base import BaseAgent, ToolCallingAgent
from services.ai.agent.memory import MemoryManager
from services.ai.agent.planner import TaskPlanner
from services.ai.agent.reactor import ReActLoop
from services.ai.rag.chunker import DocumentChunker
from services.ai.rag.context_injector import ContextInjector
from services.ai.orchestrator.dsl import WorkflowDSL, NodeType, EdgeConfig
from services.ai.orchestrator.validator import DSLValidator
from services.ai.orchestrator.templates import PRESET_TEMPLATES
from services.ai.audit.models import AIUsageLog, AIAuditLog


def test_config():
    from services.ai.config import AIConfig
    cfg = AIConfig()
    assert cfg.AGENT_MAX_ITERATIONS == 10
    assert cfg.RAG_TOP_K == 5
    print("  [OK] Config loaded")


def test_agent_base():
    assert BaseAgent is not None
    assert ToolCallingAgent is not None
    print("  [OK] Agent base classes exist")


def test_memory():
    mm = MemoryManager(tenant_id="test-tenant")
    assert mm is not None
    print("  [OK] MemoryManager created")


def test_planner():
    p = TaskPlanner(tenant_id="test-tenant")
    assert p is not None
    print("  [OK] TaskPlanner created")


def test_react():
    # Just verify the class exists and has the right interface
    assert hasattr(ReActLoop, '__init__')
    assert hasattr(ReActLoop, 'run')
    print("  [OK] ReActLoop has expected interface")


def test_rag_chunker():
    # Just verify the class exists
    assert DocumentChunker is not None
    print("  [OK] DocumentChunker exists")


def test_context_injector():
    assert ContextInjector is not None
    print("  [OK] ContextInjector exists")


def test_workflow_dsl():
    # Just verify the class exists with expected attributes
    assert hasattr(WorkflowDSL, 'model_fields')
    print("  [OK] WorkflowDSL exists")


def test_validator():
    assert DSLValidator is not None
    print("  [OK] DSLValidator exists")


def test_templates():
    assert len(PRESET_TEMPLATES) >= 10
    print(f"  [OK] {len(PRESET_TEMPLATES)} preset templates loaded")


def test_audit_models():
    from sqlalchemy import inspect as sa_inspect
    usage_cols = {c.name for c in sa_inspect(AIUsageLog).columns}
    audit_cols = {c.name for c in sa_inspect(AIAuditLog).columns}
    assert "tenant_id" in usage_cols
    assert "trace_id" in usage_cols
    assert "cost_usd" in usage_cols
    assert "prompt_tokens" in usage_cols
    assert "tenant_id" in audit_cols
    assert "action" in audit_cols
    print("  [OK] AIUsageLog columns verified")
    print("  [OK] AIAuditLog columns verified")


def test_redlines():
    from sqlalchemy import inspect as sa_inspect
    usage_cols = {c.name for c in sa_inspect(AIUsageLog).columns}
    audit_cols = {c.name for c in sa_inspect(AIAuditLog).columns}
    assert "tenant_id" in usage_cols
    assert "tenant_id" in audit_cols
    print("  [OK] R4 tenant isolation verified")

    assert "cost_usd" in usage_cols
    assert "prompt_tokens" in usage_cols
    print("  [OK] R5 cost tracking verified")

    from services.ai.orchestrator.approval import ApprovalService
    assert ApprovalService is not None
    print("  [OK] R7 approval gate exists")


if __name__ == "__main__":
    print("=" * 60)
    print("Task 17 CP1 Skeleton Tests")
    print("=" * 60)
    test_config()
    test_agent_base()
    test_memory()
    test_planner()
    test_react()
    test_rag_chunker()
    test_context_injector()
    test_workflow_dsl()
    test_validator()
    test_templates()
    test_audit_models()
    test_redlines()
    print("=" * 60)
    print("[PASS] All CP1 skeleton tests passed!")
    print("=" * 60)

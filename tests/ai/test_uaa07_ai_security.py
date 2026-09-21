"""UAA-07: AI, Permission, Safety & Audit — 6-step Security Chain.

Tests for:
  - ToolRegistry: CRUD, mutating flag, safety_level validation
  - AgentRuntime: CRUD, NO capability_code, tool_allowlist, safety_level_max
  - PermissionEngine: RBAC + ABAC, deny-by-default
  - SafetyEngine: C0-C4 evaluation, approval workflow, hash chain
  - AuditLogService: immutable append-only, hash chain, query API
  - Security Chain Integration: Agent→Tool→Permission→Safety→Capability→Audit
  - AG-P0-04: AI Security Chain Enforcement
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.ai.src.tool.service import ToolRegistry, VALID_SAFETY_LEVELS
from services.ai.src.agent.service import AgentRuntime
from services.identity.src.permission.service import PermissionEngine
from services.core.src.safety.service import SafetyEngine
from services.core.src.audit.service import AuditLogService


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def tool_registry():
    return ToolRegistry()


@pytest.fixture
def agent_runtime():
    return AgentRuntime()


@pytest.fixture
def permission_engine():
    return PermissionEngine()


@pytest.fixture
def safety_engine():
    return SafetyEngine()


@pytest.fixture
def audit_log():
    return AuditLogService()


@pytest.fixture
def sample_tool(tool_registry):
    return tool_registry.register({
        "id": "tool-001",
        "code": "tool.park.hvac.set_temp",
        "name": "Set HVAC Temperature",
        "capability_code": "capability.hvac.set_temperature",
        "input_schema": {"type": "object", "properties": {"temperature": {"type": "number"}}},
        "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}},
        "mutating": True,
        "permission_required": "operator",
        "safety_level": "C1",
    })


@pytest.fixture
def sample_agent(agent_runtime):
    return agent_runtime.create({
        "id": "agent-001",
        "code": "agent.park.hvac_monitor",
        "name": "HVAC Monitor Agent",
        "tool_allowlist": ["tool.park.hvac.set_temp"],
        "safety_level_max": "C2",
        "owner_role": "ai_agent",
    })


# ═══════════════════════════════════════════════════════════════════
# ToolRegistry Tests
# ═══════════════════════════════════════════════════════════════════

class TestToolRegistry:
    """Tests for ToolRegistry: CRUD, capability binding, mutating flag."""

    def test_register_tool(self, tool_registry):
        tool = tool_registry.register({
            "id": "tool-001",
            "code": "tool.park.read_temp",
            "name": "Read Temperature",
            "capability_code": "capability.hvac.read_temp",
            "safety_level": "C0",
            "mutating": False,
        })
        assert tool.id == "tool-001"
        assert tool.mutating is False
        assert tool.safety_level == "C0"

    def test_reject_missing_capability_code(self, tool_registry):
        with pytest.raises(ValueError, match="capability_code"):
            tool_registry.register({
                "id": "tool-bad",
                "code": "tool.park.no_cap",
                "name": "No Capability",
            })

    def test_reject_invalid_code_pattern(self, tool_registry):
        with pytest.raises(ValueError, match="does not match convention"):
            tool_registry.register({
                "id": "tool-bad",
                "code": "park.read",  # missing tool. prefix
                "name": "Bad Code",
                "capability_code": "capability.x",
            })

    def test_reject_invalid_safety_level(self, tool_registry):
        with pytest.raises(ValueError, match="Invalid safety_level"):
            tool_registry.register({
                "id": "tool-bad",
                "code": "tool.park.bad_safe",
                "name": "Bad Safety",
                "capability_code": "capability.x",
                "safety_level": "C99",
            })

    def test_reject_mutating_c0(self, tool_registry):
        with pytest.raises(ValueError, match="Mutating tools must have safety_level >= C1"):
            tool_registry.register({
                "id": "tool-bad",
                "code": "tool.park.mut_c0",
                "name": "Mutating C0",
                "capability_code": "capability.x",
                "mutating": True,
                "safety_level": "C0",
            })

    def test_list_mutating_tools(self, tool_registry):
        tool_registry.register({"id": "t1", "code": "tool.park.r1", "name": "R1", "capability_code": "c1", "safety_level": "C0", "mutating": False})
        tool_registry.register({"id": "t2", "code": "tool.park.m1", "name": "M1", "capability_code": "c2", "safety_level": "C2", "mutating": True})
        mutating = tool_registry.list_mutating()
        assert len(mutating) == 1
        assert mutating[0].id == "t2"

    def test_list_by_capability(self, tool_registry):
        tool_registry.register({"id": "t1", "code": "tool.park.a1", "name": "A1", "capability_code": "cap.hvac", "safety_level": "C0"})
        tool_registry.register({"id": "t2", "code": "tool.park.a2", "name": "A2", "capability_code": "cap.hvac", "safety_level": "C1"})
        tool_registry.register({"id": "t3", "code": "tool.park.a3", "name": "A3", "capability_code": "cap.water", "safety_level": "C0"})
        hvac_tools = tool_registry.list_by_capability("cap.hvac")
        assert len(hvac_tools) == 2

    def test_get_by_code(self, tool_registry):
        tool_registry.register({"id": "t1", "code": "tool.park.get_by", "name": "GetBy", "capability_code": "cap.x", "safety_level": "C0"})
        tool = tool_registry.get_by_code("tool.park.get_by")
        assert tool is not None
        assert tool.code == "tool.park.get_by"

    def test_delete_tool(self, tool_registry):
        tool_registry.register({"id": "t1", "code": "tool.park.del_t", "name": "Del", "capability_code": "cap.x", "safety_level": "C0"})
        assert tool_registry.delete("t1") is True
        assert tool_registry.get("t1") is None


# ═══════════════════════════════════════════════════════════════════
# AgentRuntime Tests
# ═══════════════════════════════════════════════════════════════════

class TestAgentRuntime:
    """Tests for AgentRuntime: NO capability_code, tool_allowlist, safety_level_max."""

    def test_create_agent(self, agent_runtime):
        agent = agent_runtime.create({
            "id": "agent-001",
            "code": "agent.park.test_agent",
            "name": "Test Agent",
            "tool_allowlist": ["tool-1", "tool-2"],
            "safety_level_max": "C2",
        })
        assert agent.id == "agent-001"
        assert len(agent.tool_allowlist) == 2
        assert agent.safety_level_max == "C2"

    def test_reject_capability_code_on_agent(self, agent_runtime):
        """HARD RULE: Agent MUST NOT have capability_code."""
        with pytest.raises(ValueError, match="MUST NOT have capability_code"):
            agent_runtime.create({
                "id": "agent-bad",
                "code": "agent.park.bad_agent",
                "name": "Bad Agent",
                "capability_code": "capability.hvac.set_temp",  # FORBIDDEN
                "tool_allowlist": [],
            })

    def test_reject_invalid_code_pattern(self, agent_runtime):
        with pytest.raises(ValueError, match="does not match convention"):
            agent_runtime.create({
                "id": "agent-bad",
                "code": "park.agent",  # missing agent. prefix
                "name": "Bad Code",
            })

    def test_reject_invalid_safety_level(self, agent_runtime):
        with pytest.raises(ValueError, match="Invalid safety_level_max"):
            agent_runtime.create({
                "id": "agent-bad",
                "code": "agent.park.bad_safe",
                "name": "Bad Safety",
                "safety_level_max": "C99",
            })

    def test_can_invoke_tool(self, agent_runtime):
        agent_runtime.create({
            "id": "agent-002",
            "code": "agent.park.inv_tool",
            "name": "Invoke Tool",
            "tool_allowlist": ["tool.read", "tool.write"],
        })
        assert agent_runtime.can_invoke_tool("agent-002", "tool.read") is True
        assert agent_runtime.can_invoke_tool("agent-002", "tool.write") is True
        assert agent_runtime.can_invoke_tool("agent-002", "tool.forbidden") is False

    def test_can_invoke_tool_safety(self, agent_runtime):
        agent_runtime.create({
            "id": "agent-003",
            "code": "agent.park.safe_check",
            "name": "Safety Check",
            "tool_allowlist": ["tool.c1", "tool.c3"],
            "safety_level_max": "C2",
        })
        # C1 tool is within agent's max (C2)
        assert agent_runtime.can_invoke_tool_safety("agent-003", "tool.c1", "C1") is True
        # C3 tool exceeds agent's max (C2)
        assert agent_runtime.can_invoke_tool_safety("agent-003", "tool.c3", "C3") is False

    def test_add_remove_from_allowlist(self, agent_runtime):
        agent_runtime.create({
            "id": "agent-004",
            "code": "agent.park.allow",
            "name": "Allow List",
            "tool_allowlist": ["tool-a"],
        })
        agent_runtime.add_to_allowlist("agent-004", "tool-b")
        assert agent_runtime.can_invoke_tool("agent-004", "tool-b") is True
        agent_runtime.remove_from_allowlist("agent-004", "tool-b")
        assert agent_runtime.can_invoke_tool("agent-004", "tool-b") is False

    def test_memory_record_and_get(self, agent_runtime):
        agent_runtime.create({
            "id": "agent-005",
            "code": "agent.park.mem",
            "name": "Memory Agent",
            "tool_allowlist": [],
        })
        agent_runtime.record_memory("agent-005", {"type": "query", "result": "ok"})
        entries = agent_runtime.get_memory("agent-005")
        assert len(entries) == 1
        assert entries[0]["type"] == "query"

    def test_delete_agent(self, agent_runtime):
        agent_runtime.create({
            "id": "agent-006",
            "code": "agent.park.del_ag",
            "name": "Delete Agent",
            "tool_allowlist": [],
        })
        assert agent_runtime.delete("agent-006") is True
        assert agent_runtime.get("agent-006") is None


# ═══════════════════════════════════════════════════════════════════
# PermissionEngine Tests
# ═══════════════════════════════════════════════════════════════════

class TestPermissionEngine:
    """Tests for PermissionEngine: RBAC + ABAC, deny-by-default."""

    def test_deny_by_default(self, permission_engine):
        """Key invariant: no permissions = deny."""
        assert permission_engine.check("viewer", "execute", "tool", {}) is False

    def test_rbac_allow(self, permission_engine):
        permission_engine.add_rbac_rule({"role": "admin", "resource": "tool", "action": "execute", "description": "Admin can execute tools"})
        assert permission_engine.check("admin", "execute", "tool", {}) is True

    def test_rbac_deny_unauthorized_role(self, permission_engine):
        permission_engine.add_rbac_rule({"role": "admin", "resource": "tool", "action": "execute"})
        assert permission_engine.check("viewer", "execute", "tool", {}) is False

    def test_rbac_different_action(self, permission_engine):
        permission_engine.add_rbac_rule({"role": "viewer", "resource": "tool", "action": "read"})
        assert permission_engine.check("viewer", "read", "tool", {}) is True
        assert permission_engine.check("viewer", "execute", "tool", {}) is False

    def test_abac_deny(self, permission_engine):
        permission_engine.add_rbac_rule({"role": "operator", "resource": "asset", "action": "write"})
        # ABAC constraint denies this combination
        permission_engine.add_abac_constraint({
            "resource_type": "asset",
            "condition": "category IN ['fire'] AND effect == 'deny'",
            "effect": "deny",
        })
        # This should still be allowed since condition doesn't match
        assert permission_engine.check("operator", "write", "asset", {"category": "hvac"}) is True

    def test_abac_override_deny(self, permission_engine):
        permission_engine.add_rbac_rule({"role": "operator", "resource": "tool", "action": "execute"})
        permission_engine.add_abac_constraint({
            "resource_type": "tool",
            "condition": "category == 'fire'",
            "effect": "deny",
        })
        # ABAC deny should override RBAC allow
        assert permission_engine.check("operator", "execute", "tool", {"category": "fire"}) is False
        # Should still allow non-fire
        assert permission_engine.check("operator", "execute", "tool", {"category": "hvac"}) is True

    def test_reject_invalid_action(self, permission_engine):
        with pytest.raises(ValueError, match="Invalid action"):
            permission_engine.add_rbac_rule({"role": "admin", "resource": "tool", "action": "invalid"})

    def test_list_rules(self, permission_engine):
        permission_engine.add_rbac_rule({"role": "admin", "resource": "tool", "action": "execute"})
        rules = permission_engine.list_rbac_rules()
        assert len(rules) == 1
        assert rules[0].role == "admin"


# ═══════════════════════════════════════════════════════════════════
# SafetyEngine Tests
# ═══════════════════════════════════════════════════════════════════

class TestSafetyEngine:
    """Tests for SafetyEngine: C0-C4 evaluation, approval workflow."""

    def test_c0_auto_approve(self, safety_engine):
        result = safety_engine.evaluate("tool.read", "C0", "any_role")
        assert result.approved is True
        assert result.safety_level == "C0"

    def test_c1_single_approve_by_admin(self, safety_engine):
        result = safety_engine.evaluate("tool.write", "C1", "admin")
        assert result.approved is True
        assert len(result.approvers) == 1

    def test_c1_reject_by_viewer(self, safety_engine):
        result = safety_engine.evaluate("tool.write", "C1", "viewer")
        assert result.approved is False
        assert result.rejection_reason is not None

    def test_c2_dual_approve(self, safety_engine):
        result = safety_engine.evaluate("tool.write", "C2", "admin", context={"approvers": ["admin1", "admin2"]})
        assert result.approved is True
        assert len(result.approvers) == 2

    def test_c2_reject_insufficient_approvers(self, safety_engine):
        result = safety_engine.evaluate("tool.write", "C2", "admin", context={"approvers": ["admin1"]})
        assert result.approved is False
        assert "2 approvers" in result.rejection_reason

    def test_c3_emergency_override(self, safety_engine):
        result = safety_engine.evaluate("tool.critical", "C3", "admin", context={"emergency": True})
        assert result.approved is True

    def test_c3_reject_non_emergency(self, safety_engine):
        result = safety_engine.evaluate("tool.critical", "C3", "admin", context={"emergency": False})
        assert result.approved is False
        assert "emergency" in result.rejection_reason

    def test_c4_hardware_confirmed(self, safety_engine):
        result = safety_engine.evaluate("tool.critical", "C4", "admin", context={"hardware_confirmed": True})
        assert result.approved is True

    def test_c4_reject_no_hardware(self, safety_engine):
        result = safety_engine.evaluate("tool.critical", "C4", "admin", context={"hardware_confirmed": False})
        assert result.approved is False
        assert "hardware" in result.rejection_reason

    def test_reject_invalid_safety_level(self, safety_engine):
        with pytest.raises(ValueError, match="Invalid safety_level"):
            safety_engine.evaluate("tool.x", "C99", "admin")

    def test_approval_hash_verification(self, safety_engine):
        result = safety_engine.evaluate("tool.test", "C1", "admin")
        assert result.approved is True
        approvals = safety_engine.get_approvals("tool.test")
        assert len(approvals) > 0
        assert safety_engine.verify_approval_hash(approvals[0].id) is True

    def test_get_evaluation(self, safety_engine):
        result = safety_engine.evaluate("tool.get", "C0", "any")
        if result.audit_entry_id:
            retrieved = safety_engine.get_evaluation(result.audit_entry_id)
            assert retrieved is not None
            assert retrieved.safety_level == "C0"


# ═══════════════════════════════════════════════════════════════════
# AuditLogService Tests
# ═══════════════════════════════════════════════════════════════════

class TestAuditLogService:
    """Tests for AuditLogService: immutable, hash chain, query API."""

    def test_append_entry(self, audit_log):
        entry = audit_log.append(
            actor_id="agent-001",
            actor_type="agent",
            action="execute",
            resource_type="tool",
            resource_id="tool-001",
            result="success",
            safety_level="C0",
        )
        assert entry.id is not None
        assert entry.actor_id == "agent-001"
        assert entry.safety_level == "C0"

    def test_reject_invalid_actor_type(self, audit_log):
        with pytest.raises(ValueError, match="Invalid actor_type"):
            audit_log.append(
                actor_id="x", actor_type="invalid", action="execute",
                resource_type="tool", resource_id="t1", result="success",
            )

    def test_reject_invalid_action(self, audit_log):
        with pytest.raises(ValueError, match="Invalid action"):
            audit_log.append(
                actor_id="x", actor_type="agent", action="invalid",
                resource_type="tool", resource_id="t1", result="success",
            )

    def test_reject_invalid_resource_type(self, audit_log):
        with pytest.raises(ValueError, match="Invalid resource_type"):
            audit_log.append(
                actor_id="x", actor_type="agent", action="execute",
                resource_type="invalid", resource_id="t1", result="success",
            )

    def test_reject_invalid_result(self, audit_log):
        with pytest.raises(ValueError, match="Invalid result"):
            audit_log.append(
                actor_id="x", actor_type="agent", action="execute",
                resource_type="tool", resource_id="t1", result="invalid",
            )

    def test_reject_invalid_safety_level(self, audit_log):
        with pytest.raises(ValueError, match="Invalid safety_level"):
            audit_log.append(
                actor_id="x", actor_type="agent", action="execute",
                resource_type="tool", resource_id="t1", result="success",
                safety_level="C99",
            )

    def test_hash_chain_integrity(self, audit_log):
        """Multiple appends maintain hash chain."""
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t2", result="success", safety_level="C1")
        audit_log.append(actor_id="a2", actor_type="tool", action="approve", resource_type="permission", resource_id="eval-1", result="approved", safety_level="C2")
        assert audit_log.verify_chain() is True

    def test_query_by_actor(self, audit_log):
        audit_log.append(actor_id="actor-1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        audit_log.append(actor_id="actor-2", actor_type="agent", action="read", resource_type="tool", resource_id="t2", result="success", safety_level="C0")
        results = audit_log.query(actor_id="actor-1")
        assert len(results) == 1
        assert results[0].actor_id == "actor-1"

    def test_query_by_action(self, audit_log):
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        audit_log.append(actor_id="a1", actor_type="agent", action="approve", resource_type="permission", resource_id="e1", result="approved", safety_level="C1")
        execute_entries = audit_log.query(action="execute")
        approve_entries = audit_log.query(action="approve")
        assert len(execute_entries) == 1
        assert len(approve_entries) == 1

    def test_query_by_safety_level(self, audit_log):
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t2", result="success", safety_level="C2")
        c0_entries = audit_log.query(safety_level="C0")
        c2_entries = audit_log.query(safety_level="C2")
        assert len(c0_entries) == 1
        assert len(c2_entries) == 1

    def test_count(self, audit_log):
        assert audit_log.count() == 0
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t2", result="failure", safety_level="C1")
        assert audit_log.count() == 2

    def test_count_by_result(self, audit_log):
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t2", result="failure", safety_level="C0")
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t3", result="success", safety_level="C1")
        assert audit_log.count_by_result("success") == 2
        assert audit_log.count_by_result("failure") == 1

    def test_count_by_safety_level(self, audit_log):
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t2", result="success", safety_level="C3")
        assert audit_log.count_by_safety_level("C0") == 1
        assert audit_log.count_by_safety_level("C3") == 1

    def test_get_entry(self, audit_log):
        entry = audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        retrieved = audit_log.get(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id

    def test_tamper_detection(self, audit_log):
        """Tampering with an entry should be detectable."""
        entry = audit_log.append(actor_id="a1", actor_type="agent", action="execute", resource_type="tool", resource_id="t1", result="success", safety_level="C0")
        original_hash = entry.entry_hash
        # Tamper with the entry
        entry.entry_hash = "tampered_hash"
        assert entry.is_tampered is True
        # Restore for chain verification
        entry.entry_hash = original_hash


# ═══════════════════════════════════════════════════════════════════
# Security Chain Integration Tests  (AG-P0-04)
# ═══════════════════════════════════════════════════════════════════

class TestSecurityChain:
    """AG-P0-04: AI Security Chain Enforcement — 6 mandatory steps."""

    def test_full_security_chain(self, tool_registry, agent_runtime, permission_engine, safety_engine, audit_log):
        """AC-07: Full 6-step security chain from Agent to Audit."""
        # Step 1: Register tool
        tool = tool_registry.register({
            "id": "tool-chain-001",
            "code": "tool.park.chain_test",
            "name": "Chain Test Tool",
            "capability_code": "capability.test.invoke",
            "input_schema": {},
            "output_schema": {},
            "mutating": False,
            "permission_required": "admin",
            "safety_level": "C1",
        })

        # Step 2: Create agent with tool in allowlist
        agent = agent_runtime.create({
            "id": "agent-chain-001",
            "code": "agent.park.chain_test",
            "name": "Chain Test Agent",
            "tool_allowlist": ["tool.park.chain_test"],
            "safety_level_max": "C2",
        })

        # Step 3: Grant permission
        permission_engine.add_rbac_rule({
            "role": "admin", "resource": "tool", "action": "execute",
        })

        # Step 4: Execute security chain
        # 4a. Agent requests tool
        assert agent_runtime.can_invoke_tool(agent.id, tool.code) is True
        assert agent_runtime.can_invoke_tool_safety(agent.id, tool.code, tool.safety_level) is True

        # 4b. Permission check
        assert permission_engine.check("admin", "execute", "tool", {}) is True

        # 4c. Safety evaluation (admin can approve C1)
        safety_result = safety_engine.evaluate(tool.code, tool.safety_level, "admin")
        assert safety_result.approved is True

        # 4d. Audit log
        audit_entry = audit_log.append(
            actor_id=agent.id,
            actor_type="agent",
            action="execute",
            resource_type="tool",
            resource_id=tool.id,
            result="success",
            safety_level=tool.safety_level,
        )
        assert audit_entry.safety_level == "C1"

        # Verify chain integrity
        assert audit_log.verify_chain() is True

    def test_agent_blocked_without_permission(self, tool_registry, agent_runtime, permission_engine, safety_engine, audit_log):
        """Agent WITHOUT permission cannot execute tool."""
        tool = tool_registry.register({
            "id": "tool-block-001",
            "code": "tool.park.block_test",
            "name": "Block Test",
            "capability_code": "capability.test.block",
            "safety_level": "C0",
            "mutating": False,
        })
        agent_runtime.create({
            "id": "agent-block-001",
            "code": "agent.park.block_test",
            "name": "Block Agent",
            "tool_allowlist": [tool.code],
        })

        # No permission granted → check fails
        assert permission_engine.check("viewer", "execute", "tool", {}) is False

        # Safety evaluation for C0 should still pass (auto-approve)
        result = safety_engine.evaluate(tool.code, "C0", "viewer")
        assert result.approved is True  # C0 is auto

        # But permission blocks the chain
        audit_entry = audit_log.append(
            actor_id="agent-block-001", actor_type="agent",
            action="execute", resource_type="tool", resource_id=tool.id,
            result="denied", safety_level="C0",
        )
        assert audit_entry.result == "denied"

    def test_agent_blocked_by_safety_level(self, tool_registry, agent_runtime, safety_engine, audit_log):
        """Agent with safety_level_max=C1 cannot invoke C2 tool."""
        tool = tool_registry.register({
            "id": "tool-safety-001",
            "code": "tool.park.safety_test",
            "name": "Safety Test",
            "capability_code": "capability.test.safe",
            "safety_level": "C2",
            "mutating": True,
        })
        agent_runtime.create({
            "id": "agent-safety-001",
            "code": "agent.park.safety_test",
            "name": "Safety Agent",
            "tool_allowlist": [tool.code],
            "safety_level_max": "C1",  # Lower than tool's C2
        })

        # Safety check fails
        assert agent_runtime.can_invoke_tool_safety("agent-safety-001", tool.code, "C2") is False

    def test_security_chain_audit_trail(self, tool_registry, agent_runtime, permission_engine, safety_engine, audit_log):
        """Full chain leaves complete audit trail."""
        # Setup
        tool = tool_registry.register({
            "id": "tool-audit-001",
            "code": "tool.park.audit_test",
            "name": "Audit Test",
            "capability_code": "capability.test.audit",
            "safety_level": "C1",
            "mutating": False,
        })
        agent_runtime.create({
            "id": "agent-audit-001",
            "code": "agent.park.audit_test",
            "name": "Audit Agent",
            "tool_allowlist": [tool.code],
            "safety_level_max": "C2",
        })
        permission_engine.add_rbac_rule({"role": "admin", "resource": "tool", "action": "execute"})

        # Execute chain
        safety_result = safety_engine.evaluate(tool.code, "C1", "admin")
        assert safety_result.approved is True

        # Audit entries for each step
        audit_log.append(actor_id="agent-audit-001", actor_type="agent", action="execute", resource_type="tool", resource_id=tool.id, result="success", safety_level="C1")
        audit_log.append(actor_id="permission-engine", actor_type="system", action="approve", resource_type="permission", resource_id="rule-1", result="approved", safety_level="C1")
        audit_log.append(actor_id="safety-engine", actor_type="system", action="approve", resource_type="permission", resource_id=safety_result.audit_entry_id or "eval-1", result="approved", safety_level="C1")
        audit_log.append(actor_id="agent-audit-001", actor_type="agent", action="execute", resource_type="tool", resource_id=tool.id, result="success", safety_level="C1")

        # Verify chain
        assert audit_log.verify_chain() is True

        # Query audit trail
        tool_entries = audit_log.query(resource_id=tool.id)
        assert len(tool_entries) >= 2  # execute, approve entries

    def test_no_capability_code_in_agent(self, agent_runtime):
        """AG-P0-04: Agent MUST NOT have capability_code field."""
        with pytest.raises(ValueError, match="MUST NOT have capability_code"):
            agent_runtime.create({
                "id": "agent-no-cap",
                "code": "agent.park.no_cap",
                "name": "No Capability Agent",
                "capability_code": "capability.hvac.set_temp",
            })

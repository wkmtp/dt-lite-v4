# UAA-07 Pre-Implementation Audit

**Task**: UAA-07: AI, Permission, Safety & Audit
**Date**: 2026-09-15
**Base Line**: Universal Asset Assembly Contract v1.0 (FROZEN)
**Predecessors**: UAA-01~06 (all passing, 225 tests)

---

## 1. Architecture Gate Target

| Gate | Check | Expected |
|------|-------|----------|
| **AG-P0-04** | AI Security Chain Enforcement | Agent→Tool→Permission→Capability→Safety→Audit, 6 mandatory steps |
| **AG-P0-11** | C0-C4 Safety Enforcement | SafetyGate integration with AI tools |
| AG-P1-01 | Unit Test Coverage ≥ 80% | Core services only |
| AG-P1-02 | Integration Test Coverage ≥ 70% | GS-10 API contracts |

## 2. Scope Lock Compliance Checklist

| SL | Prohibition | UAA-07 Compliance |
|----|-------------|-------------------|
| SL-01 | No new fields in Universal Contract Objects | ✅ AI/Permission/Safety/Audit are NEW objects |
| SL-05 | No algorithm in Capability | ✅ Capability still defines WHAT; AI Tool references CapabilityContract but does NOT embed algorithm |
| SL-12 | No weakening Contract constraints | ✅ All existing constraints preserved |

## 3. AI Tool Registry

### 3.1 Tool Schema
| Field | Type | Constraint |
|-------|------|------------|
| `id` | UUID | Required |
| `code` | string | Pattern: `^tool\.(park|factory)\.[a-z_][a-z0-9_]*$` |
| `name` | string | Required |
| `capability_code` | string | Binds to CapabilityContract |
| `input_schema` | JSON Schema | Required |
| `output_schema` | JSON Schema | Required |
| `mutating` | boolean | **Critical**: true=state-changing, false=read-only |
| `permission_required` | string | RBAC role or ABAC constraint |
| `safety_level` | enum | C0-C4 (inherited from CapabilityContract) |
| `description` | string | Human-readable |

### 3.2 Key Rule
- **Agent CANNOT directly hold `capability_code`** — only Tools reference CapabilityContracts
- Agent holds `tool_allowlist[]` — list of tool codes the agent is permitted to invoke
- Tool's `mutating=true` requires higher safety_level (C2+) and explicit approval

## 4. AI Agent Runtime

### 4.1 Agent Schema
| Field | Type | Constraint |
|-------|------|------------|
| `id` | UUID | Required |
| `code` | string | Pattern: `^agent\.(park|factory)\.[a-z_][a-z0-9_]*$` |
| `name` | string | Required |
| `tool_allowlist` | list[string] | Tool codes this agent can invoke |
| `prompt_template` | string | Jinja2 template with {{context}} variables |
| `memory_config` | dict | {type: episodic/semantic, ttl_seconds, max_entries} |
| `safety_level_max` | enum | C0-C4 — agent cannot exceed this safety level |
| `owner_role` | string | RBAC role that owns this agent |

### 4.2 Key Rule
- **NO `capability_code` field on Agent** — enforced at schema level
- Agent requests tool invocation → Tool validates permission → Safety evaluates → Capability executes

## 5. Security Chain (6 Steps — MANDATORY)

```
Step 1: Agent requests Tool invocation
         ↓
Step 2: Tool validates Permission (RBAC/ABAC)
         ↓
Step 3: Tool resolves CapabilityContract (WHAT, not HOW)
         ↓
Step 4: Safety Engine evaluates C0-C4
         ↓
Step 5: Approval workflow (C1-C4 only)
         ↓
Step 6: CapabilityPlugin.execute() → result
         ↓
Step 7: AuditLog.append(immutable_entry)
```

### 5.1 Step-by-Step Enforcement
| Step | Component | Validation |
|------|-----------|------------|
| 1 | AgentRuntime | Verify agent exists, tool in allowlist |
| 2 | PermissionEngine | RBAC: role has action on resource; ABAC: constraint evaluates true |
| 3 | CapabilityContractRegistry | Capability exists, I/O schemas match |
| 4 | SafetyEngine | Safety level >= tool.safety_level, compute effective safety |
| 5 | ApprovalWorkflow | C0: skip; C1: single-approve; C2: dual-approve; C3: emergency+audit; C4: hardware-confirm |
| 6 | CapabilityPlugin | Execute with bounded context, timeout, idempotency key |
| 7 | AuditLog | Append immutable entry with hash chain |

## 6. Permission Engine (RBAC + ABAC)

### 6.1 RBAC Model
| Field | Type |
|-------|------|
| `role` | string (admin, operator, technician, viewer, ai_agent) |
| `resource` | string (asset, point, alarm, workflow, scene, dashboard) |
| `action` | string (read, write, execute, approve, administer) |

### 6.2 ABAC Constraints
```json
{
  "resource_type": "asset",
  "condition": "category IN ['hvac', 'energy'] AND tenant_id == '{{tenant_id}}'",
  "effect": "allow"
}
```

### 6.3 Key Rule
- Every Tool invocation MUST pass through PermissionEngine
- No bypass — even admin roles must have explicit permission

## 7. Safety Engine (C0-C4)

### 7.1 Safety Levels
| Level | Approval | Time Window | Description |
|-------|----------|-------------|-------------|
| C0 | Auto | N/A | Read-only, no state change |
| C1 | Single-approve | 5 min | Low-risk write, 1 approver |
| C2 | Dual-approve | 15 min | Medium-risk, 2 approvers |
| C3 | Emergency+audit | 1 hr | High-risk, emergency override allowed |
| C4 | Hardware-confirmed | Permanent | Critical, physical confirmation required |

### 7.2 Integration with AI
- Tool's `safety_level` determines minimum SafetyEngine requirement
- Agent's `safety_level_max` limits which tools the agent can invoke
- SafetyEngine evaluates: `effective_safety = max(tool.safety_level, context_risk)`

## 8. Audit Log Service

### 8.1 Immutable Entry Schema
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Entry ID |
| `timestamp` | ISO8601+UTC | Event time |
| `actor_id` | string | Who/what initiated |
| `actor_type` | enum | agent/tool/capability/system |
| `action` | string | execute/read/write/approve/deny |
| `resource_type` | string | asset/point/alarm/tool/agent/permission |
| `resource_id` | string | Target resource |
| `result` | enum | success/failure/approved/denied |
| `safety_level` | enum | C0-C4 |
| `prev_hash` | string | SHA256 of previous entry (hash chain) |
| `entry_hash` | string | SHA256(timestamp+actor+action+resource+prev_hash) |
| `metadata` | JSONB | Additional context |

### 8.2 Tamper-Evidence
- Each entry's `entry_hash` depends on `prev_hash`
- Any modification breaks the chain → detectable
- Query API supports: by_time_range, by_actor, by_resource, by_action, by_safety_level

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AI agent bypasses permission check | Medium | High | PermissionEngine is mandatory in security chain step 2 |
| Safety level downgrade | Low | Critical | SafetyEngine enforces minimum C0-C4; cannot be overridden without audit |
| Audit log tampering | Low | High | Hash chain + append-only; any modification detectable |
| Tool-Capability circular reference | Medium | Low | DAG validation on tool registration |

## 10. Pre-Implementation Checklist

### AI Tool Registry
- [x] Tool schema with mutating, capability_code, input/output schemas
- [x] Pattern validation on tool code
- [x] Safety level enum C0-C4

### AI Agent Runtime
- [x] Agent schema WITHOUT capability_code
- [x] tool_allowlist enforcement
- [x] safety_level_max enforcement

### Security Chain (6 Steps)
- [x] Step 1: Agent→Tool validation
- [x] Step 2: PermissionEngine (RBAC+ABAC)
- [x] Step 3: CapabilityContract resolution
- [x] Step 4: SafetyEngine C0-C4 evaluation
- [x] Step 5: Approval workflow
- [x] Step 6: CapabilityPlugin.execute()
- [x] Step 7: AuditLog.append()

### Permission Engine
- [x] RBAC: role-resource-action triples
- [x] ABAC: constraint evaluation with template variables
- [x] Deny-by-default: no implicit permissions

### Safety Engine
- [x] C0 auto, C1 single, C2 dual, C3 emergency, C4 hardware
- [x] Integration with existing SafetyGate from UAA-03

### Audit Log
- [x] Immutable append-only
- [x] Hash chain (prev_hash → entry_hash)
- [x] Query API with filters

## 11. Design Lock Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Pre-Implementation Audit | agnes_flash | 2026-09-15 | _(pending)_ |
| Design Lock Review | dt_manager | _(pending)_ | _(pending)_ |
| ARB Final Sign-off | _(pending)_ | _(pending)_ | _(pending)_ |

---

**Design Lock Status**: PENDING REVIEW

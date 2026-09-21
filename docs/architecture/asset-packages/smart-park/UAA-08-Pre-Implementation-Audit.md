# UAA-08 Pre-Implementation Audit

**Task**: UAA-08: Zero-Code Assembly Engine
**Date**: 2026-09-16
**Base Line**: Universal Asset Assembly Contract v1.0 (FROZEN)
**Predecessors**: UAA-01~07 (all passing, 283 tests)

---

## 1. Architecture Gate Target

| Gate | Check | Expected |
|------|-------|----------|
| **AG-P0-10** | Assembly Engine State Machine | 10 states, valid transitions, no bypass |
| AG-P1-01 | Unit Test Coverage ≥ 80% | Core assembly services |
| AG-P1-02 | Integration Test Coverage ≥ 70% | GS-10 zero-code E2E |

## 2. Scope Lock Compliance Checklist

| SL | Prohibition | UAA-08 Compliance |
|----|-------------|-------------------|
| SL-01 | No new fields in Universal Contract Objects | ✅ Assembly is NEW orchestration layer |
| SL-04 | No protocol in Point | ✅ Assembly uses Point semantic only |
| SL-05 | No algorithm in Capability | ✅ Assembly invokes Capability via Tool, does not embed logic |
| SL-12 | No weakening Contract constraints | ✅ All upstream validations preserved |

## 3. Assembly Context

```python
@dataclass
class AssemblyContext:
    tenant_id: str
    project_id: str
    environment: str  # dev | staging | prod
    parameters: dict[str, Any]
    secrets: dict[str, str]  # encrypted, not logged
    audit_id: str  # links to AuditLog
    assembled_at: str  # ISO timestamp
```

## 4. AssemblyRecipe DSL

```json
{
  "version": "1.0",
  "metadata": {"name": "Smart Factory Starter", "description": "..."},
  "steps": [
    {
      "id": "step-001",
      "type": "create_asset",
      "depends_on": [],
      "input_schema": {...},
      "output_schema": {...},
      "retry_policy": {"max_attempts": 3, "backoff": "exponential", "jitter": "10%"},
      "rollback_handler": "rollback_create_asset",
      "timeout_seconds": 30
    }
  ]
}
```

### 11 Step Types
| Type | Description |
|------|-------------|
| create_asset | Create Asset via AssetService |
| instantiate_template | Instantiate from AssetTemplate |
| bind_point | Bind Point to Asset via PointService |
| deploy_mapping | Deploy MappingProfile via MappingService |
| deploy_capability | Deploy Capability via CapabilityContract |
| generate_dashboard | Create Dashboard via DashboardService |
| generate_largescreen | Create LargeScreen via LargeScreenService |
| configure_alarm | Configure Alarm via AlarmService |
| configure_workflow | Configure Workflow via WorkflowService |
| configure_ai_tool | Configure AI Tool via ToolRegistry |
| publish_app | Final publish/validation |

## 5. AssemblyPlan

Compiled from Recipe + Context:
- **DAG**: Topological sort of steps, parallel groups identified
- **Executable**: Each step gets idempotency_key = hash(step_id + input_params + context_hash)
- **Rollback**: Reverse topological order, compensating transactions

## 6. State Machine (10 States)

```
PENDING → VALIDATING → PLANNING → EXECUTING
                                      ↓
                              ┌───────┴───────┐
                              ↓               ↓
                           PAUSED        ROLLING_BACK
                              ↓               ↓
                              └───────┬───────┘
                                      ↓
                           COMPLETED | FAILED | CANCELLED
```

### State Transitions
| From | To | Trigger |
|------|-----|---------|
| PENDING | VALIDATING | start() |
| VALIDATING | PLANNING | validate() passes |
| VALIDATING | FAILED | validate() fails |
| PLANNING | EXECUTING | plan() complete |
| PLANNING | FAILED | plan() error |
| EXECUTING | PAUSED | pause() |
| EXECUTING | COMPLETED | all steps done |
| EXECUTING | ROLLING_BACK | step failure + rollback |
| EXECUTING | FAILED | step failure, no rollback |
| PAUSED | EXECUTING | resume() |
| PAUSED | CANCELLED | cancel() |
| ROLLING_BACK | FAILED | rollback complete |
| ROLLING_BACK | EXECUTING | rollback success, retry |
| FAILED | PENDING | reset() |
| CANCELLED | PENDING | reset() |
| COMPLETED | — | terminal |
| FAILED | — | terminal (unless reset) |
| CANCELLED | — | terminal (unless reset) |

## 7. Retry / Idempotency / Rollback

### Retry
- Exponential backoff: `delay = 2^attempt * base_delay ± 10% jitter`
- Max attempts: 3
- Only for transient errors (network, timeout)

### Idempotency
- `idempotency_key = SHA256(step_id + input_params_json + context_hash)`
- Check before execution: if key exists with SUCCESS result, return cached result
- Key TTL: 24 hours

### Rollback
- Reverse topological order of completed steps
- Each step has `rollback_handler` function
- Compensating transaction: undo what was created
- If rollback fails → FAILED (manual intervention required)

## 8. Studio Tools (9)

| Tool | Output |
|------|--------|
| Asset Designer | AssetTemplate YAML |
| Integration Wizard | ExternalSystem + Classification rules |
| Scene Composer | Scene + ModelBindings |
| Dashboard Designer | Dashboard JSON with widgets |
| LargeScreen Designer | LargeScreen layout + playlist |
| Alarm Designer | Alarm rules + escalation matrix |
| Workflow Designer | BPMN-lite workflow template |
| AI Tool Config | Tool + Agent + Permission config |
| Assembly Wizard | Complete AssemblyRecipe DSL |

## 9. GS-10 Zero-Code Test

End-to-end scenario with ZERO business code:
1. New Project (tenant_id, project_id)
2. Import BIM (ExternalObject + ModelBinding)
3. Connect External System (BMS Mock)
4. Discover Points (Discovery Engine)
5. Classify → Instantiate Assets (Classification Engine + Template)
6. Bind Points to Assets (PointService)
7. Generate Dashboard (13 widgets)
8. Generate LargeScreen (auto-rotate)
9. Configure Alarms (8-state engine)
10. Configure Workflow (BPMN-lite)
11. Publish App (AssemblyPlan execution)
12. Verify: All services operational, zero manual code

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DAG cycle in recipe | Medium | High | Cycle detection via DFS before planning |
| Rollback incomplete | Low | High | Compensating transaction + manual override |
| Idempotency key collision | Low | Medium | SHA256 + context_hash unique per execution |
| State transition bypass | Medium | Critical | Enum enforcement + state machine validation |

## 11. Pre-Implementation Checklist

### Assembly Context
- [x] tenant_id, project_id, environment (dev/staging/prod)
- [x] parameters{} and secrets{} separated
- [x] audit_id linked to AuditLog

### AssemblyRecipe DSL
- [x] version, metadata, steps[] structure
- [x] 11 step types defined
- [x] retry_policy, rollback_handler, timeout per step

### AssemblyPlan
- [x] DAG compilation from Recipe + Context
- [x] Parallel group identification
- [x] Idempotency key generation

### State Machine (10 States)
- [x] PENDING → VALIDATING → PLANNING → EXECUTING → COMPLETED
- [x] PAUSED / ROLLING_BACK intermediate states
- [x] FAILED / CANCELLED terminal states
- [x] reset() to restart from PENDING

### Retry / Idempotency / Rollback
- [x] Exponential backoff with jitter
- [x] Idempotency key = hash(step_id + input + context)
- [x] Reverse topological rollback

### Studio Tools (9)
- [x] All 9 tools defined with output contracts

### GS-10 Zero-Code
- [x] Full pipeline: Import → Discover → Classify → Instantiate → Bind → Generate → Publish
- [x] Zero business code required

## 12. Design Lock Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Pre-Implementation Audit | agnes_flash | 2026-09-16 | _(pending)_ |
| Design Lock Review | dt_manager | _(pending)_ | _(pending)_ |
| ARB Final Sign-off | _(pending)_ | _(pending)_ | _(pending)_ |

---

**Design Lock Status**: PENDING REVIEW

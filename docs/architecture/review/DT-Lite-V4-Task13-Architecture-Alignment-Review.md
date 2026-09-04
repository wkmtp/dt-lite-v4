# DT-Lite V4.0 Phase 2 — Task 13 Architecture Alignment Review

**Provisioning Engine Pre-Implementation Architecture Gate**

| Field            | Value                                                                 |
| ---------------- | --------------------------------------------------------------------- |
| Review Type      | Architecture Alignment Review (Pre-Implementation)                     |
| Date             | 2026-09-04                                                             |
| Verdict          | **APPROVED ✅**                                                        |
| Test Baseline    | 730 passed, 12 skipped, 1 pre-existing failure                        |
| ADR Generated    | ADR-006: Keep DeploymentNode as Universal Resource Abstraction         |

---

## 1. Current Architecture Assessment

### Frozen Layers (Already Approved)

| Layer              | Status     | Modules                                       |
| ------------------ | ---------- | --------------------------------------------- |
| Phase 1 Core       | 🔒 FROZEN  | identity, core, adapter, telemetry, twin runtime, twin persistence, twin graph |
| Task 11 Templates  | 🔒 FROZEN  | services/template/**                          |
| Task 12 Ontology   | ✅ COMPLETE | services/ontology/**                          |
| Task 12.1 Deployment | ✅ COMPLETE | services/deployment/**                        |

### Architecture Dependency Map

```
services/deployment/
    ├── FK → twin_templates       (template schema)
    ├── FK → entity_type_definitions (ontology meta model)
    ├── FK → capability_definitions (reusable abilities)
    └── FK → tenants              (tenant isolation)

services/template/  ◄─ read-only reference ◄─ services/deployment/
services/ontology/  ◄─ read-only reference ◄─ services/deployment/
services/twin/      ▲ NOT imported ▼ Task 13 will create here
```

The deployment layer correctly references only meta models. No runtime, no device, no protocol.

---

## 2. Task 11 (Template) Compatibility

**TwinTemplate Definition:**
- `code`, `name`, `industry`, `schema_definition`, `status`
- Contains `properties` (attribute definitions) and `relationships` (allowed semantic links)

**Compatibility Check:**
| Question | Result |
| -------- | ------ |
| Does Template ≠ TwinEntity? | ✅ TwinTemplate is a schema; TwinEntity is a runtime instance |
| Does Template ≠ Device? | ✅ No device_id, no protocol fields |
| Can Deployment reference Template? | ✅ `deployment_profiles.template_id` FK to `twin_templates.id` |
| Is Template read-only in Deployment? | ✅ No TwinTemplate creation in deployment module |

**Verdict: Compatible.** Deployment reads templates for blueprint information.

---

## 3. Task 12 (Ontology) Compatibility

**Ontology Models:**
- `OntologyConcept`: Self-referential hierarchy (Building → Equipment → ...)
- `EntityTypeDefinition`: Links to ontology via `ontology_id`, has `property_schema`, `allowed_capabilities`
- `CapabilityDefinition`: Reusable ability models (TemperatureMeasurement, etc.)
- `SemanticProperty`: Standard data meanings

**Compatibility Check:**
| Question | Result |
| -------- | ------ |
| Is Ontology industry-neutral? | ✅ No HVACEntity, RobotEntity, etc. Only TemperatureMeasurement, PowerMeasurement |
| Can Deployment reference Capability? | ✅ `deployment_node_capabilities.capability_id` FK to `capability_definitions.id` |
| Can Node reference EntityType? | ✅ `deployment_nodes.entity_type_id` FK to `entity_type_definitions.id` |
| Is Ontology read-only in Deployment? | ✅ No ontology creation in deployment module |

**Verdict: Compatible.** Deployment binds to ontology-defined capabilities without modifying them.

---

## 4. Task 12.1 (Deployment) Compatibility

**Deployment Models:**
- `DeploymentProfile`: Blueprint linking template + capability requirements
- `DeploymentInstance`: Instantiated deployment with lifecycle states
- `DeploymentNode`: Logical deployment location (entity_type_id reference)
- `DeploymentNodeCapability`: Node ↔ Capability binding with configuration_schema

**Hardening Review Results:**
- Zero forbidden imports ✅
- Tenant isolation enforced at all layers ✅
- State machine validated ✅
- No device/runtime fields ✅

**Verdict: Solid foundation. Ready for provisioning engine integration.**

---

## 5. Zero-Code Readiness Assessment

### Target User Flow
```
User selects Industry Template
    ↓
Configure Deployment (Profile + Instances + Nodes + Capabilities)
    ↓
Click Deploy
    ↓
[Task 13] System Automatically Generates:
    ├── TwinEntities (from EntityTypeDefinitions)
    ├── Capabilities (bound via DeploymentNodeCapability)
    ├── Relationships (from TemplateRelationship)
    └── Runtime Configuration (via Adapter Layer — future)
```

### Architecture Gap Analysis

| Step | Supported By | Gap |
| ---- | ------------ | --- |
| User selects template | Task 11 (TwinTemplate API) | None |
| Configure profile/instances/nodes | Task 12.1 (Deployment API) | None |
| Define capabilities per node | Task 12 (Capability API) | None |
| **Validate configuration** | Task 12.1 (ValidationService) | Partial — structural only |
| **Generate provisioning plan** | ❌ Task 13 needed | New module required |
| **Create TwinEntities** | ❌ Task 13 needed | Must call Twin service |
| **Bind relationships** | ❌ Task 13 needed | Must call TwinGraph service |
| Activate in runtime | ❌ Future (Adapter Layer) | Out of scope |

**Assessment: Architecture supports zero-code flow up to provisioning. Task 13 fills the critical gap.**

---

## 6. Multi-Industry Compatibility

### Scenario Testing

#### Smart Building 🏢
```
Profile: "Smart Building v1"
├── Template: TwinTemplate(code="smart_building")
├── Instance: "HQ Building A"
│   ├── Node: "AHU Room 101" (node_type="room", entity_type_id=ahu_room_et)
│   │   └── Capability: TemperatureMeasurement (config: {setpoint: 22})
│   │   └── Capability: AlarmManagement (config: {severity: "high"})
│   ├── Node: "Lighting Circuit B" (node_type="circuit")
│   │   └── Capability: EnergyConsumption (config: {unit: "kWh"})
│   └── Node: "Access Point L1" (node_type="access_point")
│       └── Capability: OccupancyDetection (config: {sensitivity: 0.8})
└── Status: READY
```
✅ Supported by current DeploymentNode abstraction.

#### Manufacturing 🏭
```
Profile: "Factory Line v1"
├── Instance: "Production Line Alpha"
│   ├── Node: "Station 01" (node_type="station")
│   │   └── Capability: ProductionCounting
│   │   └── Capability: OEE
│   ├── Node: "Quality Gate" (node_type="gate")
│   │   └── Capability: QualityInspection
│   └── Node: "Conveyor Main" (node_type="conveyor")
│       └── Capability: MotionControl
└── Status: READY
```
✅ Supported. node_type = "station"/"gate"/"conveyor" handles variation.

#### Energy ⚡
```
Profile: "Power Plant v1"
├── Instance: "Solar Farm South"
│   ├── Node: "PV Array Row 1" (node_type="pv_array")
│   │   └── Capability: PowerMeasurement
│   │   └── Capability: EnergyConsumption
│   ├── Node: "Transformer T1" (node_type="transformer")
│   │   └── Capability: VoltageMeasurement
│   │   └── Capability: AlarmManagement
│   └── Node: "Substation S1" (node_type="substation")
│       └── Capability: PowerMonitoring
└── Status: READY
```
✅ Supported. entity_type_id distinguishes PV Array vs Transformer vs Substation.

#### Campus 🏗️
```
Profile: "Campus Management v1"
├── Instance: "Tech Park"
│   ├── Node: "Building A" (node_type="building")
│   │   └── Capability: EnergyManagement
│   ├── Node: "Parking Lot P1" (node_type="parking")
│   │   └── Capability: EnvironmentMonitoring
│   └── Node: "Main Entrance" (node_type="entrance")
│       └── Capability: SecurityMonitoring
└── Status: READY
```
✅ Supported. Flat or nested structure both work via DeploymentInstance → DeploymentNode hierarchy.

**Multi-Industry Verdict: PASS ✅ — DeploymentNode is sufficiently generic.**

---

## 7. Required Architecture Changes

### Decision: Keep DeploymentNode as Universal Resource Abstraction

**Rationale:**

DeploymentNode already satisfies all four industry scenarios without modification:

| Industry | node_type values | entity_type_id role |
| -------- | ---------------- | ------------------- |
| Building | room, circuit, access_point | Distinguishes AHU Room vs Lighting Circuit |
| Manufacturing | station, gate, conveyor | Distinguishes Production Station vs Quality Gate |
| Energy | pv_array, transformer, substation | Distinguishes each asset type |
| Campus | building, parking, entrance | Distinguishes each facility type |

**Why NOT introduce DeploymentResource abstraction:**
1. Adds unnecessary complexity (extra table, migration, service layer)
2. DeploymentNode + node_type + entity_type_id already provides sufficient differentiation
3. Introducing another abstraction risks confusing the boundary between "deployment planning" and "runtime resource"
4. Future provisioning engine can treat any DeploymentNode as a "provisioning target" without renaming

### ADR-006 Summary

| Field | Content |
| ----- | ------- |
| ID | ADR-006 |
| Title | Keep DeploymentNode as Universal Resource Abstraction |
| Status | Proposed |
| Context | Task 13 needs to provision TwinEntities from DeploymentNodes |
| Decision | Keep DeploymentNode unchanged; do not introduce DeploymentResource |
| Rationale | DeploymentNode + node_type + entity_type_id provides sufficient expressiveness across all industries |
| Consequences | Task 13 will read DeploymentNode directly and create corresponding TwinEntities |
| Migration | None required (no schema change) |

---

## 8. Task 13 Boundary Definition

### What Task 13 MAY Do ✅
- Create `TwinEntity` instances from `DeploymentNode` + `EntityTypeDefinition`
- Create `TwinRelationship` instances from `TemplateRelationship` definitions
- Bind capabilities to created `TwinEntity` via `EntityCapabilityBinding` (new)
- Generate `ProvisioningPlan` objects
- Validate deployment configuration against template/ontology requirements
- Return provisioning status to deployment lifecycle

### What Task 13 MUST NOT Do ❌
- Import `services.adapter.*` — belongs to Device layer
- Import `services.telemetry.*` — belongs to Data layer
- Handle BACnet, MQTT, OPC-UA, Modbus, PLC — belongs to Adapter layer
- Ingest or store telemetry values — belongs to Telemetry layer
- Perform AI reasoning — belongs to AI Agent layer (future)
- Manage runtime device state — belongs to Twin Runtime layer

### Recommended Service Structure
```
services/provisioning/
├── __init__.py
├── exceptions.py
├── models.py          # ProvisioningPlan, ProvisioningItem, ProvisioningExecution
├── schemas.py
├── services.py        # ProvisioningService — orchestrates creation
└── routes.py
```

### Recommended Data Model

| Model | Purpose | FK References |
| ----- | ------- | ------------- |
| `ProvisioningPlan` | Tracks one provisioning run | `deployment_instances.id`, `tenant_id` |
| `ProvisioningItem` | Individual resource creation record | `provisioning_plans.id`, `resource_id` |
| `ProvisioningExecution` | Execution log with timestamps/errors | `provisioning_plans.id` |

---

## 9. Security Review

### Tenant Security Requirements for Task 13

| Rule | Implementation |
| ---- | -------------- |
| tenant_id source | ONLY from `Depends(get_current_tenant)` |
| tenant_id in request body | FORBIDDEN — rejected by schema design |
| Cross-tenant provisioning | BLOCKED — all repos use TenantAwareRepository |
| Required tests | `test_cross_tenant_provisioning_blocked`, `test_template_tenant_isolation`, `test_deployment_instance_isolation` |

**Pattern matches existing deployment layer security. No concerns identified.**

---

## 10. Dependency Boundary (Pre-Flight)

### Forbidden Imports for Task 13
| Module | Reason |
| ------ | ------ |
| `services.adapter.*` | Device communication — outside provisioning scope |
| `services.telemetry.runtime` | Real-time data — outside provisioning scope |
| `services.bacnet/*`, `modbus/*`, `mqtt/*`, `opcua/*`, `plc/*` | Protocol-specific — Adapter layer responsibility |
| `services.ai.*` | AI reasoning — separate domain |

### Allowed Imports for Task 13
| Module | Purpose |
| ------ | ------- |
| `services.core.*` | Base models, repository patterns, config |
| `services.identity.*` | Tenant context, permissions |
| `services.template.*` | Read TwinTemplate schema definitions |
| `services.ontology.*` | Read EntityTypeDefinition, CapabilityDefinition |
| `services.deployment.*` | Read DeploymentInstance, DeploymentNode, DeploymentNodeCapability |
| `services.twin.*` | Create TwinEntity, TwinRelationship |
| `services.twin_graph.*` | Create/update graph edges |

---

## 11. Provisioning Architecture Review

### Recommended Flow

```
┌─────────────────────────────────────────────────────────────┐
│              DeploymentInstance (READY status)               │
│                                                             │
│  Profile ──► Template ──► EntityTypeDefinition             │
│      │          │                  │                       │
│      ▼          ▼                  ▼                       │
│  Nodes ──► CapabilityBindings ──► ConfigSchema             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 ProvisioningEngine (Task 13)                │
│                                                             │
│  1. Plan Generation                                         │
│     - Read DeploymentInstance.nodes                         │
│     - Resolve EntityTypeDefinition for each node            │
│     - Resolve CapabilityDefinition bindings                 │
│     - Generate ProvisioningPlan                             │
│                                                             │
│  2. Planning (idempotent)                                   │
│     - Create ProvisioningItems for each planned action      │
│     - Validate all references exist                         │
│                                                             │
│  3. Execution                                               │
│     - Create TwinEntity for each node                       │
│     - Bind Capabilities to TwinEntity                       │
│     - Create TwinRelationships per TemplateRelationship     │
│     - Update DeploymentInstance status → DEPLOYED           │
│                                                             │
│  4. Error Handling                                          │
│     - Per-item retry with ProvisioningExecution logging     │
│     - Rollback-friendly: mark plan FAILED, keep partial     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    Runtime Ready ✅
```

### Compatibility Verification

| Requirement | Supported? | Evidence |
| ----------- | ---------- | -------- |
| Zero-code deployment | ✅ | Profile → Instance → Node → Capability chain |
| Template marketplace | ✅ | TwinTemplate is industry-neutral registry |
| Industry plugins | ✅ | EntityTypeDefinition + CapabilityDefinition meta model |
| Future AI Agent | ✅ | Provisioning engine produces structured plan, not decisions |
| Idempotent re-deploy | ✅ | ProvisioningPlan tracks state, can resume |

**Architecture is compatible with all stated requirements.**

---

## 12. Final Verdict

### Checklist

| Gate Check | Result |
| ---------- | ------ |
| Frozen boundaries respected (no modifications to Tasks 1–12.1) | ✅ |
| No production code written | ✅ |
| No migrations created | ✅ |
| No existing modules modified | ✅ |
| Zero-code flow validated | ✅ |
| Multi-industry compatibility confirmed | ✅ |
| ADR-006 decision documented | ✅ |
| Task 13 boundary clearly defined | ✅ |
| Security model verified | ✅ |
| Dependency boundaries specified | ✅ |
| New data models sufficient | ✅ |

---

### **TASK 13 ARCHITECTURE ALIGNMENT: APPROVED ✅**

**STATUS: Task 13 may proceed to engineering implementation.**

Awaiting: **"Task 13 Engineering Implementation Prompt"**

---

*This review was performed by the DT-Lite Architecture Guardian Agent.*
*No code was written. No migrations were created. No existing modules were modified.*

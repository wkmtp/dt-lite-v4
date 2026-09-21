# DT-Lite V4.0 UAA Task Dispatch to agnes_flash Team

> **Architecture Baseline**: `DT-Lite_V4.0_Architecture_Freeze_Universal_Asset_Assembly_Contract_v1.0.md` (FROZEN)
> **Reference Spec**: `DT-Lite_V4.0_Universal_Asset_Assembly_Contract_Smart_Park_Production_Asset_Package_Specification_v4.0.md`
> **Execution Rules**: `UAA-01_AgnesCode_Execution_Prompt.md` ~ `UAA-10_AgnesCode_Execution_Prompt.md`
> **Contract Hardening**: `00_UAA_Contract_Hardening_and_Freeze_Specification.md`

---

## 📋 COMMON EXECUTION RULES (MANDATORY FOR ALL UAA TASKS)

### 1. Layered Architecture Compliance
```
API Layer → Application Service → Repository → SQLAlchemy ORM → PostgreSQL
```
- **Controller**: NO business rules, only request validation, DTO conversion, response formatting
- **Service**: ALL business logic, orchestration, cross-entity coordination
- **Repository**: Data access only, NO business logic
- **ORM**: SQLAlchemy models map to tables; migrations via Alembic ONLY

### 2. Universal Contract Priority (FROZEN - HIGHEST)
- **Universal Asset Assembly Contract v1.0** is **FROZEN** — zero tolerance for modifications
- 31 Contract Objects defined in §2 of Architecture Freeze document are IMMUTABLE
- Any deviation requires **Architecture Review Board (ARB) approval** with **Architecture Conflict Report**

### 3. Industry-Agnostic Universal Contract
- **NO** `SmartPark`, `Park`, `Factory`, `Industrial` mandatory fields in Universal Contract
- Industry-specific extensions live in **Industry Asset Package layer** (plugins, templates, profiles)
- Smart Factory compatibility validated by: **Universal Contract semantic diff = ZERO**

### 4. Point Semantic / Protocol Separation (HARD RULE)
| Layer | Responsibility | Example |
|-------|---------------|---------|
| **PointSemantic / Point** | Physical quantity, unit (UCUM/QUDT), semantic tags, aggregation | `asset.park.energy.transformer.power_active` |
| **MappingProfile** | Protocol address, register, function code, scaling, polling | `bacnet:device:123:analog-input:45` |
| **Relation** | One Point ↔ Many MappingProfiles (BACnet/Modbus/OPC UA/MQTT/REST/OCPP) |

### 5. Capability Contract vs Plugin Separation (HARD RULE)
| Layer | Responsibility | Example |
|-------|---------------|---------|
| **CapabilityContract** | **What** — I/O schema, safety level (C0-C4), preconditions, postconditions, idempotency key | `capability.hvac.set_temperature` |
| **CapabilityPlugin** | **How** — Protocol-specific implementation, adapter, vendor SDK | `plugin.hvac.daikin.bacnet` |

### 6. BIM/GIS/3D Identity Boundary (HARD RULE)
- **ModelObject ≠ Asset Identity** — ModelObject is a **rendering/analysis reference only**
- Deleting a BIM element / GIS feature / 3D node **MUST NOT** cascade-delete the Asset
- Binding: `Asset.model_bindings[] → {source, source_id, transform, lod}`

### 7. Dashboard vs LargeScreen (INDEPENDENT OBJECTS)
- **Dashboard**: Interactive, multi-user, role-filtered, widget-based, drill-down
- **LargeScreen**: Read-only, single-layout, auto-rotate, kiosk-mode, TV/wall display
- Different persistence, different rendering pipeline, different permission model

### 8. External Object Model (SEPARATE ONTOLOGY)
- `ExternalSystem / ExternalObject / ExternalPoint / ExternalEvent / ExternalCommand / ExternalRelationship`
- **NOT** part of Universal Ontology
- Zero-code onboarding: Discovery → Classification → MappingProfile Generation → Validation

### 9. AI Security Chain (MANDATORY 6-STEP)
```
Agent → Tool → Capability → Permission → Safety (C0-C4) → Audit
```
- **No bypass**: Agent cannot invoke Capability directly
- **Mutating tools** require explicit Permission + Safety evaluation
- **Every AI action** produces immutable AuditLog entry

### 10. Package Boundary (CI-SCANNED RED LINES)
| Boundary | Rule | CI Validator |
|----------|------|--------------|
| **BL-01** | Package DB migrations ONLY extend Core tables (FK to Core PK) | `alembic check --no-create` |
| **BL-02** | Package NEVER deploys Infra (PostgreSQL, TimescaleDB, Redis, EMQX, MinIO, Neo4j) | Helm chart scan |
| **BL-03** | Package NEVER mutates Core tables directly (must use Core APIs) | SQL pattern scan |
| **BL-04** | Package imports Core Contracts via SDK, NEVER bundles Core code | Dependency graph scan |
| **BL-05** | Package Helm values ONLY parameterize Package resources | `helm template` diff |

### 11. Smart Factory Constraints
- **NO** reimplementation of Assembly Engine
- **NO** hardcoded industry scripts replacing Zero-Code Engine
- **MUST** reuse Universal Contract v1.0 unchanged
- Compatibility matrix: 16 capabilities × 5 domains (Energy, HVAC, Water, Security, Production)

---

## ⚠️ SCOPE LOCK — ABSOLUTE PROHIBITIONS (SL-01 through SL-12)

| ID | Prohibition | Violation = |
|----|-------------|-------------|
| **SL-01** | No new fields in Universal Contract Objects (31 frozen) | Breaking Change |
| **SL-02** | No renaming/removing Universal Contract fields | Breaking Change |
| **SL-03** | No mandatory industry fields in Universal Contract | Breaking Change |
| **SL-04** | No protocol address in PointSemantic/Point definition | Architecture Gate Fail |
| **SL-05** | No algorithm/logic in CapabilityContract | Architecture Gate Fail |
| **SL-06** | No bypass of AI Security Chain (Agent→Tool→Capability→Permission→Safety→Audit) | Security Gate Fail |
| **SL-07** | No Core DB mutation from Package code | CI Scan Fail |
| **SL-08** | No infrastructure deployment in Package Helm chart | CI Scan Fail |
| **SL-09** | No Dashboard/LargeScreen conflation (must remain independent) | Architecture Gate Fail |
| **SL-10** | No ModelObject=Asset identity conflation | Architecture Gate Fail |
| **SL-11** | No ExternalObject in Universal Ontology | Architecture Gate Fail |
| **SL-12** | No weakening Contract constraints to pass tests | **Immediate STOP + Conflict Report** |

---

## 🚦 ARCHITECTURE GATES (EVERY UAA TASK MUST PASS)

### P0 Architecture Gates (11 Gates — MUST PASS)
| Gate | Check | Tool/Method |
|------|-------|-------------|
| **AG-P0-01** | Universal Contract Schema Validation | JSON Schema validator (6 schemas) |
| **AG-P0-02** | Point vs MappingProfile Separation | AST scan for protocol fields in Point |
| **AG-P0-03** | Capability Contract vs Plugin Separation | Interface/implementation scan |
| **AG-P0-04** | AI Security Chain Enforcement | Call graph analysis |
| **AG-P0-05** | Core/Package Boundary (BL-01~05) | CI pipeline validators |
| **AG-P0-06** | BIM/GIS/3D Identity Boundary | FK constraint + cascade test |
| **AG-P0-07** | Dashboard ≠ LargeScreen Independence | Type check + separate persistence |
| **AG-P0-08** | External Object Ontology Separation | Schema diff vs Universal |
| **AG-P0-09** | Composite Asset Tree+Graph Mechanics | Cycle detection + inheritance test |
| **AG-P0-10** | Assembly Engine State Machine (10 states) | State transition test matrix |
| **AG-P0-11** | Control Safety C0-C4 Approval/Audit/Retention | Policy engine test |

### P1 Quality Gates (8 Gates — TARGET PASS)
| Gate | Check | Target |
|------|-------|--------|
| **AG-P1-01** | Unit Test Coverage (Core Services) | ≥ 80% |
| **AG-P1-02** | Integration Test Coverage (API Contracts) | ≥ 70% |
| **AG-P1-03** | Contract Compatibility (Semantic Diff) | ZERO breaking changes |
| **AG-P1-04** | Golden Asset Cross-Layer Validation | GA-01~20 all pass |
| **AG-P1-05** | Golden Scenario Execution | GS-01~10 all pass |
| **AG-P1-06** | Performance (p95 API < 200ms) | Benchmark pass |
| **AG-P1-07** | Security Scan (Trivy + Bandit + pip-audit) | ZERO critical/high |
| **AG-P1-08** | Helm Render + Kubeval (values-smart-park.yaml) | Clean render |

---

## 📦 UAA TASK DEFINITIONS & ACCEPTANCE CRITERIA

---

### UAA-01: Universal Contract Schema, Registry & Validator

**Source**: `UAA-01_AgnesCode_Execution_Prompt.md` + Architecture Freeze §2, §18.1

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **JSON Schemas (6)** | `packages/schemas/universal/` | `Asset.json`, `Point.json`, `Capability.json`, `Relationship.json`, `AssetTemplate.json`, `CompositeAsset.json` |
| **Contract Registry** | `services/core/src/contracts/registry.py` | Load, validate, version, diff Universal Contract objects |
| **Validator CLI** | `tools/contract-validator/` | `contract-validator validate --schema Asset.json --data asset.yaml` |
| **Compatibility Test** | `tests/contracts/test_compatibility.py` | v1.0 ↔ v1.0 semantic diff = ZERO |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: All 31 Universal Contract objects have JSON Schema with `required`, `type`, `enum`, `pattern` constraints
- [ ] **AC-02**: Registry loads schemas at startup, caches, hot-reload on change
- [ ] **AC-03**: Validator CLI returns exit code 0/non-zero, structured JSON output with error paths
- [ ] **AC-04**: Compatibility test: `semantic_diff(universal_v1.0, universal_v1.0) == {}` (ZERO diff)
- [ ] **AC-05**: Unit tests ≥ 80% coverage on registry + validator modules
- [ ] **AC-06**: Integration test: invalid Asset YAML rejected with precise field-level errors
- [ ] **AG-P0-01 PASS**: Schema validation gate passes in CI

#### Pre-Implementation Audit Output (REQUIRED BEFORE CODING)
```markdown
# UAA-01 Pre-Implementation Audit
## Schema Inventory
- [ ] Asset.json — fields: id, code, name, category, attributes, capabilities, relationships, model_bindings, metadata
- [ ] Point.json — fields: id, code, semantic_type, unit, aggregation, tags, asset_id, metadata
- [ ] Capability.json — fields: id, code, category, input_schema, output_schema, safety_level, preconditions, postconditions, idempotency_key
- [ ] Relationship.json — fields: id, source_id, target_id, type, direction, metadata
- [ ] AssetTemplate.json — fields: id, code, name, version, asset_schema, point_templates, capability_templates, relationship_templates, instantiation_params_schema
- [ ] CompositeAsset.json — fields: id, code, name, composition_tree, capability_inheritance, aggregation_rules
## Risk Assessment
- [ ] No protocol fields in Point.json
- [ ] No algorithm fields in Capability.json
- [ ] Safety_level enum = [C0, C1, C2, C3, C4]
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-02: Asset, Template, CompositeAsset & Relationship

**Source**: `UAA-02_AgnesCode_Execution_Prompt.md` + Architecture Freeze §3, §4, §18.2

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **Asset Service** | `services/core/src/asset/` | CRUD, lifecycle, validation, search |
| **AssetTemplate Service** | `services/core/src/asset/template/` | Versioning, instantiation, parameter binding |
| **CompositeAsset Engine** | `services/core/src/asset/composite/` | Tree+Graph composition, capability inheritance, aggregation |
| **Relationship Service** | `services/core/src/asset/relationship/` | Directed, typed, bidirectional sync |
| **Dual-Domain Test** | `tests/asset/test_dual_domain.py` | Building/HVAC + ProductionLine/Machine same runtime |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: Asset CRUD with naming convention `asset.park.<sub>.<type>` enforced
- [ ] **AC-02**: AssetTemplate versioning (SemVer), instantiation with JSON Schema parameter validation
- [ ] **AC-03**: CompositeAsset: Tree hierarchy (parent→children) + Graph relationships (peer→peer)
- [ ] **AC-04**: Capability Inheritance: Child capabilities override/extend parent with conflict resolution
- [ ] **AC-05**: Aggregation: 8 functions (sum, avg, min, max, count, latest, weighted_avg, custom_expr)
- [ ] **AC-06**: Relationship: Directed, typed, cascading options (none, delete, detach), bidirectional sync
- [ ] **AC-07**: Dual-domain test: `Building + HVAC` AND `ProductionLine + Machine` coexist, zero conflicts
- [ ] **AC-08**: Unit tests ≥ 80%, Integration tests ≥ 70%
- [ ] **AG-P0-02, AG-P0-09 PASS**: Architecture gates pass

#### Pre-Implementation Audit Output
```markdown
# UAA-02 Pre-Implementation Audit
## Service Boundaries
- [ ] AssetService: CRUD, validation, search — NO template logic
- [ ] AssetTemplateService: Versioning, instantiation — NO asset CRUD
- [ ] CompositeAssetEngine: Composition, inheritance, aggregation — NO persistence
- [ ] RelationshipService: Graph ops, sync — NO business rules
## Naming Convention Enforcement
- [ ] Regex: ^asset\.park\.(energy|hvac|water|security|transport|environment|production|lighting|fire|elevator|access|parking|waste|green|it)\.[a-z_]+$
## Composite Asset Mechanics
- [ ] Tree: acyclic, single parent, depth ≤ 10
- [ ] Graph: cyclic allowed, max 1000 edges per asset
- [ ] Inheritance: LIFO override, explicit conflict resolution strategy
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-03: Point, Mapping & Capability

**Source**: `UAA-03_AgnesCode_Execution_Prompt.md` + Architecture Freeze §5, §9, §18.3

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **Point Service** | `services/core/src/point/` | Semantic definition, UCUM/QUDT units, aggregation |
| **MappingProfile Service** | `services/iot/src/mapping/` | Protocol-specific address, transform, polling |
| **CapabilityContract Registry** | `services/core/src/capability/contract/` | I/O schema, safety level, pre/post conditions |
| **CapabilityPlugin Framework** | `services/core/src/capability/plugin/` | Adapter interface, vendor implementations |
| **Safety Gate** | `services/core/src/capability/safety/` | C0-C4 enforcement, approval, audit |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: Point definition: `semantic_type` (UCUM/QUDT), `unit`, `aggregation` (8 functions), `tags[]` — **ZERO protocol fields**
- [ ] **AC-02**: MappingProfile: One Point ↔ Many Mappings (BACnet, Modbus, OPC UA, MQTT, REST, OCPP)
- [ ] **AC-03**: MappingProfile fields: `protocol`, `address`, `register`, `function_code`, `scaling`, `polling_interval`, `transform_expr`
- [ ] **AC-04**: CapabilityContract: `input_schema` (JSON Schema), `output_schema`, `safety_level`, `preconditions[]`, `postconditions[]`, `idempotency_key`
- [ ] **AC-05**: CapabilityPlugin: Abstract base class `execute(input) → output`, protocol-specific subclasses
- [ ] **AC-06**: Safety Gate: C0 (observe) auto-approve, C1 (adjust) single-approve, C2 (command) dual-approve, C3 (override) emergency+audit, C4 (interlock) hardware-confirmed
- [ ] **AC-07**: Multi-protocol test: Same Point → BACnet + Modbus + MQTT mappings active simultaneously
- [ ] **AG-P0-02, AG-P0-03, AG-P0-11 PASS**

#### Pre-Implementation Audit Output
```markdown
# UAA-03 Pre-Implementation Audit
## Point Semantic Model
- [ ] UCUM unit codes validated (e.g., "kW", "degC", "m3/h", "Pa", "A", "V")
- [ ] QUDT quantity kinds referenced
- [ ] Aggregation enum: sum, avg, min, max, count, latest, weighted_avg, custom
- [ ] ZERO fields: protocol, address, register, slave_id, topic, url
## Mapping Profile
- [ ] Protocol enum: bacnet, modbus, opcua, mqtt, rest, ocpp
- [ ] Transform: linear (scale+offset), polynomial, lookup_table, script (sandboxed)
- [ ] Polling: interval, timeout, retry, deadband
## Capability Contract
- [ ] Safety level enum: C0, C1, C2, C3, C4 (matches Architecture Freeze §10)
- [ ] Preconditions: JSONLogic expressions on Asset/Point state
- [ ] Postconditions: JSONLogic expressions on result
- [ ] Idempotency key: SHA256(capability_code + input_params + timestamp_window)
## Capability Plugin
- [ ] Interface: initialize(config), execute(input), health_check(), shutdown()
- [ ] Registry: plugin_code → class, versioned
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-04: External Integration & Mapping

**Source**: `UAA-04_AgnesCode_Execution_Prompt.md` + Architecture Freeze §6, §18.4

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **External Object Model** | `services/iot/src/external/` | ExternalSystem, Object, Point, Event, Command, Relationship |
| **Discovery Engine** | `services/iot/src/discovery/` | Protocol-specific discovery (BACnet Who-Is, Modbus scan, OPC UA browse) |
| **Classification Engine** | `services/iot/src/classification/` | Rule-based + ML auto-classification to Universal Asset types |
| **Mapping Generator** | `services/iot/src/mapping/generator/` | Zero-code MappingProfile generation from discovered points |
| **Validation Engine** | `services/iot/src/validation/` | Round-trip read/write, data quality scoring |
| **Mock Adapters** | `services/iot/src/adapters/mock/` | BMS Mock (Building), Factory MES/PLC Mock (Production) |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: ExternalSystem CRUD with 15 categories (BMS, SCADA, PLC, MES, ERP, IoT Gateway, ...)
- [ ] **AC-02**: Discovery: BACnet Who-Is/I-Am, Modbus coil/register scan, OPC UA namespace browse
- [ ] **AC-03**: Classification: Rule engine (YAML rules) + optional ML model → Universal Asset type + Point semantic type
- [ ] **AC-04**: Mapping Generator: Discovered point → MappingProfile YAML (protocol-specific) with transform hints
- [ ] **AC-05**: Validation: Round-trip test (write→read back), data quality score (completeness, timeliness, validity)
- [ ] **AC-06**: BMS Mock: Simulates 50+ Building points (HVAC, lighting, access, fire, elevator)
- [ ] **AC-07**: Factory Mock: Simulates 50+ Production points (MES work orders, PLC tags, OPC UA nodes)
- [ ] **AC-08**: Both mocks use **SAME** External Object Model contract
- [ ] **AG-P0-08 PASS**: External Object Ontology Separation

#### Pre-Implementation Audit Output
```markdown
# UAA-04 Pre-Implementation Audit
## External Object Model (6 Objects)
- [ ] ExternalSystem: id, code, name, category, protocol, connection_config, metadata
- [ ] ExternalObject: id, system_id, object_id, name, type, properties, asset_id (nullable)
- [ ] ExternalPoint: id, object_id, point_id, name, data_type, unit, address, metadata
- [ ] ExternalEvent: id, system_id, object_id, event_type, timestamp, payload, severity
- [ ] ExternalCommand: id, system_id, object_id, command_type, parameters, idempotency_key
- [ ] ExternalRelationship: id, source_system_id, source_object_id, target_system_id, target_object_id, type
## Zero-Code Onboarding Flow
- [ ] 1. Register ExternalSystem → 2. Discover → 3. Classify → 4. Generate MappingProfiles → 5. Validate → 6. Bind to Assets
## Mock Adapters
- [ ] BMS Mock: BACnet/IP, 50 points, realistic values, alarms, trends
- [ ] Factory Mock: OPC UA + Modbus TCP, 50 points, work orders, recipes, quality data
- [ ] BOTH use identical External Object Model interfaces
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-05: Scene, BIM, GIS & 3D

**Source**: `UAA-05_AgnesCode_Execution_Prompt.md` + Architecture Freeze §7, §18.5

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **Scene Service** | `services/twin/src/scene/` | 10 scene types, layout, camera, layers |
| **Model Binding Service** | `services/twin/src/binding/` | Asset ↔ ModelObject (BIM/IFC, GIS/GeoJSON, 3D/glTF) |
| **3D Runtime Integration** | `engine/three-runtime/` | Asset state → 3D visual (color, animation, tooltip) |
| **Identity Boundary Test** | `tests/twin/test_identity_boundary.py` | ModelObject deletion ≠ Asset deletion |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: Scene: 10 types (overview, energy, hvac, water, security, transport, environment, production, fire, custom)
- [ ] **AC-02**: Scene layout: JSON schema with layers, camera, widgets, filters, permissions
- [ ] **AC-03**: Model Binding: `Asset.model_bindings[] → {source: bim|gis|3d, source_id, transform, lod}`
- [ ] **AC-04**: BIM: IFC element GUID binding, property set mapping, LOD 100-500
- [ ] **AC-05**: GIS: GeoJSON feature binding, coordinate transform (WGS84 ↔ local), feature styling
- [ ] **AC-06**: 3D: glTF node binding, material/animation-driven-by-Asset-state
- [ ] **AC-07**: Asset Runtime → 3D: Real-time telemetry drives color (threshold), animation (rotation), tooltip
- [ ] **AC-08**: Identity Boundary: Delete BIM element / GIS feature / 3D node → Asset PERSISTS, binding set to null
- [ ] **AG-P0-06 PASS**: BIM/GIS/3D Identity Boundary

#### Pre-Implementation Audit Output
```markdown
# UAA-05 Pre-Implementation Audit
## Scene Contract (10 Types)
- [ ] overview, energy, hvac, water, security, transport, environment, production, fire, custom
## Model Binding
- [ ] Source enum: bim (IFC), gis (GeoJSON), 3d (glTF)
- [ ] Transform: translation, rotation, scale (matrix 4x4)
- [ ] LOD: 100 (conceptual) to 500 (as-built)
## Identity Boundary (HARD RULE)
- [ ] FK: model_binding.asset_id → Asset.id (ON DELETE SET NULL)
- [ ] NO cascade delete from ModelObject to Asset
- [ ] Test: DELETE FROM bim_elements WHERE guid='X' → Asset still exists, binding.guid = NULL
## 3D Runtime
- [ ] Telemetry → Visual mapping: value → color (gradient), value → animation (speed/angle), value → tooltip
- [ ] Update rate: ≤ 100ms latency from telemetry ingest to 3D update
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-06: Dashboard, LargeScreen, KPI, Alarm, Workflow & WorkOrder

**Source**: `UAA-06_AgnesCode_Execution_Prompt.md` + Architecture Freeze §8, §11, §12, §13, §18.6

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **Dashboard Service** | `services/application/src/dashboard/` | Interactive, widget-based, role-filtered, drill-down |
| **LargeScreen Service** | `services/application/src/largescreen/` | Read-only, auto-rotate, kiosk, TV/wall |
| **KPI Engine** | `services/telemetry/src/kpi/` | 20 KPIs, real-time + scheduled, formula DSL |
| **Alarm Engine** | `services/telemetry/src/alarm/` | 8-state lifecycle, escalation, notification, closure loop |
| **Workflow Engine** | `services/application/src/workflow/` | BPMN-lite, SOP→WorkOrder, human+auto tasks |
| **WorkOrder Service** | `services/application/src/workorder/` | Assignment, SLA, closure, audit trail |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: Dashboard: 13 widget types (chart, gauge, table, map, 3d, alarm_list, kpi_card, ...), role-based visibility
- [ ] **AC-02**: LargeScreen: Independent persistence, layout schema, auto-rotate playlist, kiosk mode, no user interaction
- [ ] **AC-03**: Dashboard ≠ LargeScreen: Different tables, different APIs, different permission models
- [ ] **AC-04**: KPI: 20 definitions (energy_intensity, equipment_availability, occupant_comfort, ...), formula DSL (SQL + time-series functions)
- [ ] **AC-05**: Alarm: 8 states (normal → acknowledged → investigating → resolving → resolved → closed → archived → purged), escalation matrix, notification channels
- [ ] **AC-06**: Alarm→Workflow→WorkOrder chain: Alarm triggers SOP Workflow → creates WorkOrder → tracks to closure → auto-resolves Alarm
- [ ] **AC-07**: Workflow: BPMN-lite (start, user_task, service_task, gateway, end), variable persistence, timer boundaries
- [ ] **AC-08**: GS-09 Pass: Dashboard + LargeScreen + KPI + Alarm + Workflow integrated scenario
- [ ] **AG-P0-07 PASS**: Dashboard ≠ LargeScreen Independence

#### Pre-Implementation Audit Output
```markdown
# UAA-06 Pre-Implementation Audit
## Dashboard vs LargeScreen (INDEPENDENT)
- [ ] Dashboard: tables: dashboard, dashboard_widget, dashboard_permission
- [ ] LargeScreen: tables: largescreen, largescreen_layout, largescreen_playlist
- [ ] NO shared tables, NO shared base class
- [ ] Dashboard: interactive, multi-user, drill-down, real-time WebSocket
- [ ] LargeScreen: read-only, single layout, auto-rotate, WebSocket broadcast only
## KPI Engine
- [ ] 20 KPIs minimum per Architecture Freeze §17
- [ ] Formula DSL: SELECT, AGG, TIME_WINDOW, FILTER, MATH
- [ ] Real-time (streaming) + Scheduled (cron) computation modes
## Alarm Engine
- [ ] 8 states with enforced transitions (no skip)
- [ ] Escalation: time-based + severity-based + acknowledgment-based
- [ ] Closure loop: Alarm → SOP → WorkOrder → Resolution → Alarm.resolved
## Workflow/WorkOrder
- [ ] SOP Template → Workflow Instance → WorkOrder(s)
- [ ] Human tasks: assignee, role, due_date, form_schema
- [ ] Auto tasks: capability_invocation, script, webhook
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-07: AI, Permission, Safety & Audit

**Source**: `UAA-07_AgnesCode_Execution_Prompt.md` + Architecture Freeze §10, §14, §18.7

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **AI Tool Registry** | `services/ai/src/tool/` | Tool definition, I/O schema, capability binding, mutating flag |
| **AI Agent Runtime** | `services/ai/src/agent/` | Agent definition, prompt template, tool allowlist, memory |
| **Permission Engine** | `services/identity/src/permission/` | RBAC + ABAC, resource-action-constraint |
| **Safety Engine** | `services/core/src/safety/` | C0-C4 evaluation, approval workflow, audit trail |
| **Audit Log Service** | `services/core/src/audit/` | Immutable append-only, tamper-evident, query API |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: Tool: `mutating: boolean`, `capability_code`, `input_schema`, `output_schema`, `permission_required`
- [ ] **AC-02**: Agent: `tool_allowlist[]`, `prompt_template`, `memory_config`, `safety_level_max`
- [ ] **AC-03**: Security Chain Enforcement: Agent→Tool→Capability→Permission→Safety→Audit (NO bypass)
- [ ] **AC-04**: Mutating Tool: Requires Permission check + Safety evaluation (C0-C4) BEFORE Capability execution
- [ ] **AC-05**: Safety Engine: C0 auto, C1 single-approve, C2 dual-approve, C3 emergency+audit, C4 hardware-confirmed
- [ ] **AC-06**: Audit Log: Every AI action (tool call, capability exec, safety decision) → immutable entry with hash chain
- [ ] **AC-07**: Audit Query: Filter by agent, tool, capability, safety_level, time_range, outcome
- [ ] **AC-08**: Test: Agent attempts direct Capability call → BLOCKED, Audit entry created
- [ ] **AG-P0-04 PASS**: AI Security Chain Enforcement

#### Pre-Implementation Audit Output
```markdown
# UAA-07 Pre-Implementation Audit
## AI Tool
- [ ] Fields: code, name, description, mutating, capability_code, input_schema, output_schema, permission_required, safety_level
- [ ] Mutating tool MUST have capability_code, permission_required, safety_level ≥ C1
## AI Agent
- [ ] Fields: code, name, prompt_template, tool_allowlist[], memory_config, safety_level_max
- [ ] Agent CANNOT have capability_code directly
## Security Chain (6 Steps - MANDATORY)
1. Agent requests Tool
2. Tool validates Permission (RBAC/ABAC)
3. Tool resolves CapabilityContract
4. Safety Engine evaluates C0-C4
5. Approval workflow (if C1-C4)
6. CapabilityPlugin.execute() → result
7. AuditLog.append(immutable_entry)
## Safety Engine
- [ ] C0: observe — auto-approve, log only
- [ ] C1: adjust — single approver (role-based), 5min timeout
- [ ] C2: command — dual approver (role-separated), 15min timeout
- [ ] C3: override — emergency role + audit trail, 1hr retention
- [ ] C4: interlock — hardware confirmation (digital input), permanent retention
## Audit Log
- [ ] Immutable: append-only table, hash_chain (prev_hash + current_hash)
- [ ] Tamper evidence: Merkle root periodic anchor
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-08: Zero-Code Assembly Engine

**Source**: `UAA-08_AgnesCode_Execution_Prompt.md` + Architecture Freeze §15, §18.8

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **Assembly Engine Core** | `services/application/src/assembly/` | State machine (10 states), context, recipe, plan, step, validation, result |
| **Assembly Recipe DSL** | `packages/schemas/assembly/recipe.json` | Declarative recipe: steps, dependencies, rollback, idempotency |
| **Studio Tools (9)** | `apps/admin/src/studio/` | Asset Designer, Integration Wizard, Scene Composer, Dashboard Designer, LargeScreen Designer, Alarm Designer, Workflow Designer, AI Tool Config, Assembly Wizard |
| **Retry/Idempotency/Rollback** | `services/application/src/assembly/runtime/` | Exponential backoff, idempotency keys, compensating transactions |
| **GS-10 Test** | `tests/assembly/test_gs10_zero_code.py` | New Project → Import BIM → Connect → Discover → Classify → Instantiate → Bind → Generate Apps → Publish |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: AssemblyContext: tenant, project, environment, parameters, secrets, audit_id
- [ ] **AC-02**: AssemblyRecipe: versioned, JSON Schema validated, steps[] with dependencies (DAG)
- [ ] **AC-03**: AssemblyPlan: Compiled from Recipe + Context, executable DAG with parallel groups
- [ ] **AC-04**: AssemblyStep: type (create_asset, bind_point, deploy_capability, generate_dashboard, ...), input, output, retry_policy, rollback_handler
- [ ] **AC-05**: State Machine: 10 states (PENDING → VALIDATING → PLANNING → EXECUTING → PAUSED → ROLLING_BACK → COMPLETED / FAILED / CANCELLED)
- [ ] **AC-06**: Retry: Exponential backoff (max 3), jitter, dead letter queue
- [ ] **AC-07**: Idempotency: Every step has `idempotency_key`, re-execution safe
- [ ] **AC-08**: Rollback: Compensating transaction per step, reverse topological order
- [ ] **AC-09**: Studio Tools (9): All functional, produce valid Recipe/Template YAML
- [ ] **AC-10**: **GS-10 PASS**: Zero business code end-to-end (New Project → Publish)
- [ ] **AG-P0-10 PASS**: Assembly Engine State Machine

#### Pre-Implementation Audit Output
```markdown
# UAA-08 Pre-Implementation Audit
## Assembly Context
- [ ] tenant_id, project_id, environment (dev|staging|prod), parameters{}, secrets{}, audit_id
## Assembly Recipe DSL (JSON Schema)
- [ ] version, metadata, steps[]
- [ ] Step: id, type, depends_on[], input_schema, output_schema, retry_policy, rollback_handler, timeout
- [ ] Step Types: create_asset, instantiate_template, bind_point, deploy_mapping, deploy_capability, generate_dashboard, generate_largescreen, configure_alarm, configure_workflow, configure_ai_tool, publish_app
## State Machine (10 States)
- [ ] PENDING → VALIDATING → PLANNING → EXECUTING → (PAUSED | ROLLING_BACK) → COMPLETED | FAILED | CANCELLED
- [ ] Transitions guarded by validation results
## Retry/Idempotency/Rollback
- [ ] Retry: max_attempts=3, backoff=exp(2^attempt), jitter=±10%
- [ ] Idempotency: key = hash(step_id + input_params + context_hash)
- [ ] Rollback: handler per step type, executed in reverse dependency order
## Studio Tools (9)
1. Asset Designer → AssetTemplate YAML
2. Integration Wizard → MappingProfile YAML
3. Scene Composer → SceneTemplate YAML
4. Dashboard Designer → DashboardTemplate YAML
5. LargeScreen Designer → LargeScreenTemplate YAML
6. Alarm Designer → AlarmDefinition YAML
7. Workflow Designer → WorkflowTemplate YAML
8. AI Tool Config → AITool YAML
9. Assembly Wizard → AssemblyRecipe YAML
## GS-10 Zero-Code E2E
- [ ] New Project wizard
- [ ] Import BIM (IFC) → Auto-extract spaces/elements
- [ ] Connect External Systems (BMS/SCADA)
- [ ] Discover Points
- [ ] Auto Classify → Universal Asset Types
- [ ] Instantiate Assets from Templates
- [ ] Bind Points to Assets
- [ ] Generate Dashboard + LargeScreen + Alarms + Workflows
- [ ] Publish → Live in runtime
- [ ] ZERO business code written
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-09: Golden Assets & Golden Scenarios

**Source**: `UAA-09_AgnesCode_Execution_Prompt.md` + Architecture Freeze §16, §17, §18.9

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **Golden Assets (20)** | `packages/industry/smart-park/golden-assets/` | GA-01~20 YAML + validation test |
| **Golden Scenarios (10)** | `packages/industry/smart-park/golden-scenarios/` | GS-01~10 YAML + execution test |
| **Cross-Layer Validator** | `tools/golden-validator/` | Validates Asset→Point→Capability→Template→Scene→Dashboard→Alarm→Workflow chain |
| **Scenario Runner** | `tools/scenario-runner/` | Executes GS-01~10, produces pass/fail report |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: GA-01~20: Each covers Asset + Point + Capability + Template + Relationship + Binding (cross-layer)
- [ ] **AC-02**: GA Categories: Building, HVAC, Energy, Water, Security, Transport, Environment, Production, Fire, Elevator, Access, Parking, Waste, Green, IT (min 1 per, some multiple)
- [ ] **AC-03**: GS-01~10: Each is a complete ScenarioTemplate with all layers instantiated
- [ ] **AC-04**: GS-01: Energy Management, GS-02: HVAC Optimization, GS-03: Water Management, GS-04: Security & Access, GS-05: Transport & Parking, GS-06: Environment Monitoring, GS-07: Production Monitoring, GS-08: Fire Safety, GS-09: Integrated Operations (Dashboard+LargeScreen+KPI+Alarm+Workflow), GS-10: Zero-Code Assembly (UAA-08)
- [ ] **AC-05**: Cross-Layer Validator: For each GA, validates all 8 layers linked correctly
- [ ] **AC-06**: Scenario Runner: Executes GS, compares runtime state to expected, outputs JUnit XML
- [ ] **AC-07**: **ALL GA-01~20 PASS**, **ALL GS-01~10 PASS**, **GS-10 = Zero Business Code**
- [ ] **AG-P1-04, AG-P1-05 PASS**: Golden Gates

#### Pre-Implementation Audit Output
```markdown
# UAA-09 Pre-Implementation Audit
## Golden Assets (20 Minimum)
| GA-ID | Category | Asset Types | Points | Capabilities | Templates | Scenes | Dashboards | Alarms | Workflows |
|-------|----------|-------------|--------|--------------|-----------|--------|------------|--------|-----------|
| GA-01 | Building | Building, Floor, Zone | 15 | 5 | 3 | 1 | 1 | 3 | 2 |
| GA-02 | HVAC | AHU, FCU, Chiller, Pump | 25 | 8 | 4 | 1 | 1 | 5 | 3 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| GA-20 | IT | Server, Switch, UPS | 10 | 3 | 2 | 1 | 1 | 2 | 1 |
## Golden Scenarios (10)
- [ ] GS-01 Energy Management
- [ ] GS-02 HVAC Optimization
- [ ] GS-03 Water Management
- [ ] GS-04 Security & Access
- [ ] GS-05 Transport & Parking
- [ ] GS-06 Environment Monitoring
- [ ] GS-07 Production Monitoring
- [ ] GS-08 Fire Safety
- [ ] GS-09 Integrated Operations
- [ ] GS-10 Zero-Code Assembly (from UAA-08)
## Cross-Layer Validation Rules
- [ ] Asset.code follows naming convention
- [ ] Point.semantic_type valid UCUM/QUDT
- [ ] Capability.safety_level matches operation risk
- [ ] Template.instantiation_params_schema valid JSON Schema
- [ ] Scene.model_bindings reference existing Asset
- [ ] Dashboard.widgets reference valid KPI/Alarm/Point
- [ ] Alarm.escalation references valid Workflow
- [ ] Workflow.tasks reference valid Capability
## Design Lock Sign-off: _________________ Date: __________
```

---

### UAA-10: Smart Factory Compatibility & Final Freeze

**Source**: `UAA-10_AgnesCode_Execution_Prompt.md` + Architecture Freeze §19, §20, §18.10

#### Deliverables
| Artifact | Path | Description |
|----------|------|-------------|
| **Factory Mock Package** | `packages/industry/smart-factory/` | AssetPackage manifest, templates, mock adapters |
| **Compatibility Test Suite** | `tests/compatibility/test_smart_factory.py` | Factory assembly using Universal Contract ONLY |
| **Semantic Diff Tool** | `tools/contract-diff/` | `contract-diff universal_v1.0 factory_usage → ZERO breaking changes` |
| **Final Freeze Report** | `docs/architecture/freeze/ARCHITECTURE_FREEZE_REPORT_v1.0.md` | Consolidated sign-off, all gates passed |

#### Acceptance Criteria (ALL MUST PASS)
- [ ] **AC-01**: Smart Factory AssetPackage loads without modifying Universal Contract
- [ ] **AC-02**: Factory assets (ProductionLine, Machine, Robot, AGV, CNC, Mold, Tool, Fixture) instantiate via Universal Contract
- [ ] **AC-03**: Factory capabilities (OEE, predictive_maintenance, quality_inspection, recipe_management, scheduling) use CapabilityContract + Plugin
- [ ] **AC-04**: Factory points (vibration, temperature, pressure, current, position, cycle_count) use PointSemantic + MappingProfile
- [ ] **AC-05**: Factory external systems (MES, PLC, SCADA, ERP, Historian) onboard via External Object Model
- [ ] **AC-06**: Factory scenes (production_overview, cell_detail, quality_dashboard, maintenance_view) use Scene Contract
- [ ] **AC-07**: **Universal Contract Semantic Diff = ZERO** (no breaking changes, no additions, no removals)
- [ ] **AC-08**: Compatibility Matrix: 16 capabilities × 5 domains all GREEN
- [ ] **AC-09**: All 12 Release Gates pass (Architecture Freeze §21)
- [ ] **AC-10**: Final Freeze Report signed by Architecture Review Board

#### Pre-Implementation Audit Output
```markdown
# UAA-10 Pre-Implementation Audit
## Smart Factory AssetPackage
- [ ] Manifest: asset-package.yaml with version, dependencies, schemas, templates, profiles
- [ ] NO Core infrastructure deployment (BL-02)
- [ ] NO Core DB mutations (BL-03)
- [ ] Imports Core SDK only (BL-04)
## Compatibility Validation
- [ ] Universal Contract v1.0 used AS-IS (no fork, no extension)
- [ ] Factory assets use asset.park.production.* naming (industry package convention)
- [ ] Factory capabilities use CapabilityContract (What) + Plugin (How)
- [ ] Factory points use PointSemantic (semantic) + MappingProfile (protocol)
- [ ] Factory external systems use External Object Model
## Semantic Diff = ZERO
- [ ] Tool: contract-diff --baseline universal_v1.0.json --target factory_usage.json
- [ ] Output: {} (empty diff)
- [ ] Any non-empty diff = ARCHITECTURE CONFLICT REPORT → STOP
## Release Gates (12 Gates from Architecture Freeze §21)
1. [ ] Schema Validation Gate
2. [ ] Architecture Gate (11 P0)
3. [ ] Unit Test Coverage Gate (≥80% core)
4. [ ] Integration Test Gate (≥70% API)
5. [ ] Contract Compatibility Gate (ZERO diff)
6. [ ] Golden Asset Gate (GA-01~20 PASS)
7. [ ] Golden Scenario Gate (GS-01~10 PASS)
8. [ ] Security Scan Gate (ZERO critical/high)
9. [ ] Helm Render Gate (values-smart-park.yaml clean)
10. [ ] Performance Gate (p95 < 200ms)
11. [ ] Documentation Gate (all contracts documented)
12. [ ] ARB Sign-off Gate
## Design Lock Sign-off: _________________ Date: __________
```

---

## 📋 MANDATORY OUTPUT FORMAT: FINAL REPORT (EVERY UAA TASK)

Each UAA task **MUST** produce a `FINAL_REPORT_UAA-XX.md` with this exact structure:

```markdown
# FINAL REPORT: UAA-XX [Task Name]

## Executive Summary
- **Status**: PASS / FAIL
- **Date**: YYYY-MM-DD
- **Engineer**: [Name]
- **Reviewer**: [Name]

## Deliverables Checklist
| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| [Deliverable 1] | [path] | ✅/❌ | |
| [Deliverable 2] | [path] | ✅/❌ | |

## Acceptance Criteria Results
| AC-ID | Description | Result | Evidence |
|-------|-------------|--------|----------|
| AC-01 | [description] | ✅ PASS / ❌ FAIL | [test log link / screenshot] |
| AC-02 | [description] | ✅ PASS / ❌ FAIL | [test log link / screenshot] |
| ... | ... | ... | ... |

## Architecture Gate Results
| Gate | Check | Result | Evidence |
|------|-------|--------|----------|
| AG-P0-01 | [description] | ✅ PASS / ❌ FAIL | [CI log link] |
| AG-P0-02 | [description] | ✅ PASS / ❌ FAIL | [CI log link] |
| ... | ... | ... | ... |
| AG-P1-01 | [description] | ✅ PASS / ❌ FAIL | [CI log link] |
| ... | ... | ... | ... |

## Test Coverage
| Module | Unit Coverage | Integration Coverage | Target Met? |
|--------|---------------|---------------------|-------------|
| [module] | XX% | YY% | ✅/❌ |

## Architecture Conflict Report (IF ANY)
> **ONLY if any P0 gate FAILS or Scope Lock violated**

```markdown
# ARCHITECTURE CONFLICT REPORT: UAA-XX
## Conflict Summary
- **Gate Violated**: AG-P0-XX / SL-XX
- **Root Cause**: [Technical description]
- **Impact**: [Which contracts, services, tests affected]
- **Proposed Resolution**: [Option A / Option B / Requires ARB]
## ARB Decision
- [ ] Approved with mitigation
- [ ] Rejected — revert to baseline
- [ ] Deferred — requires spec change
**ARB Chair**: _________________ **Date**: __________
```

## Risk Register
| Risk | Likelihood | Impact | Mitigation | Status |
|------|------------|--------|------------|--------|
| [Risk 1] | High/Med/Low | High/Med/Low | [Mitigation] | Open/Mitigated |

## Sign-off
- **Engineer**: _________________ **Date**: __________
- **Tech Lead**: _________________ **Date**: __________
- **Architecture Review Board**: _________________ **Date**: __________
```

---

## 🚀 DISPATCH INSTRUCTIONS FOR agnes_flash TEAM

### Execution Order (SEQUENTIAL — NOT PARALLEL)
```
UAA-01 → UAA-02 → UAA-03 → UAA-04 → UAA-05 → UAA-06 → UAA-07 → UAA-08 → UAA-09 → UAA-10
```
**Rationale**: Each task builds on contracts/services from previous tasks. Parallel execution causes integration conflicts.

### Phase Gates Between Tasks
| Transition | Required Gate | Blocking Condition |
|------------|---------------|-------------------|
| UAA-01 → UAA-02 | Schema Validation (AG-P0-01) | FAIL = STOP |
| UAA-02 → UAA-03 | Asset/Template/Composite/Relationship tests PASS | FAIL = STOP |
| UAA-03 → UAA-04 | Point/Mapping/Capability + Safety Gate PASS | FAIL = STOP |
| UAA-04 → UAA-05 | External Model + Mocks PASS | FAIL = STOP |
| UAA-05 → UAA-06 | Scene/BIM/GIS/3D + Identity Boundary PASS | FAIL = STOP |
| UAA-06 → UAA-07 | Dashboard/LargeScreen/KPI/Alarm/Workflow PASS | FAIL = STOP |
| UAA-07 → UAA-08 | AI Security Chain + Audit PASS | FAIL = STOP |
| UAA-08 → UAA-09 | Assembly Engine + GS-10 PASS | FAIL = STOP |
| UAA-09 → UAA-10 | ALL Golden Assets/Scenarios PASS | FAIL = STOP |
| UAA-10 → FREEZE | Semantic Diff = ZERO + 12 Release Gates PASS | FAIL = STOP |

### CI/CD Integration
Each UAA task **MUST** add its tests to the comprehensive CI pipeline (`.github/workflows/ci-comprehensive.yml`):
- Unit tests → `unit-tests` job (service-specific path)
- Integration tests → `integration-smoke` job
- Architecture scans → `arch-scan` job (custom rules per task)
- Contract validation → `contract-validator` in `arch-scan`
- Golden tests → `golden-gate` job (new, add to pipeline)

### Communication Protocol
1. **Pre-Implementation**: Submit Audit Output → **WAIT for Design Lock Sign-off** → Begin coding
2. **Daily**: Update task status in project board (Not Started / In Progress / Review / Done / Blocked)
3. **Blocker**: Immediate escalation with Architecture Conflict Report template
4. **Completion**: Submit Final Report → Peer Review → ARB Sign-off → Merge

---

## 📌 ESCALATION CONTACTS

| Role | Contact | Escalation Trigger |
|------|---------|-------------------|
| **Tech Lead (agnes_flash)** | [Assigned] | Task-level blockers, design decisions |
| **Architecture Review Board** | [Architecture Team] | P0 gate failures, Scope Lock violations, Contract changes |
| **Product Owner** | [PO] | Scope changes, priority conflicts |
| **Platform Team** | [Platform] | Core service changes, infra dependencies |

---

## ✅ DISPATCH CONFIRMATION

**Dispatched By**: Architecture Team
**Date**: 2026-09-12
**Baseline Version**: Universal Asset Assembly Contract v1.0 (FROZEN)
**Total Tasks**: 10 (UAA-01 through UAA-10)
**Estimated Duration**: 10-14 weeks (sequential)
**Success Criteria**: All 10 Final Reports = PASS, Semantic Diff = ZERO, GS-10 Zero-Code E2E PASS

---

> **⚠️ CRITICAL REMINDER**: 
> - Universal Contract v1.0 is **FROZEN**. Any modification attempt = **Immediate STOP + Architecture Conflict Report**
> - **No weakening Contract constraints to pass tests** — this is non-negotiable
> - **GS-10 (Zero-Code End-to-End) is the ultimate acceptance test** — if it fails, the architecture is not ready
> - **Smart Factory Compatibility** is validated by **Universal Contract Semantic Diff = ZERO** — not by "it works"

**End of Dispatch Document**
# DT-Lite V4.0 Universal Asset Assembly Contract v1.0
## Contract Hardening & Freeze Specification

**Document ID:** DT-Lite-V4.0-UAA-CONTRACT-HARDENING-FREEZE  
**Version:** 1.0.0  
**Status:** Engineering Freeze Specification  
**Primary Industry Validator:** Smart Park  
**Secondary Compatibility Validator:** Smart Factory Mock  
**Implementation Agent:** AgnesCode

---

## 1. Purpose

本文件将 DT-Lite V4.0 的 Universal Asset Assembly Contract 从架构原则进一步固化为可由 AgnesCode 逐项实现、测试和验收的工程 Contract。

最终目标：

```text
DT-Lite Core
      +
Universal Asset Assembly Contract v1.0
      +
Industry Asset Package
      +
Zero-Code Assembly Engine
      +
Twin Runtime
```

Smart Park 是第一个真实行业样板；Smart Factory 是第二个兼容性验证器。

Factory 扩展只能采用：

```text
复制/复用 Universal Contract
        ↓
新增 Factory Ontology
        ↓
新增 Factory Assets
        ↓
新增 Factory Integration
        ↓
新增 Factory Templates
        ↓
新增 Factory Scenarios
```

不得重新设计 Universal Assembly Engine。

---

# 2. Highest-Priority Freeze Rules

## UAA-FR-001 Universal Contract 优先级最高

任何 Smart Park / Smart Factory 业务需求都不得直接修改 Universal Contract。

发现冲突：

```text
STOP
↓
Architecture Conflict Report
↓
等待架构决策
```

## UAA-FR-002 Industry Neutrality

Universal Object 不得包含 Park-only 或 Factory-only mandatory field。

行业字段只能进入 Industry Package Extension。

## UAA-FR-003 Stable Identity

所有持久化 Universal Object 必须有稳定 `id`。

以下均不得作为 Universal identity：

```text
BIM object id
GIS feature id
PLC address
BACnet instance
Modbus register
OPC UA node id
MQTT topic
External business id
```

## UAA-FR-004 Semantic / Protocol Separation

```text
PointSemantic
    ↓
Point
    ↓
PointMapping
    ↓
ExternalPoint
    ↓
Connector
```

PointSemantic 和 Point 不保存协议地址。

## UAA-FR-005 Asset Semantic Authority

```text
BIM / GIS / 3D ModelObject
        ↓
ModelBinding
        ↓
Asset
```

空间模型不是业务 Asset identity。

## UAA-FR-006 Capability / Implementation Separation

Capability 定义“能做什么”；Connector / Plugin / Adapter 定义“如何实现”。

## UAA-FR-007 External Isolation

```text
ExternalSystem
 ↓
Connector
 ↓
ExternalObject
 ↓
MappingProfile
 ↓
Universal Object
```

## UAA-FR-008 Declarative Application

Dashboard、LargeScreen、KPI、Alarm、Workflow、WorkOrder、AI Tool 必须可声明式装配。

## UAA-FR-009 Assembly State Machine

Assembly 必须具备：

```text
state
transition
precondition
validation
retry
rollback
audit
result
```

## UAA-FR-010 Factory Compatibility

Factory Mock 前后：

```text
Universal Contract semantic diff = ZERO
```

否则 UAA v1.0 不得冻结。

---

# 3. Universal Object Registry

## 3.1 Asset

```text
AssetType
AssetTemplate
Asset
CompositeAssetTemplate
CompositeAsset
Property
Relationship
```

## 3.2 Telemetry / Capability

```text
PointSemantic
Point
PointMapping
CapabilityContract
Capability
```

## 3.3 Integration

```text
ExternalSystem
Connector
ConnectorInstance
ExternalObject
ExternalPoint
ExternalEvent
ExternalCommand
ExternalRelationship
IntegrationProfile
MappingProfile
```

## 3.4 Spatial / 3D

```text
Model
ModelObject
ModelBinding
Scene
SceneTemplate
SceneBinding
```

## 3.5 Application

```text
Widget
DashboardTemplate
Dashboard
LargeScreenTemplate
LargeScreen
KPI
Rule
Alarm
SOP
WorkflowTemplate
Workflow
WorkOrderTemplate
WorkOrder
```

## 3.6 AI / Governance

```text
AITool
AIAgent
Permission
SafetyContract
AuditRecord
```

## 3.7 Assembly / Package

```text
ScenarioTemplate
Scenario
AssemblyContext
AssemblyRecipe
AssemblyPlan
AssemblyStep
AssemblyValidation
AssemblyResult
Package
PackageManifest
PackageDependency
PackageVersion
Migration
```

---

# 4. Base Object Contract

所有持久化 Universal Object 统一采用：

```yaml
object:
  id: string
  type: string
  version: string

  name: string
  description: string|null

  lifecycle:
    status: string
    created_at: datetime
    created_by: string
    updated_at: datetime
    updated_by: string

  governance:
    owner_ref: string|null
    source_ref: string|null
    confidence: number|null

  metadata:
    labels: object
    tags: array
    extensions: object
```

Mandatory：

```text
id
type
version
lifecycle.status
created_at
created_by
updated_at
updated_by
```

Rules：

- `id` 生命周期内不可改变。
- `type` 必须来自 Registry 或合法 Industry Extension。
- `version` 使用 SemVer。
- `extensions` 不得覆盖 Universal 字段。
- `extensions` 不得改变 Universal 字段语义。

---

# 5. Asset Contract

## 5.1 AssetType

Required：

```yaml
id:
version:
name:
ontology_ref:
```

Optional：

```yaml
parent_type_ref:
property_definitions: []
point_definitions: []
capability_refs: []
allowed_relationships: []
```

Lifecycle：

```text
DRAFT → ACTIVE → DEPRECATED → RETIRED
```

## 5.2 AssetTemplate

```yaml
id:
version:
asset_type_ref:
required_properties: []
point_bindings: []
capability_refs: []
default_relationships: []
validation_rules: []
```

Optional：

```yaml
default_scene_binding:
default_dashboard_binding:
default_alarm_refs: []
default_workflow_refs: []
default_ai_tool_refs: []
default_model_bindings: []
```

Template 必须可以实例化合法 Asset。

## 5.3 Asset

Required：

```yaml
id:
type_ref:
template_ref:
template_version:

identity:
  name:
  code:

lifecycle:
  status:

properties: {}
points: []
capabilities: []
relationships: []

spatial:
  scene_ref:
  parent_asset_ref:
  location_ref:

external_bindings: []
model_bindings: []

application_bindings:
  dashboards: []
  large_screens: []
  kpis: []
  alarms: []
  workflows: []
  ai_tools: []
```

Lifecycle：

```text
DRAFT
→ PROVISIONED
→ ACTIVE
→ SUSPENDED
→ DECOMMISSIONED
→ ARCHIVED
```

## 5.4 CompositeAsset

必须支持 Tree + Graph：

```yaml
id:
root_asset_ref:
member_refs: []
relationship_refs: []
```

标准关系：

```text
contains
located_in
feeds
supplies
controls
monitors
serves
depends_on
connected_to
belongs_to
```

Building/HVAC 与 ProductionLine/Machine 必须使用同一 Composite Asset Runtime。

---

# 6. Point Contract

## 6.1 PointSemantic

```yaml
id:
quantity_kind:
data_type:
unit:
value_semantics:
```

可选：

```yaml
engineering_range:
quality_policy:
historical_policy:
retention_policy:
missing_data_policy:
calibration_policy:
aggregation_policy:
```

禁止：

```text
BACnet instance
Modbus register
OPC UA node id
MQTT topic
PLC address
REST endpoint
```

## 6.2 Point

```yaml
id:
asset_ref:
semantic_ref:
direction:
```

Direction：

```text
TELEMETRY
STATE
COMMAND
PARAMETER
EVENT
```

Runtime metadata：

```text
source_timestamp
ingest_timestamp
quality
sampling
deadband
historical
aggregation
retention
availability
missing_data_policy
calibration
estimated_value_policy
```

## 6.3 PointMapping

```yaml
id:
point_ref:
mapping_profile_ref:
external_point_ref:

transform:
  read:
  write:

quality_mapping:
timestamp_mapping:
enabled:
```

同一 PointSemantic 必须能够映射到：

```text
BACnet
Modbus
OPC UA
MQTT/REST 等
```

---

# 7. Capability Contract

```yaml
id:
version:
input_schema:
output_schema:
preconditions:
errors:
permission_ref:
safety_contract_ref:

execution_policy:
  timeout:
  retry_policy:
  idempotency:
  audit_required:
  approval_required:
```

Capability 不得内嵌：

```text
vendor algorithm
connector implementation
industry business implementation
```

---

# 8. External Integration Contract

## ExternalSystem

```yaml
id:
name:
category:
protocol:
lifecycle:
vendor:
connection_profile_ref:
capabilities: []
```

## Connector

```yaml
id:
type:
version:
supported_protocol:
features:
  discovery:
  read:
  write:
  event:
  command:
```

## ConnectorInstance

```yaml
id:
connector_ref:
external_system_ref:
endpoint_ref:
credential_ref:
status:
```

凭证只能引用 Secret Store。

## ExternalObject

```yaml
id:
system_ref:
external_id:
external_type:
parent_ref:
properties: {}
status:
```

## ExternalPoint

保存 external system 自身的：

```text
external_id
external_type
protocol-specific metadata
```

但不能污染 Universal Point。

## IntegrationProfile

定义：

```text
Discovery
Classification
Mapping
Validation
Read Test
Write Test
Event Test
Command Test
```

## MappingProfile

负责：

```text
External Object Type → AssetType
External Point → PointSemantic / Point
External Event → Alarm/Event
External Command → Capability
External Relationship → Relationship
```

---

# 9. BIM / GIS / 3D Contract

## Model

```text
id
type
version
source
format
```

## ModelObject

```text
id
model_ref
external_object_id
geometry_ref
properties
```

## ModelBinding

```yaml
id:
asset_ref:
model_ref:
model_object_ref:

transform:
  position:
  rotation:
  scale:

visualization:
  visible:
  lod:
  state_visualization:
  interaction:
  drill_down:
```

允许抽象来源：

```text
BIM
GIS
GLB / glTF
CAD-derived
3D Tiles
```

Rules：

1. 一个 Asset 可以绑定多个 ModelObject。
2. 一个 ModelObject 不能成为 Asset 唯一业务身份。
3. 删除 ModelObject 不得删除 Asset。
4. Asset runtime state 可以驱动 3D visualization。

---

# 10. Scene Contract

```yaml
id:
type:
asset_selector:
```

Optional：

```yaml
model_refs: []
scene_bindings: []
dashboard_refs: []
large_screen_refs: []
interaction_policy:
camera:
filters:
```

Scene 引用 Asset，不拥有 Asset。

---

# 11. Dashboard / LargeScreen

## Widget

```yaml
id:
type:
data_source:
binding:
refresh_policy:
interaction:
style:
drill_down:
```

## Dashboard

```yaml
id:
template_ref:
layout:
widgets: []
data_bindings: []
permission_ref:
```

## LargeScreen

```yaml
id:
template_ref:
resolution:
layout:
widgets: []
refresh_policy:
display_profile:
auto_rotation:
drill_down:
alarm_overlay:
multi_screen:
full_screen:
```

Dashboard 与 LargeScreen 必须是两个独立 Contract。

---

# 12. KPI

```yaml
id:
inputs: []

calculation:
  expression:
  aggregation:
  time_window:

dimensions: []
filters: []
unit:
target:
thresholds: []
refresh_policy:
```

计算链：

```text
Input
→ Calculation
→ Aggregation
→ Time Window
→ Dimension
→ Threshold
→ Output
```

Park 可以定义 Energy Intensity；Factory 可以定义 OEE；Contract 不变。

---

# 13. Alarm

Rule 负责：

```text
condition
event correlation
alarm generation
workflow trigger
workorder trigger
notification
```

Alarm State Machine：

```text
DETECTED
→ RAISED
→ ACKNOWLEDGED
→ DIAGNOSING
→ DISPATCHED
→ RESOLVED
→ VERIFIED
→ CLOSED
```

Exception：

```text
FAILED
SUPPRESSED
CANCELLED
```

每次 transition 必须记录：

```text
from
to
actor
condition
timestamp
evidence
audit
```

非法 transition 必须拒绝。

---

# 14. Workflow / SOP / WorkOrder

## WorkflowTemplate

```yaml
trigger:
steps:
conditions:
branches:
approvals:
actions:
compensation:
closure:
```

## WorkOrderTemplate

定义工单结构。

## WorkOrder

```yaml
id:
template_ref:
source:
asset_ref:
priority:
assignment:
sla:
checklist:
evidence:
attachments:
execution:
verification:
closure:
audit:
```

Lifecycle：

```text
DRAFT
→ CREATED
→ ASSIGNED
→ ACCEPTED
→ IN_PROGRESS
→ BLOCKED
→ COMPLETED
→ VERIFIED
→ CLOSED
```

允许：

```text
BLOCKED → IN_PROGRESS
```

默认禁止：

```text
DRAFT → CLOSED
CREATED → VERIFIED
```

---

# 15. AI Contract

## AITool

```yaml
id:
version:
input_schema:
output_schema:
permission_ref:
safety_contract_ref:
audit_policy:
execution_mode:
```

Execution Mode：

```text
READ_ONLY
MUTATING
```

## AIAgent

强制链：

```text
Agent
 ↓
AITool
 ↓
Capability
 ↓
Permission
 ↓
SafetyContract
 ↓
Execution
 ↓
AuditRecord
```

Agent 禁止直接访问：

```text
Database
SQL
PLC
Connector
External System
```

---

# 16. Permission / Safety / Audit

## Permission

```yaml
subject:
resource:
action:
scope:
effect:
```

## SafetyContract

```yaml
control_level:
approval_required:
conditions:
external_safety_system:
```

安全等级：

```text
C0
C1
C2
C3
C4
```

## AuditRecord

```yaml
id:
actor:
action:
resource:
before:
after:
timestamp:
result:
correlation_id:
```

所有 mutating AI execution 必须产生 AuditRecord。

---

# 17. Scenario Contract

## ScenarioTemplate

必须能够声明：

```text
assets
integrations
scenes
dashboards
large_screens
kpis
alarms
workflows
workorders
ai
assembly_recipe
acceptance
```

## Scenario

Scenario 是项目实例，不允许嵌入业务代码。

---

# 18. Assembly Contract

## AssemblyContext

```yaml
id:
project_ref:
package_refs: []
spatial_sources: []
integration_refs: []
policy_refs: []
target_environment:
```

## AssemblyRecipe

```yaml
id:
version:
inputs: []
preconditions: []
steps: []
validations: []
outputs: []
rollback_policy:
```

## AssemblyStep

```yaml
id:
action:
inputs:
preconditions:
execution:
outputs:
validations:
errors:
retry:
rollback:
audit:
```

Allowed actions：

```text
discover
classify
instantiate
bind
validate
simulate
generate
accept
publish
upgrade
rollback
```

---

# 19. Assembly State Machine

```text
DRAFT
→ DISCOVERING
→ CLASSIFYING
→ INSTANTIATING
→ BINDING
→ VALIDATING
→ SIMULATING
→ GENERATING
→ ACCEPTANCE_PENDING
→ APPROVED
→ PUBLISHING
→ PUBLISHED
→ RUNNING
```

Exception：

```text
FAILED
ROLLED_BACK
SUSPENDED
```

Mandatory：

1. 非法 transition 必须拒绝。
2. FAILED 必须产生 error + audit。
3. Retry step 必须声明 idempotency。
4. Rollback 使用已记录 AssemblyResult。
5. Publish 前必须 Validation + Acceptance。
6. Runtime 不得消费未 Published version。
7. PUBLISHED → RUNNING 必须可审计。

---

# 20. Reference Contract

```text
Asset
 ├─ instanceOf → AssetType
 ├─ configuredBy → AssetTemplate
 ├─ hasProperty → Property
 ├─ hasPoint → Point
 ├─ supports → Capability
 ├─ relatedTo → Asset
 ├─ mappedTo → ExternalObject
 ├─ boundTo → ModelObject
 └─ visualizedBy → Scene
```

Point：

```text
Point
 → PointSemantic
 → PointMapping
 → MappingProfile
 → ExternalPoint
 → Connector
 → ExternalSystem
```

Application：

```text
Asset
 → KPI
 → Alarm
 → Workflow
 → WorkOrder
```

AI：

```text
AIAgent
 → AITool
 → Capability
 → Permission
 → SafetyContract
 → AuditRecord
```

Assembly：

```text
Scenario
 → AssemblyRecipe
 → AssemblyPlan
 → AssemblyStep
 → AssemblyValidation
 → AssemblyResult
```

---

# 21. Forbidden References

```text
PointSemantic → Protocol Address
Point → PLC register
Dashboard → Protocol tag directly
AI Agent → Database
AI Agent → Connector directly
Asset → BIM Object as primary identity
ExternalObject → AssetType replacement
Industry Asset → Core-only migration
Factory Asset → Park mandatory dependency
Package → Core DB direct mutation
```

---

# 22. Lifecycle Matrix

| Object | Lifecycle |
|---|---|
| AssetType | DRAFT → ACTIVE → DEPRECATED → RETIRED |
| AssetTemplate | DRAFT → PUBLISHED → DEPRECATED → RETIRED |
| Asset | DRAFT → PROVISIONED → ACTIVE → SUSPENDED → DECOMMISSIONED → ARCHIVED |
| Point | DRAFT → ACTIVE → DISABLED → RETIRED |
| Capability | DRAFT → PUBLISHED → DEPRECATED → RETIRED |
| Mapping | DRAFT → TESTED → ACTIVE → DISABLED → RETIRED |
| Scene | DRAFT → PUBLISHED → DEPRECATED → RETIRED |
| Dashboard | DRAFT → PUBLISHED → DEPRECATED → RETIRED |
| LargeScreen | DRAFT → PUBLISHED → DEPRECATED → RETIRED |
| Workflow | DRAFT → PUBLISHED → RUNNING → SUSPENDED → COMPLETED → RETIRED |
| WorkOrder | DRAFT → CREATED → ASSIGNED → ACCEPTED → IN_PROGRESS → BLOCKED → COMPLETED → VERIFIED → CLOSED |
| AITool | DRAFT → APPROVED → PUBLISHED → DEPRECATED → RETIRED |
| Assembly | DRAFT → DISCOVERING → ... → RUNNING / FAILED / ROLLED_BACK |

---

# 23. Package Contract

```yaml
package:
  id:
  name:
  version:

  universal_contract:
    id: "dt-lite.universal-asset-assembly"
    version: "1.0.0"
    compatibility: "strict"

  core_platform:
    ref:
    version_range:

  dependencies: []

  contents:
    ontology: []
    assets: []
    templates: []
    integrations: []
    applications: []
    ai: []
    scenarios: []
```

Package 不得修改：

```text
Core schema
IAM
Twin Runtime
Workflow Runtime
Universal Contract
```

---

# 24. Smart Park / Smart Factory Boundary

## Shared Universal Layer

```text
Asset
AssetType
AssetTemplate
CompositeAsset
Point
PointSemantic
PointMapping
Relationship
Capability
ExternalObject
Connector
IntegrationProfile
MappingProfile
Scene
ModelBinding
Dashboard
LargeScreen
Widget
KPI
Alarm
Rule
Workflow
WorkOrder
AITool
AIAgent
Scenario
AssemblyContext
AssemblyRecipe
AssemblyPlan
AssemblyStep
AssemblyValidation
AssemblyResult
Permission
SafetyContract
AuditRecord
```

## Smart Park Extension

```text
Park
Building
Floor
Room
HVAC
Chiller
AHU
Pump
FireSystem
Elevator
Parking
PV
BESS
Security
```

## Smart Factory Extension

```text
Factory
Workshop
ProductionLine
Machine
Robot
Conveyor
PLC
SCADA
MES
QMS
WMS
Recipe
Batch
OEE
```

Factory 只能增加 Industry Package 内容，不得改变 Shared Universal Layer。

---

# 25. Compatibility Test Suite

## CT-001 Identity

验证 stable ID、type、version、tenant scope。

## CT-002 Required Fields

缺失 mandatory field → FAIL。

## CT-003 Type Validation

错误 data type → FAIL。

## CT-004 Reference Integrity

dangling / illegal reference → FAIL。

## CT-005 Lifecycle

非法 transition → FAIL。

## CT-006 Protocol Isolation

Point / PointSemantic 出现协议地址 → FAIL。

## CT-007 External Isolation

ExternalObject 不得替代 Universal Ontology。

## CT-008 Capability Safety

控制能力缺 Permission / Safety → FAIL。

## CT-009 AI Boundary

Agent bypass Tool / Capability / Permission / Safety → FAIL。

## CT-010 Assembly Transition

非法 Assembly transition → FAIL。

## CT-011 Idempotency

重复执行 idempotent step 不得创建重复 Asset。

## CT-012 Rollback

Assembly failure 后必须恢复稳定版本。

## CT-013 Park Compatibility

至少验证：

```text
Park
Building
HVAC
Meter
Alarm
Dashboard
WorkOrder
```

## CT-014 Factory Compatibility

至少验证：

```text
Factory
ProductionLine
Machine
Robot
Alarm
Dashboard
WorkOrder
```

## CT-015 Contract Diff

```text
Universal Contract semantic diff = ZERO
```

---

# 26. Golden Scenarios

```text
GS-01 Energy Monitoring
GS-02 HVAC Operations
GS-03 Security
GS-04 Parking
GS-05 Fire
GS-06 Environment
GS-07 Facility Maintenance
GS-08 BIM / 3D
GS-09 Command Center
GS-10 Zero-Code End-to-End
```

GS-10：

```text
New Park Project
→ Import BIM
→ Connect BMS
→ Connect EMS
→ Connect CCTV
→ Discover
→ Auto Classify
→ Instantiate
→ Bind
→ Generate Dashboard
→ Generate Large Screen
→ Generate Alarm/SOP
→ Publish
```

最终实施人员不得修改 Python、TypeScript、SQL，也不得直接修改生产数据库。

---

# 27. Architecture Rules for AgnesCode

固定工程链：

```text
Contract
→ Schema
→ Domain Model
→ Application Service
→ Repository
→ ORM
→ Migration
→ API
→ Test
→ Golden Scenario
→ Acceptance
```

平台架构：

```text
API
 ↓
Application Service
 ↓
Repository
 ↓
SQLAlchemy ORM
 ↓
PostgreSQL
```

发现 Core/UAA 冲突：

```text
STOP
→ Architecture Conflict Report
```

不得私自修改冻结 Contract。

---

# 28. Release Gates

```text
Gate 01 Schema
Gate 02 Ontology
Gate 03 Point / Mapping
Gate 04 Capability
Gate 05 Template
Gate 06 Integration
Gate 07 Scene / BIM / GIS
Gate 08 Dashboard / LargeScreen
Gate 09 Workflow / WorkOrder
Gate 10 AI
Gate 11 Zero-Code
Gate 12 Factory Compatibility
```

---

# 29. Final Freeze Checklist

```text
[ ] Object Registry Complete
[ ] Every Core Object has Schema
[ ] Valid / Invalid Fixtures Complete
[ ] Required Fields Complete
[ ] Reference Integrity PASS
[ ] Lifecycle PASS
[ ] State Machine PASS
[ ] Point / Mapping Separation PASS
[ ] Capability / Implementation Separation PASS
[ ] External Isolation PASS
[ ] BIM/GIS/3D Binding PASS
[ ] Dashboard PASS
[ ] LargeScreen PASS
[ ] KPI PASS
[ ] Alarm PASS
[ ] Workflow PASS
[ ] WorkOrder PASS
[ ] AI Permission/Safety/Audit PASS
[ ] Zero-Code GS-10 PASS
[ ] Smart Park GS-01~GS-10 PASS
[ ] Factory Mock PASS
[ ] Factory Contract Semantic Diff = ZERO
[ ] Full Regression PASS
```

## Final Freeze Definition

> UAA v1.0 不是因为规格书完成而冻结，而是因为 Smart Park 与 Smart Factory Mock 可以使用同一个 Contract、同一套 Assembly Semantics、同一套 Zero-Code Assembly Engine 完成装配，而不需要修改 Universal Contract。

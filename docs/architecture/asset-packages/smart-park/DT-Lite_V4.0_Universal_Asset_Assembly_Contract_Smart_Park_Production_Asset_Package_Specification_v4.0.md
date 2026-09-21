# DT-Lite V4.0 Universal Asset Assembly Contract & Smart Park Production Asset Package Specification v4.0

**Document ID:** DT-Lite-V4.0-UAA-SPAP-SPEC  
**Version:** v4.0  
**Status:** Architecture Baseline / Scope Lock Candidate  
**Primary Industry Sample:** Smart Park  
**Universal Contract:** Universal Asset Assembly Contract v1.0  
**Target:** Production-ready Zero-Code Smart Park Asset Package  
**Future Compatibility:** Smart Factory  
**Date:** 2026-09-11

---

## 0. 文档定位

本规格书在 `DT-Lite V4.0 Smart Park Industry Asset Package` v3.0-Reformulated 基础上重新下沉。

v3.0 已形成五层架构、Manifest、依赖图、命名、Point/Mapping 分离、Capability/Plugin 分离、C0-C4、安全边界、Template、Assembly Recipe、Zero-Code、Golden Asset、Release Gate 等治理基础；本版保留这些原则，并补齐真正实现生产级零代码装配所需的行业与运行对象。fileciteturn11file0L24-L36

**最高优先级冻结项：Universal Asset Assembly Contract v1.0。**

Smart Park 是第一个真实行业样板，但 Universal Contract 必须保持行业无关。未来 Smart Factory 不重新设计平台装配机制，而只增加 Factory Ontology、Assets、Integrations、Templates、Scenarios 和业务规则。

```text
Universal Asset Assembly Contract v1.0
                ↓
        复制/继承 Contract
                ↓
        新增 Factory Ontology
                ↓
        新增 Factory Assets
                ↓
        新增 Factory Integration
                ↓
        新增 Factory Scenarios
```

---

# 1. Architecture Baseline

## 1.1 五层架构

| Layer | 名称 | 职责 | 交付物 |
|---|---|---|---|
| L1 | Ontology | 语义本体、资产类型、关系、Point Semantic | `ontology/` |
| L2 | Capability | 能力契约、标准接口、Adapter Contract | `capability/` |
| L3 | Template | Asset/Composite/Scene Template、Assembly Recipe | `templates/` |
| L4 | Application | Dashboard、Large Screen、KPI、Alarm、Workflow、WorkOrder、AI | `application/` |
| L5 | Operations | Golden Asset、Golden Scenario、Migration、Release Gate、Compatibility | `operations/` |

强制依赖方向：

```text
L5 → L4 → L3 → L2 → L1
```

Package 只消费 Core Platform Contract，不定义 Core 数据库和基础设施。

---

# 2. Universal Asset Assembly Contract v1.0

## 2.1 Contract 对象

以下对象必须冻结为通用协议：

```text
Asset
AssetType
AssetTemplate
CompositeAsset
CompositeAssetTemplate

Property
Point
PointSemantic
PointMapping
Relationship

Capability
CapabilityContract

ExternalSystem
ExternalObject
ExternalPoint
ExternalEvent
ExternalCommand
ExternalRelationship

IntegrationProfile
MappingProfile

Scene
SceneTemplate
SceneBinding
ModelBinding

Dashboard
DashboardTemplate
LargeScreen
LargeScreenTemplate
Widget

KPI
Alarm
Rule
Workflow
SOP
WorkOrder

AITool
AIAgent

Scenario
ScenarioTemplate
AssemblyContext
AssemblyRecipe
AssemblyPlan
AssemblyValidation
AssemblyResult

Permission
SafetyContract
AuditRecord

Package
PackageManifest
PackageDependency
PackageVersion
Migration
```

## 2.2 Universal Assembly Contract

```yaml
assembly_contract:
  contract_version: "1.0"

  identity:
    asset_type: required
    template: required

  configuration:
    properties: supported
    instantiation_params: required

  telemetry:
    points: supported
    mappings: externalized

  relationships:
    topology: supported

  capabilities:
    contracts: supported

  visualization:
    scene_binding: supported
    dashboard_binding: supported

  operations:
    alarms: supported
    workflows: supported
    work_orders: supported

  intelligence:
    ai_tools: supported

  integration:
    external_objects: supported

  lifecycle:
    validate: required
    simulate: required
    publish: required
    upgrade: required
    rollback: required
```

### 强制原则

1. Universal Contract 不得包含 `park-only`、`factory-only` 等行业字段。
2. 行业语义只能进入 Industry Ontology / Asset / Capability / Integration / Scenario。
3. Smart Factory 必须复用本 Contract，不得重新实现 Assembly Engine。

---

# 3. Asset Contract

## 3.1 Asset Identity

```yaml
asset:
  id: "asset.park.facility.ahu"
  type: "asset.park.facility.ahu"
  template: "tpl.park.facility.ahu"
  template_version: "1.0.0"

  name: "AHU-001"

  lifecycle:
    status: "active"

  location:
    scene_id: "scene.park.building-a"
    spatial_id: "building-a-floor-03-zone-01"
```

Asset 必须支持：

```text
Identity
Properties
Points
Relationships
Capabilities
External Bindings
Scene Binding
Dashboard Binding
Alarm Binding
Workflow Binding
AI Tool Binding
Lifecycle
Audit
```

---

# 4. Smart Park Production Asset Ontology

Smart Park 第一版必须至少覆盖：

```text
spatial
building
energy
electrical
hvac
water
lighting
fire
security
parking
transport
environment
elevator
renewable-energy
facility
operation
management
```

## 4.1 Spatial

```text
asset.park.spatial.park
asset.park.spatial.building
asset.park.spatial.building-group
asset.park.spatial.floor
asset.park.spatial.zone
asset.park.spatial.room
asset.park.spatial.corridor
asset.park.spatial.road
asset.park.spatial.plaza
asset.park.spatial.green-area
asset.park.spatial.parking-area
```

## 4.2 Electrical

```text
asset.park.energy.transformer
asset.park.energy.switchgear
asset.park.energy.distribution-cabinet
asset.park.energy.busbar
asset.park.energy.power-meter
asset.park.energy.generator
asset.park.energy.ups
asset.park.energy.ats
asset.park.energy.pdu
```

## 4.3 HVAC

```text
asset.park.facility.chiller
asset.park.facility.cooling-tower
asset.park.facility.ahu
asset.park.facility.fcu
asset.park.facility.vav
asset.park.facility.fan
asset.park.facility.pump
asset.park.facility.valve
asset.park.facility.heat-exchanger
asset.park.facility.heat-pump
asset.park.management.hvac-controller
```

## 4.4 Water

```text
asset.park.energy.water-meter
asset.park.facility.water-tank
asset.park.facility.water-pump
asset.park.facility.water-valve
asset.park.facility.water-treatment
asset.park.environment.leak-sensor
asset.park.facility.drainage-pump
```

## 4.5 Lighting

```text
asset.park.facility.lighting-controller
asset.park.facility.lighting-group
asset.park.facility.street-light
asset.park.facility.indoor-light
asset.park.facility.landscape-light
```

## 4.6 Fire

```text
asset.park.security.fire-panel
asset.park.security.smoke-detector
asset.park.security.heat-detector
asset.park.security.manual-call-point
asset.park.security.fire-hydrant
asset.park.facility.fire-pump
asset.park.facility.sprinkler
asset.park.facility.fire-valve
asset.park.security.fire-door
asset.park.security.emergency-light
```

## 4.7 Security

```text
asset.park.security.camera
asset.park.security.camera-ptz
asset.park.security.nvr
asset.park.security.access-controller
asset.park.security.door
asset.park.security.reader
asset.park.security.barrier
asset.park.security.intercom
asset.park.security.intrusion-sensor
asset.park.security.alarm-panel
```

## 4.8 Parking / Transport

```text
asset.park.transport.parking-lot
asset.park.transport.parking-zone
asset.park.transport.parking-space
asset.park.transport.parking-gate
asset.park.transport.parking-camera
asset.park.transport.license-plate-camera
asset.park.transport.charging-pile
asset.park.transport.agv
```

## 4.9 Environment

```text
asset.park.environment.temperature-sensor
asset.park.environment.humidity-sensor
asset.park.environment.co2-sensor
asset.park.environment.pm25-sensor
asset.park.environment.voc-sensor
asset.park.environment.noise-sensor
asset.park.environment.weather-station
asset.park.environment.water-quality
```

## 4.10 Elevator / Renewable Energy / Operations

```text
asset.park.facility.elevator
asset.park.facility.escalator
asset.park.facility.elevator-controller

asset.park.energy.pv-array
asset.park.energy.pv-inverter
asset.park.energy.storage-bess
asset.park.energy.pcs

asset.park.operation.inspection-point
asset.park.operation.work-order
asset.park.operation.maintenance-plan
asset.park.operation.asset-maintenance
asset.park.operation.spare-part
asset.park.operation.technician
asset.park.operation.service-request
asset.park.operation.sla
```

目标生产基线：**≥60 Asset Types**。

---

# 5. Composite Asset Contract

Composite Asset 是 Smart Park 与 Smart Factory 的核心共用机制。

```text
Building
 ├── Electrical
 ├── HVAC
 ├── Lighting
 ├── Fire
 ├── Security
 └── Elevator

Production Line
 ├── Machine
 ├── Robot
 ├── Conveyor
 ├── Vision
 └── PLC
```

二者都必须通过相同 `CompositeAsset` 机制装配。

```yaml
composite_asset:
  id: "asset.park.spatial.building-a"
  type: "asset.park.spatial.building"

  children:
    - ref: "asset.park.energy.transformer"
    - ref: "asset.park.facility.chiller"
    - ref: "asset.park.security.camera"

  relationships:
    - type: "contains"
    - type: "feeds"
    - type: "controls"

  inherited_capabilities:
    - "monitoring"
    - "alarm"
    - "maintenance"
```

必须支持：

- 子资产
- 父子关系
- 拓扑关系
- 能力继承
- KPI 聚合
- Alarm 聚合
- Scene 聚合
- Dashboard 聚合
- Workflow 聚合

---

# 6. Point Semantic Contract

v3.0 的核心原则必须保持：

> **Point ≠ Protocol Tag**

Point 只定义语义契约；协议地址由 Mapping Profile 管理。v3.0 已明确提出 Point Definition 与 Mapping Profile 分离，以支持一对多协议适配。fileciteturn11file0L122-L136

## 6.1 Point

```yaml
point:
  semantic_id: "point.park.energy.transformer.active-power"

  quantity_kind: "power"
  unit: "kW"
  data_type: "float64"

  telemetry:
    sampling:
      interval: "1s"
      strategy: "report_on_change"
      deadband: 0.5

    historical: true

  constraints:
    min: -5000
    max: 5000
```

必须支持：

```text
sampling
deadband
historical
aggregation
retention
availability
sourceTimestamp
ingestTimestamp
quality
missingDataPolicy
calibration
estimatedValuePolicy
```

Aggregation 至少：

```text
latest
min
max
avg
sum
count
delta
rate
```

---

# 7. Mapping Profile

```text
Semantic Point
      │
 ┌────┼──────┬──────┬──────┐
 ↓    ↓      ↓      ↓      ↓
BACnet Modbus OPC-UA MQTT REST
```

Smart Park v1 至少支持：

```text
BACnet/IP
Modbus TCP
Modbus RTU
OPC UA
MQTT
HTTP/REST
WebSocket
OCPP
```

示例：

```yaml
mapping_profile:
  id: "map.bacnet.ahu.v1"
  protocol: "bacnet-ip"
  external_type: "AHU"

  mapping:
    point:
      semantic_id: "point.park.facility.ahu.supply-air-temperature"
      object_type: "analog-input"
      object_instance: 101
      property: "present-value"

  polling:
    interval: "1s"
    timeout: "500ms"
    retries: 3
```

---

# 8. External Object Model

这是 Park → Factory 可复用集成协议的关键。

对象：

```text
ExternalSystem
ExternalObject
ExternalPoint
ExternalEvent
ExternalCommand
ExternalRelationship
```

示例：

```yaml
external_system:
  id: "system.park.bms.vendor-a"
  category: "BMS"
  vendor: "vendor-a"
  protocol: "bacnet-ip"

external_object:
  system_ref: "system.park.bms.vendor-a"
  external_id: "AHU-001"
  external_type: "AHU"

  mapped_asset:
    asset_type: "asset.park.facility.ahu"
    asset_id: "ahu-001"
```

未来工厂：

```yaml
external_object:
  system_ref: "system.factory.mes"
  external_id: "M001"
  external_type: "machine"

  mapped_asset:
    asset_type: "asset.factory.equipment.machine"
    asset_id: "machine-001"
```

DT-Lite Core 的 Asset Contract 不改变。

---

# 9. Integration Profile

Smart Park 必须预留：

```text
BMS / BAS
EMS
SCADA
CCTV
Access Control
Parking
Fire System
Elevator System
CMMS / FM
ERP
WMS
GIS
BIM
IoT Platform
Weather
Billing
Visitor System
```

## 9.1 Zero-Code 接入流程

```text
选择系统
 ↓
选择协议 / Connector
 ↓
输入连接信息
 ↓
测试连接
 ↓
自动发现
 ↓
自动分类
 ↓
Asset Type Mapping
 ↓
Point Mapping
 ↓
验证
 ↓
预览
 ↓
发布
```

业务人员不得编写代码、修改 YAML、操作 Kubernetes 或直接修改数据库。

---

# 10. BIM / GIS / 3D Contract

## 10.1 Model Binding

```yaml
model_binding:
  model_id: "bim.park.building-a"
  source_type: "BIM"

  objects:
    - external_object_id: "IfcSpace_001"
      asset_id: "room-001"

      visualization:
        visible: true
        lod: 2
```

必须支持：

```text
BIM
GIS
GLB / glTF
CAD-derived model
3D Tiles
```

Asset ↔ Model 必须具备：

```text
model_id
object_id
external_id
asset_id
transform
visibility
LOD
state_visualization
interaction
drill_down
```

3D 是表现层，Twin Asset 才是业务语义事实源。

---

# 11. Scene Contract

Scene 类型：

```text
Park
Building
Floor
Zone
Equipment
Security
Energy
Parking
Operations
Command Center
```

```yaml
scene:
  id: "scene.park.command-center"

  assets:
    selector:
      scene_id: "park-001"

  models:
    - ref: "bim.park.master-model"

  dashboards:
    - ref: "dash.park.command-center"

  large_screens:
    - ref: "screen.park.command-center"
```

---

# 12. Dashboard Contract

Dashboard 是 L4 一等对象。

类型至少包括：

```text
Asset Dashboard
Building Dashboard
Energy Dashboard
Equipment Dashboard
Security Dashboard
Environment Dashboard
Operations Dashboard
Management Dashboard
AI Dashboard
```

Widget 至少：

```text
KPI Card
Trend
Table
Ranking
Alarm List
Map
3D Scene
Video Wall
Energy Flow
Topology
Gauge
Status
Work Order
Statistics
AI Insight
```

```yaml
dashboard:
  id: "dash.park.energy"

  layout:
    type: "grid"
    columns: 24

  widgets:
    - id: "energy-kpi"
      type: "kpi"
      data:
        ref: "kpi.park.energy.consumption"

    - id: "energy-trend"
      type: "trend"
      point_selector:
        semantic: "point.park.energy.*.energy-total"
```

---

# 13. Large Screen Contract

大屏必须是独立一等对象，而不是 Dashboard 别名。

```yaml
large_screen:
  id: "screen.park.command-center"
  type: "command-center"

  resolution:
    width: 7680
    height: 2160

  layout:
    columns: 24

  widgets:
    - type: "3d-scene"
    - type: "kpi"
    - type: "alarm-ranking"
    - type: "energy-flow"
    - type: "building-ranking"
    - type: "environment"
    - type: "video-wall"

  behavior:
    refresh: "5s"
    auto_rotation: true
    drill_down: true
    alarm_overlay: true
```

标准 Smart Park 大屏：

1. 园区综合驾驶舱
2. 能源驾驶舱
3. 设备驾驶舱
4. 安防驾驶舱
5. 环境驾驶舱
6. 停车驾驶舱
7. 运维驾驶舱
8. 领导驾驶舱

---

# 14. KPI Contract

```yaml
kpi:
  id: "kpi.park.energy.energy-intensity"
  name: "单位面积能耗"

  inputs:
    - "point.park.energy.*.energy-total"

  formula:
    type: "expression"
    expression: "energy / floor_area"

  aggregation:
    period: "day"
```

Smart Park KPI 至少：

```text
总能耗
单位面积能耗
峰值负荷
需量
水耗
能耗成本
新能源占比
HVAC 能效
设备在线率
设备故障率
告警闭环率
工单及时率
SLA 达成率
停车利用率
充电利用率
环境达标率
视频在线率
门禁在线率
电梯故障率
```

目标：**≥20 KPI**。

---

# 15. Alarm / Rule Contract

Alarm 生命周期：

```text
Detected
 ↓
Raised
 ↓
Acknowledged
 ↓
Diagnosing
 ↓
Dispatched
 ↓
Resolved
 ↓
Verified
 ↓
Closed
```

```yaml
alarm:
  id: "alm.park.facility.ahu.high-temperature"

  severity: "critical"

  trigger:
    point: "point.park.facility.ahu.supply-air-temperature"
    operator: ">"
    threshold: 35
    duration: "60s"

  enrichment:
    - asset_state
    - related_points
    - recent_alarms

  response:
    notification: true
    create_work_order: true
    suggest_sop: true
```

---

# 16. Workflow / SOP / WorkOrder Contract

标准闭环：

```text
Event
 ↓
Alarm
 ↓
Correlation
 ↓
Diagnosis
 ↓
Decision
 ↓
WorkOrder
 ↓
Dispatch
 ↓
Execution
 ↓
Evidence
 ↓
Verification
 ↓
Closure
 ↓
KPI
```

WorkOrder 必须支持：

```text
source
asset
priority
assignment
SLA
checklist
evidence
attachments
execution
verification
closure
audit
```

示例：

```yaml
work_order:
  id: "wo.park.facility.ahu.maintenance"

  source:
    alarm_ref: "alm.park.facility.ahu.high-temperature"

  asset_ref: "ahu-001"

  priority: "high"

  assignment:
    role: "facility-technician"

  sla:
    response_minutes: 30
    resolution_hours: 4

  evidence:
    photo: true
    checklist: true
    meter_reading: true

  closure:
    verification_required: true
```

---

# 17. Capability Contract

Capability 只定义：

> What the asset can do

Plugin 定义：

> How an algorithm is implemented

Universal Capability Categories：

```text
observe
measure
aggregate
diagnose
control
configure
maintain
notify
visualize
query
export
```

```yaml
capability:
  id: "cap.park.facility.ahu.monitor"

  requires:
    - "point.park.facility.ahu.supply-air-temperature"
    - "point.park.facility.ahu.return-air-temperature"

  provides:
    - interface: "telemetry/query"
    - interface: "health/status"

  lifecycle:
    timeout: "5s"

  safety:
    control_level: "C0"
```

---

# 18. Control Safety Contract

保留 v3.0 的 C0-C4：

| Level | Meaning |
|---|---|
| C0 | Observe |
| C1 | Adjust |
| C2 | Command |
| C3 | Override |
| C4 | Interlock |

v3.0 已明确将 C0-C4 与审批、审计和典型场景绑定。fileciteturn11file0L154-L170

## 18.1 Safety Boundary

C4 不意味着 DT-Lite 自己实现物理安全：

```text
DT-Lite
  ↓
Safety Contract
  ↓
External Controller / PLC / SIS
  ↓
Hardware Interlock
```

DT-Lite 负责 Contract、权限、反馈、审计和状态；物理安全链由外部安全控制系统负责。

---

# 19. AI Contract

## 19.1 AI Tool

```yaml
ai_tool:
  id: "tool.park.energy.anomaly-detect"

  input:
    asset_id: "string"
    time_range: "object"

  output:
    anomalies: "array"
    confidence: "number"

  permissions:
    read:
      - telemetry
```

## 19.2 Smart Park Agents

```text
Park Assistant
Energy Agent
Facility Agent
Security Agent
Environment Agent
Parking Agent
Operations Agent
Management Agent
```

AI 调用链：

```text
AI Agent
 ↓
AI Tool
 ↓
Capability Contract
 ↓
Permission
 ↓
Safety Contract
 ↓
Execution
```

AI 不得绕过任何权限、安全或审计机制。

---

# 20. Zero-Code Assembly

## 20.1 Assembly Lifecycle

```text
DRAFT
 ↓
DISCOVERY
 ↓
CLASSIFICATION
 ↓
INSTANTIATION
 ↓
BINDING
 ↓
VALIDATION
 ↓
SIMULATION
 ↓
APP_GENERATION
 ↓
ACCEPTANCE
 ↓
PUBLISH
 ↓
RUNTIME
```

## 20.2 AssemblyContext

```yaml
assembly_context:
  id: "assembly.park.demo-001"

  project:
    name: "Smart Park Demo"

  spatial:
    source: "BIM"

  integrations:
    - BMS
    - EMS
    - CCTV
    - ACCESS
    - PARKING
    - FM

  policies:
    alarm: "standard"
    dashboard: "park-command-center"
    security: "enterprise"
```

## 20.3 AssemblyRecipe

```yaml
assembly_recipe:
  id: "recipe.park.production-standard"
  version: "1.0.0"

  inputs:
    - assembly_context

  steps:
    - action: "discover"
    - action: "classify"
    - action: "instantiate"
    - action: "bind"
    - action: "validate"
    - action: "simulate"
    - action: "generate_application"
    - action: "accept"
    - action: "publish"
```

---

# 21. Zero-Code Studio

业务配置人员必须通过 UI 完成：

```text
Asset Designer
Integration Wizard
Scene Composer
Dashboard Designer
Large Screen Designer
Alarm Designer
Workflow Designer
AI Tool Configuration
Assembly Wizard
```

## 21.1 Asset

```text
选择 Asset Type
 ↓
填写参数
 ↓
选择 Template
 ↓
绑定空间
 ↓
预览
 ↓
发布
```

## 21.2 Integration

```text
选择 BMS
 ↓
选择 BACnet
 ↓
连接测试
 ↓
自动发现
 ↓
自动分类
 ↓
自动 Mapping
 ↓
异常确认
 ↓
预览
 ↓
发布
```

## 21.3 Scene

```text
选择场景模板
 ↓
选择园区 / 建筑
 ↓
绑定 BIM/GIS
 ↓
选择 Asset
 ↓
空间绑定
 ↓
3D 预览
 ↓
发布
```

## 21.4 Application

```text
选择 Dashboard / Large Screen Template
 ↓
绑定 KPI
 ↓
绑定 Widget
 ↓
绑定 Asset Selector
 ↓
预览
 ↓
发布
```

---

# 22. Smart Park Production Baseline

第一生产版最低目标：

| 对象 | 最低数量 |
|---|---:|
| Asset Types | ≥60 |
| Point Semantics | ≥200 |
| Capability Contracts | ≥40 |
| Integration / Mapping Templates | ≥30 |
| Asset Templates | ≥20 |
| Composite Templates | ≥10 |
| Dashboards | ≥8 |
| Large Screens | ≥8 |
| KPI | ≥20 |
| Alarm Rules | ≥30 |
| SOP | ≥15 |
| WorkOrder Templates | ≥15 |
| AI Tools | ≥8 |
| AI Agents | ≥8 |
| Golden Scenarios | ≥10 |

这些是生产基线，不是上限。

---

# 23. Standard Composite Assets

必须提供：

```text
Park
Building
Building Energy System
Building HVAC System
Building Security System
Building Fire System
Building Water System
Building Parking System
Energy Station
HVAC Station
Security Station
Parking Station
Operations Center
Command Center
```

---

# 24. Golden Assets

保留 v3.0 Golden Asset 的全链路验证思想；v3.0 原有 10 个资产已经覆盖变压器、水表、冷机、水泵、PTZ、环境站、充电桩、电梯、BAS 面板、开关柜。fileciteturn11file0L265-L286

v4.0 扩展为：

```text
GA-01 Transformer
GA-02 Switchgear
GA-03 Power Meter
GA-04 Water Meter
GA-05 Chiller
GA-06 AHU
GA-07 Pump
GA-08 Cooling Tower
GA-09 Fire Pump
GA-10 Fire Panel
GA-11 PTZ Camera
GA-12 Access Controller
GA-13 Elevator
GA-14 Parking Gate
GA-15 Parking Space
GA-16 Charging Pile
GA-17 Air Quality Station
GA-18 PV Inverter
GA-19 BESS
GA-20 Building Composite Asset
```

每个 Golden Asset 至少验证：

```text
Ontology
 → Capability
 → Template
 → Point
 → Mapping
 → Integration
 → Scene
 → Dashboard
 → Alarm
 → Workflow
 → WorkOrder
 → AI
 → Assembly
 → Runtime
```

---

# 25. Golden Scenario

Golden Scenario 比单一 Golden Asset 更能证明“零代码可落地”。

## GS-01 Energy Monitoring

```text
EMS/BMS
 → Discovery
 → Energy Asset
 → Mapping
 → KPI
 → Dashboard
 → Alarm
 → AI
```

## GS-02 HVAC Operations

```text
BMS
 → AHU/Chiller
 → Telemetry
 → Efficiency KPI
 → Alarm
 → SOP
 → WorkOrder
```

## GS-03 Security

```text
CCTV + Access
 → Assets
 → Event
 → Alarm
 → Video Association
 → WorkOrder
```

## GS-04 Parking

```text
Parking System
 → Parking Space
 → Gate
 → Vehicle Event
 → Occupancy KPI
 → Large Screen
```

## GS-05 Fire

```text
Fire System
 → Fire Asset
 → Alarm
 → SOP
 → Evacuation Workflow
 → Audit
```

## GS-06 Environment

```text
Sensors
 → Environment Asset
 → KPI
 → Alarm
 → Notification
 → Dashboard
```

## GS-07 Facility Maintenance

```text
Asset
 → Alarm
 → Diagnosis
 → WorkOrder
 → Dispatch
 → Evidence
 → Verification
 → Closure
```

## GS-08 BIM / 3D

```text
BIM
 → Object Discovery
 → Asset Binding
 → 3D Scene
 → Runtime State
 → Drill Down
```

## GS-09 Command Center

```text
Park
 → Multiple Systems
 → Scene
 → KPI
 → Alarm
 → Video
 → 3D
 → Large Screen
```

## GS-10 Zero-Code End-to-End

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

GS-10 是 Smart Park v4.0 最终零代码验收场景。

---

# 26. Smart Factory Compatibility

## 26.1 必须复用

Smart Factory MUST reuse：

```text
Asset
Point
Capability
CompositeAsset
ExternalObject
IntegrationProfile
MappingProfile
Template
Scene
Dashboard
LargeScreen
KPI
Alarm
Workflow
WorkOrder
AITool
Scenario
AssemblyContext
AssemblyRecipe
```

## 26.2 Factory 只增加

```text
Factory Ontology
Factory Assets
Factory Capabilities
Factory Integration
Factory Templates
Factory Scenarios
Factory KPI
Factory Workflow
Factory AI
```

例如：

```text
asset.factory.equipment.machine
asset.factory.equipment.robot
asset.factory.equipment.conveyor
asset.factory.production.production-line
asset.factory.control.plc
asset.factory.quality.vision-system
```

但使用同一：

```text
Point Contract
Capability Contract
External Object Model
Mapping Profile
Composite Asset
Assembly Recipe
Zero-Code Studio
```

---

# 27. Universal Assembly Compatibility Matrix

| Capability | Park | Building | HVAC | Machine | Production Line |
|---|---:|---:|---:|---:|---:|
| Identity | ✓ | ✓ | ✓ | ✓ | ✓ |
| Property | ✓ | ✓ | ✓ | ✓ | ✓ |
| Point | ✓ | ✓ | ✓ | ✓ | ✓ |
| Relationship | ✓ | ✓ | ✓ | ✓ | ✓ |
| Capability | ✓ | ✓ | ✓ | ✓ | ✓ |
| Composite Asset | ✓ | ✓ | ✓ | ✓ | ✓ |
| External Object | ✓ | ✓ | ✓ | ✓ | ✓ |
| Mapping | ✓ | ✓ | ✓ | ✓ | ✓ |
| Scene Binding | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dashboard | ✓ | ✓ | ✓ | ✓ | ✓ |
| Large Screen | ✓ | ✓ | ✓ | ✓ | ✓ |
| KPI | ✓ | ✓ | ✓ | ✓ | ✓ |
| Alarm | ✓ | ✓ | ✓ | ✓ | ✓ |
| Workflow | ✓ | ✓ | ✓ | ✓ | ✓ |
| WorkOrder | ✓ | ✓ | ✓ | ✓ | ✓ |
| AI Tool | ✓ | ✓ | ✓ | ✓ | ✓ |
| Assembly Recipe | ✓ | ✓ | ✓ | ✓ | ✓ |

---

# 28. Package Directory

```text
dt-lite-smart-park/
├── asset-package.yaml
├── ontology/
├── points/
├── capability/
├── assets/
├── templates/
│   ├── asset-templates.yaml
│   ├── composite-templates.yaml
│   ├── scene-templates.yaml
│   └── assembly-recipes.yaml
├── integration/
│   ├── systems.yaml
│   ├── connectors.yaml
│   ├── external-object-types.yaml
│   ├── mapping-profiles/
│   └── discovery-rules/
├── scene/
│   ├── scene-bindings.yaml
│   ├── bim/
│   ├── gis/
│   └── model-bindings.yaml
├── application/
│   ├── dashboards/
│   ├── large-screens/
│   ├── widgets/
│   ├── kpis.yaml
│   ├── alarms.yaml
│   ├── rules.yaml
│   ├── sops.yaml
│   ├── workflows.yaml
│   └── work-orders.yaml
├── ai/
│   ├── tools.yaml
│   ├── agents.yaml
│   └── prompts/
├── operations/
│   ├── golden-assets.yaml
│   ├── golden-scenarios.yaml
│   ├── assembly-validation.yaml
│   ├── migrations/
│   └── release-gates.yaml
├── schemas/
└── tests/
```

---

# 29. Manifest v4.0

```yaml
package:
  name: "dt-lite-smart-park"
  version: "1.0.0-alpha"
  maturity: "alpha"

  universal_contract:
    id: "dt-lite.universal-asset-assembly"
    version: "1.0.0"
    compatibility: "strict"

  core_platform:
    ref: "dt-lite-core-platform"
    version: ">=4.0.0 <5.0.0"

  contracts:
    - entity/v1
    - asset/v1
    - property/v1
    - relationship/v1
    - scene/v1
    - binding/v1
    - telemetry/v1
    - alarm/v1
    - workflow/v1
    - dashboard/v1
    - assembly/v1

  integrations:
    - bacnet
    - modbus
    - opcua
    - mqtt
    - rest
    - ocpp

  factory_compatibility:
    contract: "dt-lite.universal-asset-assembly@1.0.0"
    status: "required"
```

---

# 30. Release Gates

必须至少具备：

```text
Gate 1  Schema
Gate 2  Ontology
Gate 3  Point / Mapping
Gate 4  Capability
Gate 5  Template
Gate 6  Integration
Gate 7  Scene / BIM / GIS
Gate 8  Dashboard / Large Screen
Gate 9  Workflow / WorkOrder
Gate 10 AI
Gate 11 Zero-Code
Gate 12 Factory Compatibility
```

关键通过条件：

- Schema：0 Error / 0 Warning
- Point：语义定义中 0 个协议地址
- Template：100% 可实例化
- Integration：Discovery / Mapping / Read / Write / Event / Command 按适用范围通过
- BIM：Asset ↔ Model Binding 通过
- Application：标准 Dashboard / Large Screen 全部可渲染
- Workflow：Alarm → WorkOrder → Closure 全链路通过
- AI：Permission / Safety / Audit 全通过
- Zero-Code：GS-10 通过
- Factory Compatibility：Factory Mock Asset 不修改 Universal Contract 即可装配

---

# 31. AgnesCode Engineering Breakdown

## UAA-01 Universal Contract

交付：

```text
universal-asset-assembly-contract.yaml
asset.schema.json
point.schema.json
capability.schema.json
external-object.schema.json
assembly.schema.json
```

验收：Contract schema valid、version frozen、compatibility test passed。

## UAA-02 Asset / Composite

交付：

```text
Asset
AssetType
AssetTemplate
CompositeAsset
CompositeAssetTemplate
Relationship
```

验收：Park Building 与 Factory Production Line 使用同一 Contract 实例化。

## UAA-03 Point / Mapping

验收：同一 Semantic Point 可映射 BACnet / Modbus / OPC UA，且无需修改 Point Definition。

## UAA-04 External Integration

交付 ExternalSystem / ExternalObject / ExternalPoint / ExternalEvent / ExternalCommand / IntegrationProfile。

验收：BMS 与 Factory Mock MES 均可映射，Core Asset Contract 不修改。

## UAA-05 Scene / BIM / GIS / 3D

验收：BIM Object → Asset → Runtime State → 3D Visualization。

## UAA-06 Application

交付：

```text
Dashboard
LargeScreen
Widget
KPI
Alarm
Workflow
SOP
WorkOrder
```

验收 GS-09。

## UAA-07 AI

交付 Tool Contract、Agent Contract、Permission/Safety/Audit Integration。

## UAA-08 Zero-Code Studio

交付：

```text
Asset Designer
Integration Wizard
Scene Composer
Dashboard Designer
Large Screen Designer
Alarm Designer
Workflow Designer
AI Tool Configuration
Assembly Wizard
```

验收 GS-10。

## UAA-09 Golden Scenarios

GS-01 ~ GS-10 全部通过。

## UAA-10 Factory Compatibility

使用 Factory Mock Ontology / Assets / Integration / Scenarios 验证 Universal Contract 不发生修改。

---

# 32. Versioning

## Universal Contract

只有以下情况允许 MAJOR：

```text
对象 Contract Breaking Change
Assembly Semantics Breaking Change
Lifecycle Breaking Change
Compatibility Breaking Change
```

## Industry Package

```text
Smart Park 1.x
Smart Factory 1.x
```

分别演进，但必须声明：

```text
universal_contract: 1.0.0
```

示意：

```text
Universal Asset Assembly Contract 1.0
        │
        ├── Smart Park Package 1.2
        ├── Smart Building Package 1.1
        └── Smart Factory Package 1.0
```

---

# 33. Scope Lock — P0

以下必须冻结：

```text
✓ Five Layer Architecture
✓ Core / Package Boundary
✓ Manifest
✓ Dependency Direction
✓ Naming Convention
✓ Point / Mapping Separation
✓ Capability / Plugin Separation
✓ C0-C4 Safety Model
✓ Asset Template
✓ Composite Asset
✓ External Object Model
✓ Integration Profile
✓ Scene / BIM / GIS Binding
✓ Dashboard Contract
✓ Large Screen Contract
✓ KPI Contract
✓ Alarm Contract
✓ Workflow Contract
✓ WorkOrder Contract
✓ AI Tool Contract
✓ Zero-Code Assembly Contract
✓ Golden Asset
✓ Golden Scenario
✓ Universal Asset Assembly Contract v1.0
✓ Smart Factory Compatibility
```

## 33.1 Absolute Prohibitions

```text
SL-01 禁止未经 Contract Review 修改 Universal Asset Assembly Contract
SL-02 禁止把行业特定字段写入 Universal Contract
SL-03 禁止 Point Semantic 硬编码协议地址
SL-04 禁止 Capability 内嵌算法实现
SL-05 禁止 AI 绕过 Permission / Safety Contract
SL-06 禁止 BIM/GIS Object 成为 Asset 唯一业务身份
SL-07 禁止 Dashboard 与 Large Screen 混为同一对象
SL-08 禁止 External System Object 直接写入 Asset Ontology
SL-09 禁止 Asset Package 修改 Core Platform 数据库
SL-10 禁止以工程脚本替代最终 Zero-Code 产品验收
SL-11 禁止 Smart Factory 重新实现 Assembly Engine
SL-12 Golden Scenario 未通过不得声明 Production Ready
```

---

# 34. Final Architecture

```text
                         DT-Lite Core
                              │
             Universal Asset Assembly Contract 1.0
                              │
                    Assembly Engine / Studio
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
      Asset                 Point              Capability
        │                     │                     │
        └──────────────┬──────┴──────┬──────────────┘
                       │             │
                 Integration    Composite Asset
                       │             │
                       └──────┬──────┘
                              ↓
                       Assembly Context
                              ↓
                       Assembly Recipe
                              ↓
              Validate / Simulate / Publish
                              ↓
          ┌────────────┬──────┴──────┬────────────┐
          ↓            ↓             ↓            ↓
        Scene      Dashboard     Workflow       AI
          ↓            ↓             ↓
       BIM/GIS      Large Screen  WorkOrder
          └────────────┬────────────┘
                       ↓
                Digital Twin Runtime
```

最终行业扩展：

```text
                 Universal Assembly Contract 1.0
                              │
                 ┌────────────┴────────────┐
                 ↓                         ↓
            Smart Park              Smart Factory
                 │                         │
          Park Ontology             Factory Ontology
          Park Assets               Factory Assets
          Park Integration          Factory Integration
          Park Scenarios            Factory Scenarios
                 │                         │
                 └────────────┬────────────┘
                              ↓
                     SAME ASSEMBLY ENGINE
                              ↓
                       SAME ZERO-CODE
                              ↓
                      SAME TWIN RUNTIME
```

---

# 35. Final Statement

DT-Lite V4.0 的目标不是再做一套“智慧园区数字孪生系统”，而是建立：

> **Core Platform + Universal Asset Assembly Contract + Industry Asset Packages + Zero-Code Assembly**

Smart Park 是第一个生产级行业验证器。

Smart Factory 是第二个行业验证器。

Smart Park 必须证明：真实园区可以通过资产模板、外部系统映射、BIM/GIS/3D、Dashboard、大屏、KPI、Alarm、Workflow、WorkOrder、AI 和 Assembly Recipe，在不修改 Core、不写业务代码的情况下完成装配。

Smart Factory 则只增加行业语义和业务资产：

```text
Factory Ontology
Factory Assets
Factory Integration
Factory Scenarios
Factory KPI
Factory Workflow
Factory AI
```

而不重新设计：

```text
Universal Asset Contract
Point Contract
Capability Contract
Composite Asset
External Object
Mapping
Template
Scene
Dashboard
Workflow
AI Tool
Assembly Engine
Zero-Code Studio
```

**这才是 DT-Lite “一个平台、多行业资产包、零代码装配”的最终工程边界。**

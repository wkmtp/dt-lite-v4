# DT-Lite V4.0 Architecture Freeze
## Universal Asset Assembly Contract v1.0 — Frozen Baseline

> **Document ID**: DT-Lite-V4.0-UAA-FREEZE  
> **Version**: 1.0  
> **Status**: FROZEN — Architecture Baseline / Scope Lock Candidate  
> **Primary Industry Sample**: Smart Park  
> **Target**: Production-ready Zero-Code Smart Park Asset Package  
> **Future Compatibility**: Smart Factory (must reuse Contract unchanged)  
> **Date**: 2026-09-12

---

## 0. 文档定位与冻结声明

本文档是 **DT-Lite V4.0 架构冻结基线**。所有后续工程开发（UAA-01 至 UAA-10）必须严格遵循本文档定义的契约、边界、禁令与验收标准。

> **冻结原则**：Universal Asset Assembly Contract v1.0 是最高优先级冻结边界。任何偏离均需通过 Architecture Review Board 评审，输出 Architecture Conflict Report，严禁自行修改 Contract。

---

## 1. 五层架构

| Layer | 名称 | 职责 | 交付物目录 |
|-------|------|------|-----------|
| **L1** | **Ontology** | 语义本体、资产类型、关系、Point Semantic | `ontology/` |
| **L2** | **Capability** | 能力契约、标准接口、Adapter Contract | `capability/` |
| **L3** | **Template** | Asset/Composite/Scene Template、Assembly Recipe | `templates/` |
| **L4** | **Application** | Dashboard、Large Screen、KPI、Alarm、Workflow、WorkOrder、AI | `application/` |
| **L5** | **Operations** | Golden Asset、Golden Scenario、Migration、Release Gate、Compatibility | `operations/` |

### 强制依赖方向（单向、不可逆）

```text
L5 → L4 → L3 → L2 → L1
```

**Package 只消费 Core Platform Contract，不定义 Core 数据库和基础设施。**

---

## 2. Universal Asset Assembly Contract v1.0 (FROZEN)

### 2.1 Contract 对象清单（共 31 个核心对象）

以下对象已冻结为通用协议，**严禁**添加行业特定字段（如 `park-only`、`factory-only`）：

```text
Asset                     AssetType                 AssetTemplate
CompositeAsset            CompositeAssetTemplate    Property
Point                     PointSemantic             PointMapping
Relationship              Capability                CapabilityContract
ExternalSystem            ExternalObject            ExternalPoint
ExternalEvent             ExternalCommand           ExternalRelationship
IntegrationProfile        MappingProfile            Scene
SceneTemplate             SceneBinding              ModelBinding
Dashboard                 DashboardTemplate         LargeScreen
LargeScreenTemplate       Widget                    KPI
Alarm                     Rule                      Workflow
SOP                       WorkOrder                 AITool
AIAgent                   Scenario                  ScenarioTemplate
AssemblyContext           AssemblyRecipe            AssemblyPlan
AssemblyValidation        AssemblyResult            Permission
SafetyContract            AuditRecord               Package
PackageManifest           PackageDependency         PackageVersion
Migration
```

### 2.2 Universal Assembly Contract YAML 定义

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

### 2.3 强制原则（P0 冻结）

| # | 原则 | 违反后果 |
|---|------|----------|
| **P1** | Universal Contract 不得包含行业字段 | Architecture Gate FAIL |
| **P2** | 行业语义仅进入 Industry Ontology / Asset / Capability / Integration / Scenario | Contract 污染 → FAIL |
| **P3** | Smart Factory 必须复用本 Contract，不得重新实现 Assembly Engine | 重复实现 → FAIL |
| **P4** | Point ≠ Protocol Tag；语义与协议映射严格分离 | 协议地址污染语义 → FAIL |
| **P5** | Capability 定义 What，Plugin/Connector 实现 How | 算法内嵌 → FAIL |

---

## 3. Asset Contract (FROZEN)

### 3.1 Asset Identity

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

### 3.2 Asset 必须支持的完整性

```text
Identity          Properties          Points
Relationships     Capabilities        External Bindings
Scene Binding     Dashboard Binding   Alarm Binding
Workflow Binding  AI Tool Binding     Lifecycle
Audit
```

### 3.3 Naming Convention (FROZEN)

```
asset.<domain>.<sub_domain>.<specific_type>
```

| 字段 | 约束 | 示例 |
|------|------|------|
| domain | 固定 `park` / `factory` | `park` |
| sub_domain | 枚举：`energy`、`facility`、`security`、`environment`、`transport`、`operation`、`management`、`spatial` | `facility` |
| specific_type | kebab-case，业务名词单数 | `ahu`、`chiller`、`camera-ptz` |

---

## 4. Composite Asset Contract (FROZEN)

### 4.1 核心机制（Park Building 与 Factory Production Line 共用）

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

### 4.2 必须支持能力

| 能力 | 说明 |
|------|------|
| 子资产 | Tree + Graph 混合拓扑 |
| 父子关系 | `contains`、`feeds`、`controls` 等 |
| 拓扑关系 | 任意业务关系类型 |
| 能力继承 | 子资产能力向上聚合 |
| KPI 聚合 | 场景/楼宇/产线级 KPI 计算 |
| Alarm 聚合 | 子资产告警向上冒泡/收敛 |
| Scene 聚合 | 场景级可视化自动组装 |
| Dashboard 聚合 | 组合仪表盘自动生成 |
| Workflow 聚合 | 跨资产工作流编排 |

---

## 5. Point Semantic Contract (FROZEN)

### 5.1 核心原则

> **Point ≠ Protocol Tag** — Point 只定义语义契约；协议地址由 Mapping Profile 管理。

### 5.2 Point Definition Schema

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
  # 必须支持
  aggregation: [latest, min, max, avg, sum, count, delta, rate]
  retention: required
  availability: required
  quality: required
  calibration: supported
```

### 5.3 Mapping Profile（一对多协议适配）

```text
Semantic Point
      │
 ┌────┼──────┬──────┬──────┐
 ↓    ↓      ↓      ↓      ↓
BACnet Modbus OPC-UA MQTT REST
```

Smart Park v1 至少支持：`BACnet/IP`、`Modbus TCP`、`Modbus RTU`、`OPC UA`、`MQTT`、`HTTP/REST`、`WebSocket`、`OCPP`

---

## 6. External Integration Model (FROZEN)

### 6.1 核心对象

```text
ExternalSystem → ExternalObject → ExternalPoint
ExternalEvent → ExternalCommand → ExternalRelationship
```

### 6.2 Zero-Code 接入流程（业务人员不写代码、不碰 YAML、不懂 K8s）

```text
选择系统 → 选择协议/Connector → 输入连接信息 → 测试连接
    → 自动发现 → 自动分类 → Asset Type Mapping → Point Mapping
    → 验证 → 预览 → 发布
```

### 6.3 支持的外部系统类别（Smart Park v1）

```text
BMS/BAS、EMS、SCADA、CCTV、Access Control、Parking
Fire System、Elevator System、CMMS/FM、ERP
WMS、GIS、BIM、IoT Platform、Weather
Billing、Visitor System
```

---

## 7. BIM / GIS / 3D Contract (FROZEN)

### 7.1 Model Binding

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

### 7.2 支持的模型来源

```text
BIM、GIS、GLB/glTF、CAD-derived、3D Tiles
```

### 7.3 关键边界（P0 冻结）

> **BIM/GIS/3D ModelObject 不能成为 Asset 唯一业务身份** — 3D 是表现层，Twin Asset 才是业务语义事实源。

Asset ↔ Model 必须具备：`model_id`、`object_id`、`external_id`、`asset_id`、`transform`、`visibility`、`LOD`、`state_visualization`、`interaction`、`drill_down`

---

## 8. Scene / Dashboard / LargeScreen Contract (FROZEN)

### 8.1 Scene 类型

```text
Park、Building、Floor、Zone、Equipment、Security、Energy、Parking、Operations、Command Center
```

### 8.2 Dashboard 与 LargeScreen 必须是独立对象（P0 冻结 SL-07）

| 对象 | 定位 | 典型用例 |
|------|------|----------|
| **Dashboard** | 交互式分析、钻取、配置 | 资产详情、能耗分析、运维工作台 |
| **LargeScreen** | 固定分辨率、自动轮播、指挥中心展示 | 园区驾驶舱、能源驾驶舱、安防驾驶舱、领导驾驶舱 |

### 8.3 Widget 类型（最小集）

```text
KPI Card、Trend、Table、Ranking、Alarm List、Map、3D Scene
Video Wall、Energy Flow、Topology、Gauge、Status
Work Order、Statistics、AI Insight
```

---

## 9. KPI / Alarm / Workflow / WorkOrder Contract (FROZEN)

### 9.1 KPI 定义

```yaml
kpi:
  id: "kpi.park.energy.energy-intensity"
  inputs: ["point.park.energy.*.energy-total"]
  formula:
    type: "expression"
    expression: "energy / floor_area"
  aggregation:
    period: "day"
```

**最低要求**：≥20 KPI（总能耗、单位面积能耗、峰值负荷、水耗、能耗成本、新能源占比、HVAC 能效、设备在线率、故障率、告警闭环率、工单及时率、SLA 达成率、停车利用率、充电利用率、环境达标率、视频在线率、门禁在线率、电梯故障率）

### 9.2 Alarm 生命周期（严格状态机）

```text
Detected → Raised → Acknowledged → Diagnosing
    → Dispatched → Resolved → Verified → Closed
```

非法 transition 必须被拒绝。

### 9.3 Workflow / WorkOrder 标准闭环

```text
Event → Alarm → Correlation → Diagnosis → Decision
    → WorkOrder → Dispatch → Execution → Evidence
    → Verification → Closure → KPI
```

---

## 10. Capability Contract (FROZEN)

### 10.1 核心原则

> **Capability 定义 What，Plugin/Connector 实现 How**

### 10.2 Universal Capability Categories

```text
observe、measure、aggregate、diagnose、control、configure
maintain、notify、visualize、query、export
```

### 10.3 Capability Schema

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

## 11. Control Safety Contract C0-C4 (FROZEN)

| Level | Code | 定义 | 审批 | 审计 | 典型场景 |
|-------|------|------|------|------|----------|
| **C0** | `observe` | 只读监测 | 无 | 访问日志 | 仪表盘查询 |
| **C1** | `adjust` | 参数调整、非实时、可逆 | 操作员确认 | 操作日志+参数快照 | 设定温度、修改阈值 |
| **C2** | `command` | 实时开关/启停、可逆 | 双人确认 或 自动校验 | 完整指令链路+回滚 | 启停水泵、充电桩启停 |
| **C3** | `override` | 覆盖自动控制、强制介入 | 值班主管授权+双人确认 | 不可篡改轨迹+事后复盘 | 火灾强制排烟、紧急切断 |
| **C4** | `interlock` | 联锁保护、硬件级强制 | 系统自动、不可人工干预 | 硬件级黑盒记录 | 变压器差动保护、超压泄放 |

### 11.1 Safety Boundary（边界澄清）

```text
DT-Lite
  ↓
Safety Contract (权限、反馈、审计、状态)
  ↓
External Controller / PLC / SIS
  ↓
Hardware Interlock
```

DT-Lite 负责 Contract、权限、反馈、审计和状态；**物理安全链由外部安全控制系统负责**。

---

## 12. AI Contract (FROZEN)

### 12.1 AI Tool / Agent

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
    read: ["telemetry"]

ai_agent:
  id: "agent.park.energy"
  tools: ["tool.park.energy.anomaly-detect"]
```

### 12.2 强制调用链（P0 冻结 SL-05）

```text
AI Agent
    ↓
AI Tool (声明式 I/O Schema)
    ↓
Capability Contract (标准接口)
    ↓
Permission Check (RBAC/ABAC)
    ↓
Safety Contract (C0-C4)
    ↓
Execution (通过 Core Platform API)
    ↓
Audit Record (不可篡改)
```

AI **不得**绕过任何环节直接访问 DB、Connector 或 Core Platform 内部。

---

## 13. Zero-Code Assembly Contract (FROZEN)

### 13.1 Assembly Lifecycle

```text
DRAFT → DISCOVERY → CLASSIFICATION → INSTANTIATION
    → BINDING → VALIDATION → SIMULATION
    → APP_GENERATION → ACCEPTANCE → PUBLISH → RUNTIME
```

### 13.2 Assembly Objects

```text
AssemblyContext → AssemblyRecipe → AssemblyPlan
    → AssemblyStep → AssemblyValidation → AssemblyResult
```

### 13.3 Assembly State Machine（严格）

```text
DRAFT → DISCOVERY → CLASSIFICATION → INSTANTIATION
    → BINDING → VALIDATING → VALIDATED
    → SIMULATING → SIMULATED
    → GENERATING → ACCEPTANCE
    → PUBLISHED → RUNTIME
    → ARCHIVED
```

非法 transition 必须拒绝。必须支持：Retry、Idempotency、Rollback、Audit、Publish Gate。

### 13.4 Zero-Code Studio（业务配置人员 UI）

| 工具 | 功能 |
|------|------|
| Asset Designer | 选择类型 → 填参数 → 选模板 → 绑定空间 → 预览 → 发布 |
| Integration Wizard | 选系统 → 选协议 → 连接测试 → 自动发现 → 自动分类 → 自动 Mapping → 异常确认 → 预览 → 发布 |
| Scene Composer | 选模板 → 选园区/楼宇 → 绑定 BIM/GIS → 选 Asset → 空间绑定 → 3D 预览 → 发布 |
| Dashboard Designer | 选模板 → 绑定 KPI/Widget/Asset Selector → 预览 → 发布 |
| Large Screen Designer | 选模板 → 绑定 Widget/分辨率/行为 → 预览 → 发布 |
| Alarm Designer | 选点位 → 设阈值 → 选严重级 → 关联 SOP/工单 → 预览 → 发布 |
| Workflow Designer | BPMN-like 可视化编排 → 绑定 Capability/SOP → 预览 → 发布 |
| AI Tool Configuration | 选 Tool → 配置 Prompt/权限/安全级 → 测试 → 发布 |
| Assembly Wizard | 向导式完装配全流程 → 一键发布 |

---

## 14. Smart Park Production Baseline (FROZEN)

### 14.1 最低生产基线

| 对象 | 最低数量 | 备注 |
|------|---------|------|
| Asset Types | **≥60** | Spatial(12) + Electrical(9) + HVAC(12) + Water(7) + Lighting(5) + Fire(10) + Security(10) + Parking/Transport(8) + Environment(9) + Elevator(3) + Renewable Energy(4) + Operations(8) |
| Point Semantics | **≥200** | 含 sampling/aggregation/retention/quality |
| Capability Contracts | **≥40** | 覆盖所有 Asset Types |
| Integration / Mapping Templates | **≥30** | BACnet/Modbus/OPC UA/MQTT/REST/OCPP |
| Asset Templates | **≥20** | 含实例化参数 Schema |
| Composite Templates | **≥10** | Building/HVAC/Security/Fire/Water/Parking/Energy/Operations/Command Center |
| Dashboards | **≥8** | Asset/Building/Energy/Equipment/Security/Environment/Operations/Management/AI |
| Large Screens | **≥8** | 园区/能源/设备/安防/环境/停车/运维/领导驾驶舱 |
| KPI | **≥20** | 见 §9.1 |
| Alarm Rules | **≥30** | 覆盖所有关键资产类型 |
| SOP | **≥15** | 标准化故障响应、应急处置、维保作业 |
| WorkOrder Templates | **≥15** | 巡检、维修、应急、改造、校验 |
| AI Tools | **≥8** | 异常检测、能效优化、故障诊断、预测性维护、负荷预测、舒适度优化、安防分析、环境预警 |
| AI Agents | **≥8** | Park Assistant、Energy/Facility/Security/Environment/Parking/Operations/Management Agent |
| Golden Scenarios | **≥10** | GS-01 ~ GS-10 全部通过 |

---

## 15. Standard Composite Assets (FROZEN)

必须提供的标准组合资产：

```text
Park、Building、Building Energy System、Building HVAC System
Building Security System、Building Fire System、Building Water System
Building Parking System、Energy Station、HVAC Station
Security Station、Parking Station、Operations Center、Command Center
```

---

## 16. Golden Assets (FROZEN)

### 16.1 20 个 Golden Assets（v4.0 扩展）

| # | Asset | 验证链路 |
|---|-------|----------|
| GA-01 | Transformer | Ontology → Capability → Template → Point → Mapping → Integration → Scene → Dashboard → Alarm → Workflow → WorkOrder → AI → Assembly → Runtime |
| GA-02 | Switchgear | 同上 |
| GA-03 | Power Meter | 同上 |
| GA-04 | Water Meter | 同上 |
| GA-05 | Chiller | 同上 |
| GA-06 | AHU | 同上 |
| GA-07 | Pump | 同上 |
| GA-08 | Cooling Tower | 同上 |
| GA-09 | Fire Pump | 同上 |
| GA-10 | Fire Panel | 同上 |
| GA-11 | PTZ Camera | 同上 |
| GA-12 | Access Controller | 同上 |
| GA-13 | Elevator | 同上 |
| GA-14 | Parking Gate | 同上 |
| GA-15 | Parking Space | 同上 |
| GA-16 | Charging Pile | 同上 |
| GA-17 | Air Quality Station | 同上 |
| GA-18 | PV Inverter | 同上 |
| GA-19 | BESS | 同上 |
| GA-20 | Building Composite Asset | Composite 验证 |

---

## 17. Golden Scenarios (FROZEN)

### 17.1 GS-01 ~ GS-10 必须全部通过

| ID | 场景 | 核心验证链路 |
|----|------|--------------|
| **GS-01** | Energy Monitoring | EMS/BMS → Discovery → Energy Asset → Mapping → KPI → Dashboard → Alarm → AI |
| **GS-02** | HVAC Operations | BMS → AHU/Chiller → Telemetry → Efficiency KPI → Alarm → SOP → WorkOrder |
| **GS-03** | Security | CCTV + Access → Assets → Event → Alarm → Video Association → WorkOrder |
| **GS-04** | Parking | Parking System → Space/Gate → Vehicle Event → Occupancy KPI → Large Screen |
| **GS-05** | Fire | Fire System → Fire Asset → Alarm → SOP → Evacuation Workflow → Audit |
| **GS-06** | Environment | Sensors → Environment Asset → KPI → Alarm → Notification → Dashboard |
| **GS-07** | Facility Maintenance | Asset → Alarm → Diagnosis → WorkOrder → Dispatch → Evidence → Verification → Closure |
| **GS-08** | BIM/3D | BIM → Object Discovery → Asset Binding → 3D Scene → Runtime State → Drill Down |
| **GS-09** | Command Center | Park → Multiple Systems → Scene → KPI → Alarm → Video → 3D → Large Screen |
| **GS-10** | **Zero-Code End-to-End** | New Project → Import BIM → Connect BMS/EMS/CCTV → Discover → Auto Classify → Instantiate → Bind → Generate Dashboard/Screen/Alarm/SOP → Publish |

> **GS-10 是 Smart Park v4.0 最终零代码验收场景** — 全程无业务代码。

---

## 18. 10 UAA Engineering Tasks (FROZEN)

### 18.1 UAA-01: Universal Contract Schema, Registry & Validator
| 交付物 | 验收标准 |
|--------|----------|
| `universal-asset-assembly-contract.yaml`<br/>`asset.schema.json`<br/>`point.schema.json`<br/>`capability.schema.json`<br/>`external-object.schema.json`<br/>`assembly.schema.json` | Schema valid、version frozen、compatibility test passed |

### 18.2 UAA-02: Asset, Template, CompositeAsset & Relationship
| 交付物 | 验收标准 |
|--------|----------|
| AssetType、AssetTemplate、Asset、CompositeAssetTemplate、CompositeAsset、Property、Relationship | Template 可实例化 Asset、Asset lifecycle PASS、Composite Tree/Graph PASS、Relationship integrity PASS、Building/HVAC 与 ProductionLine/Machine 使用同一 Runtime、无行业专用 Universal Runtime、Asset Gate PASS |

### 18.3 UAA-03: Point, Mapping & Capability
| 交付物 | 验收标准 |
|--------|----------|
| PointSemantic、Point、PointMapping、CapabilityContract、Capability | PointSemantic 无协议地址、Point 无协议地址、PointMapping 保存外部映射、同一 Semantic 支持多协议 (BACnet/Modbus/OPC UA)、Capability I/O Schema 完整、控制能力缺 Permission/Safety 时拒绝发布、Point/Capability Gate PASS |

### 18.4 UAA-04: External Integration & Mapping
| 交付物 | 验收标准 |
|--------|----------|
| ExternalSystem、Connector、ConnectorInstance、ExternalObject、ExternalPoint、ExternalEvent、ExternalCommand、ExternalRelationship、IntegrationProfile、MappingProfile | BMS Mock Discovery PASS、ExternalObject→Asset PASS、ExternalPoint→Point PASS、ExternalEvent→Alarm/Event PASS、ExternalCommand→Capability PASS、ExternalRelationship→Relationship PASS、Factory MES/PLC Mock 可使用同一 Integration Contract、Core Contract 未修改 |

### 18.5 UAA-05: Scene, BIM, GIS & 3D
| 交付物 | 验收标准 |
|--------|----------|
| Model、ModelObject、ModelBinding、Scene、SceneTemplate、SceneBinding | BIM Object 可绑定 Asset、GIS Object 可绑定 Asset、Asset Runtime State 可驱动 3D、一个 Asset 可有多个 ModelBinding、删除 ModelObject 不删除 Asset、Scene 引用 Asset 而非拥有 Asset、Factory Mock 可复用 Scene Contract、Spatial Gate PASS |

### 18.6 UAA-06: Dashboard, LargeScreen, KPI, Alarm, Workflow & WorkOrder
| 交付物 | 验收标准 |
|--------|----------|
| Widget、DashboardTemplate、Dashboard、LargeScreenTemplate、LargeScreen、KPI、Rule、Alarm、SOP、WorkflowTemplate、Workflow、WorkOrderTemplate、WorkOrder | Dashboard 声明式渲染、LargeScreen 独立对象、KPI 计算 PASS、Alarm State Machine PASS、非法 Alarm transition 被拒绝、Workflow lifecycle PASS、WorkOrder lifecycle PASS、Alarm→Workflow→WorkOrder 链路 PASS、GS-09 PASS |

### 18.7 UAA-07: AI, Permission, Safety & Audit
| 交付物 | 验收标准 |
|--------|----------|
| AITool、AIAgent、Permission、SafetyContract、AuditRecord | Read-only Tool 可执行、Mutating Tool 缺 Permission/Safety 时拒绝、Agent 不能绕过 Tool/Capability、Agent 不能直接访问 DB/Connector、Mutating execution 必须 Audit、AI Gate PASS |

### 18.8 UAA-08: Zero-Code Assembly Engine
| 交付物 | 验收标准 |
|--------|----------|
| AssemblyContext、AssemblyRecipe、AssemblyPlan、AssemblyStep、AssemblyValidation、AssemblyResult | Assembly State Machine PASS、非法 transition 被拒绝、Retry/Idempotency/Rollback/Audit PASS、Publish 前 Validation+Acceptance、Runtime 不消费未 Published version、GS-10 所需装配可声明式表达、Zero-Code Gate PASS |

### 18.9 UAA-09: Golden Assets & Golden Scenarios
| 交付物 | 验收标准 |
|--------|----------|
| Golden Validation Framework、GA-01~GA-20、GS-01~GS-10 | Golden Asset 跨层覆盖、GS-01~GS-10 全部 PASS、GS-10 无业务代码、Golden Gate PASS |

### 18.10 UAA-10: Smart Factory Compatibility & Final Freeze
| 交付物 | 验收标准 |
|--------|----------|
| Factory Mock Industry Package (Factory/Workshop/ProductionLine/Machine/Robot/Conveyor/PLC) | Factory Mock 可完整装配、Factory Package 不修改 Universal Contract、Assembly Engine 无 Factory-specific branch、Park regression PASS、Factory shared object contract PASS、Factory Integration/Scenario/AI/Assembly PASS、Universal Contract semantic diff = **ZERO** → **UAA v1.0 FINAL FREEZE** |

---

## 19. Architecture Gates (P0/P1 Definition)

### 19.1 P0 Architecture Gates（任一 FAIL = NOT READY）

```text
[ ] Contract boundary preserved
[ ] Industry neutrality preserved
[ ] Point / Mapping separation preserved
[ ] Capability / Implementation separation preserved
[ ] External isolation preserved
[ ] BIM/GIS identity boundary preserved
[ ] Dashboard / LargeScreen separation preserved
[ ] AI security chain preserved
[ ] Core / Package boundary preserved
[ ] Service / Repository boundary preserved
[ ] No undocumented hard-coded business rule
```

### 19.2 P1 Quality Gates

```text
[ ] Unit Test Coverage ≥ 80% (core services)
[ ] Schema Test 100% valid/invalid fixtures covered
[ ] Reference Test 0 dangling
[ ] Lifecycle Test all states reachable
[ ] State Machine Test all transitions covered
[ ] Integration Test core paths PASS
[ ] Regression Test 0 new failures
[ ] Golden Test GA-01~GA-20 / GS-01~GS-10 PASS
```

---

## 20. Scope Lock — Absolute Prohibitions (SL-01 至 SL-12)

| 编号 | 绝对禁止事项 | 违反检测机制 |
|------|--------------|--------------|
| **SL-01** | 禁止未经 Contract Review 修改 Universal Asset Assembly Contract | CI Schema Diff Gate |
| **SL-02** | 禁止把行业特定字段写入 Universal Contract | Industry Neutrality Validator |
| **SL-03** | 禁止 Point Semantic 硬编码协议地址 | Protocol Isolation Validator |
| **SL-04** | 禁止 Capability 内嵌算法实现 | Capability/Implementation Separation Validator |
| **SL-05** | 禁止 AI 绕过 Permission / Safety Contract | AI Security Chain Validator |
| **SL-06** | 禁止 BIM/GIS Object 成为 Asset 唯一业务身份 | BIM/GIS Identity Boundary Validator |
| **SL-07** | 禁止 Dashboard 与 Large Screen 混为同一对象 | Dashboard/LargeScreen Separation Validator |
| **SL-08** | 禁止 External System Object 直接写入 Asset Ontology | External Isolation Validator |
| **SL-09** | 禁止 Asset Package 修改 Core Platform 数据库 | Core/Package Boundary Validator |
| **SL-10** | 禁止以工程脚本替代最终 Zero-Code 产品验收 | Zero-Code Gate (GS-10) |
| **SL-11** | 禁止 Smart Factory 重新实现 Assembly Engine | Factory Compatibility Test |
| **SL-12** | Golden Scenario 未通过不得声明 Production Ready | Golden Gate |

---

## 21. Contract Boundaries (16 Invariants)

以下 16 条不变量构成架构契约边界，任何变更均为 Breaking Change：

1. **Five Layer Architecture** — L1→L2→L3→L4→L5 单向依赖
2. **Core / Package Boundary** — Package 仅消费 Core Contract，不修改 Core DB
3. **Manifest** — `asset-package.yaml` 单一事实源
4. **Dependency Direction** — 严格向下依赖，无循环
5. **Naming Convention** — `asset.<domain>.<sub_domain>.<specific_type>`
6. **Point / Mapping Separation** — 语义与协议物理隔离
7. **Capability / Plugin Separation** — 契约与实现解耦
8. **C0-C4 Safety Model** — 五级控制安全分级
9. **Asset Template** — 可实例化、可校验、可版本化
10. **Composite Asset** — Tree+Graph、能力继承、聚合
11. **External Object Model** — 外部系统对象映射而非替代本体
12. **Integration Profile** — Discovery/Mapping/Validation 标准化
13. **Scene / BIM / GIS Binding** — 3D 为表现层，Asset 为语义源
14. **Dashboard Contract** — 交互式分析对象
15. **LargeScreen Contract** — 固定分辨率指挥中心展示对象
16. **Universal Asset Assembly Contract v1.0** — 最高优先级冻结边界

---

## 22. Smart Factory Compatibility Matrix (FROZEN)

| Capability | Park | Building | HVAC | Machine | Production Line |
|------------|:---:|:---:|:---:|:---:|:---:|
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

### Factory 只增加，不修改 Contract

```text
Factory Ontology → Factory Assets → Factory Capabilities
    → Factory Integration → Factory Templates → Factory Scenarios
    → Factory KPI → Factory Workflow → Factory AI
```

**共用**：Point Contract、Capability Contract、External Object、Mapping、Composite Asset、Assembly Recipe、Zero-Code Studio、Twin Runtime

---

## 23. Release Gates (12 Gates)

| Gate | 名称 | 通过条件 | 自动化 |
|------|------|----------|--------|
| **Gate 1** | Schema | 0 Error / 0 Warning | ✅ |
| **Gate 2** | Ontology | 类型完整性、关系一致性、JSON-LD Context | ✅ |
| **Gate 3** | Point / Mapping | 语义定义中 0 个协议地址、多协议复用 | ✅ |
| **Gate 4** | Capability | I/O Schema 完整、控制能力需 Permission/Safety | ✅ |
| **Gate 5** | Template | 100% 可实例化、参数 Schema 校验通过 | ✅ |
| **Gate 6** | Integration | Discovery/Mapping/Read/Write/Event/Command 按范围通过 | ✅ |
| **Gate 7** | Scene / BIM / GIS | Asset ↔ Model Binding 通过、BIM/GIS/GLB/3D Tiles 支持 | ✅ |
| **Gate 8** | Dashboard / LargeScreen | 标准 Dashboard/LargeScreen 全部可渲染、独立对象 | ✅ |
| **Gate 9** | Workflow / WorkOrder | Alarm→Workflow→WorkOrder→Closure 全链路通过 | ✅ |
| **Gate 10** | AI | Permission/Safety/Audit 全通过、Agent 不绕过链路 | ✅ |
| **Gate 11** | Zero-Code | **GS-10 通过**（全程无业务代码） | ✅ |
| **Gate 12** | Factory Compatibility | Factory Mock Asset 不修改 Universal Contract 即可装配 | ✅ |

---

## 24. Versioning Strategy

### 24.1 Universal Contract Versioning

**只有以下情况允许 MAJOR 版本升级：**

```text
- 对象 Contract Breaking Change
- Assembly Semantics Breaking Change
- Lifecycle Breaking Change
- Compatibility Breaking Change
```

### 24.2 Industry Package Versioning

```text
Smart Park Package:     1.x (依赖 Universal Contract 1.0)
Smart Building Package: 1.x (依赖 Universal Contract 1.0)
Smart Factory Package:  1.x (依赖 Universal Contract 1.0)
```

### 24.3 版本声明示例

```yaml
package:
  name: "dt-lite-smart-park"
  version: "1.2.0"
  universal_contract:
    id: "dt-lite.universal-asset-assembly"
    version: "1.0.0"
    compatibility: "strict"
```

---

## 25. Package Directory Structure (FROZEN)

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

## 26. Manifest v4.0 (FROZEN)

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

## 27. Final Architecture Diagram

```text
                         DT-Lite Core Platform
                              │
             Universal Asset Assembly Contract v1.0 (FROZEN)
                              │
                    Assembly Engine / Zero-Code Studio
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
              Validate / Simulate / Publish (Gates)
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

### 最终行业扩展模式

```text
                 Universal Assembly Contract 1.0 (FROZEN)
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
                       SAME ZERO-CODE STUDIO
                              ↓
                      SAME TWIN RUNTIME
```

---

## 28. 最终声明

DT-Lite V4.0 的目标不是再做一套"智慧园区数字孪生系统"，而是建立：

> **Core Platform + Universal Asset Assembly Contract + Industry Asset Packages + Zero-Code Assembly**

| 验证器 | 目标 |
|--------|------|
| **Smart Park** | 第一个生产级行业验证器 — 证明真实园区可通过模板、映射、BIM/3D、Dashboard、大屏、KPI、Alarm、Workflow、WorkOrder、AI 和 Assembly Recipe，**不修改 Core、不写业务代码**完成装配 |
| **Smart Factory** | 第二个行业验证器 — 仅增加行业语义和业务资产，复用所有 Universal Contract、Assembly Engine、Zero-Code Studio、Twin Runtime |

**这才是 DT-Lite "一个平台、多行业资产包、零代码装配" 的最终工程边界。**

---

## 附录 A：Architecture Conflict Report Template

当发现架构冲突时，必须输出：

```markdown
# Architecture Conflict Report

## Conflict ID
UAA-{task}-{YYYYMMDD}-{NNN}

## Conflicting Component
[Component Name / Contract Section]

## Current Behavior
[What currently happens]

## Expected Behavior (per Frozen Contract)
[What the frozen contract requires]

## Proposed Resolution
[ ] Modify Implementation to match Contract
[ ] Request Contract Review (Architecture Review Board)

## Impact Analysis
- Affected UAA Tasks:
- Affected Tests:
- Migration Required:

## Decision
[ ] ACCEPT — Implementation fixed
[ ] ESCALATE — Contract Review Required
[ ] REJECT — Violates Frozen Baseline

## Sign-off
Architecture Review Board: _______________ Date: _______________
```

---

## 附录 B：引用文档映射

| 本文档章节 | 源文档 | 源文档位置 |
|------------|--------|------------|
| §1-2 | v4.0 Spec | §1, §2 |
| §3 | v4.0 Spec | §3 |
| §4 | v4.0 Spec | §5 |
| §5 | v4.0 Spec | §6 |
| §6 | v4.0 Spec | §7-9 |
| §7 | v4.0 Spec | §10 |
| §8 | v4.0 Spec | §11-13 |
| §9 | v4.0 Spec | §14-16 |
| §10 | v4.0 Spec | §17 |
| §11 | v4.0 Spec | §18 |
| §12 | v4.0 Spec | §19 |
| §13 | v4.0 Spec | §20 |
| §14 | v4.0 Spec | §22 |
| §15 | v4.0 Spec | §23 |
| §16 | v4.0 Spec | §24 |
| §17 | v4.0 Spec | §25 |
| §18 | UAA-01~10 | 各文件 §1, §6 |
| §19 | UAA-01~10 | 各文件 §7 |
| §20 | v4.0 Spec | §33.1 |
| §21 | v4.0 Spec | §33 |
| §22 | v4.0 Spec | §26-27 |
| §23 | v4.0 Spec | §30 |
| §24 | v4.0 Spec | §32 |
| §25 | v4.0 Spec | §28 |
| §26 | v4.0 Spec | §29 |

---

## 附录 C：变更历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 1.0 | 2026-09-12 | **FROZEN** | 基于 v4.0 Spec 与 UAA-01~10 编译生成的架构冻结基线 |

---

> **文档状态**：**FROZEN** — Architecture Baseline / Scope Lock Candidate  
> **下一步**：启动 UAA-01 至 UAA-10 严格工程执行，每任务必须通过 Pre-Implementation Audit、Design Lock、Architecture Gate、Final Report 全流程。  
> **严禁**：在未通过 UAA-10 Final Freeze 前声称任何组件 Production Ready。
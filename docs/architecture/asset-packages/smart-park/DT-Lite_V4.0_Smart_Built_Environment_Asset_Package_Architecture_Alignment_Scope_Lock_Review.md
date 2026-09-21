# DT-Lite V4.0 Smart Built Environment Asset Package
# Architecture Alignment & Scope Lock Review

**文档类型**：Architecture Alignment & Scope Lock Review  
**版本**：v1.0  
**状态**：Scope Lock 前置审计基线  
**适用平台**：DT-Lite Core V4.0  
**评审对象**：Smart Built Environment / Smart Park Industry Asset Package Specification v1.0  
**评审目标**：在进入大规模行业资产包工程实现前，完成平台架构对齐、边界确认、接口契约审计与 Phase 2 Scope Lock。  
**评审原则**：先审计、后冻结；先确认 Core 能力、再实现行业扩展；禁止通过 Asset Package 反向污染 DT-Lite Core 架构。

---

## 1. 文档目的

本文件用于对《DT-Lite V4.0 Smart Park Industry Asset Package Specification v1.0》进行工程化架构对齐审计，并将其从“行业能力设计蓝图”进一步约束为可安装、可验证、可升级、可治理的 DT-Lite Asset Package。

本评审不以增加资产数量为主要目标，而以以下目标为核心：

1. 明确 DT-Lite Core 与 Industry Asset Package 的边界。
2. 确认 L1 Ontology、L2 Capability、L3 Template、L4 Application、L5 Operations 的正式契约。
3. 建立 Asset Package Manifest 与 Dependency Graph。
4. 建立 Asset / Point / Capability / Adapter / Template / Application / Operations 的完整引用链。
5. 将“Zero-Code”从工程人员 YAML/Helm 配置提升为产品级零代码安装与配置能力。
6. 确保真实设备控制能力具有安全等级、权限、审批、审计与防误操作机制。
7. 建立资产包版本、依赖、升级、迁移与兼容性规则。
8. 建立 Golden Asset 作为跨层端到端工程验收标准。
9. 明确 Phase 2 行业场景开发范围，避免七个场景并行开发造成架构分叉。
10. 在 Scope Lock 后形成 AgnesCode 可执行的工程实施边界。

---

# 2. 评审结论摘要

## 2.1 总体结论

当前 Asset Package Specification 的总体架构方向正确，五层模型已经具备行业资产产品化的基础：

```text
L5 Operations
    ↑
L4 Application
    ↑
L3 Template
    ↑
L2 Capability
    ↑
L1 Ontology
```

但当前版本更接近：

> 行业知识模型 + 产品功能目录 + 工程实施计划

尚未完全达到：

> 可执行、可安装、可验证、可升级、可治理的 Production Asset Package Contract

因此：

**评审结论：CONDITIONAL PASS / 有条件通过，不建议直接进入七大场景全面工程实现。**

必须先完成本文件定义的 P0 架构对齐项，并经过 Scope Lock。

---

# 3. 当前成熟度评估

| 维度 | 当前评价 | 结论 |
|---|---:|---|
| 总体架构 | 9/10 | PASS |
| 五层模型 | 8.5/10 | PASS |
| 行业覆盖 | 9/10 | PASS |
| Ontology | 7.5/10 | NEED ALIGNMENT |
| Capability | 7/10 | NEED ALIGNMENT |
| Template | 7/10 | NEED ALIGNMENT |
| Application | 7/10 | NEED ALIGNMENT |
| Operations | 7.5/10 | NEED ALIGNMENT |
| Zero-Code | 5.5/10 | P0 |
| Package Manifest | 5/10 | P0 |
| Dependency Governance | 5/10 | P0 |
| Protocol Binding | 6/10 | P1 |
| Security / Control Safety | 6.5/10 | P0 |
| Version / Migration | 6/10 | P0 |
| QA / Validation | 7/10 | P1 |
| AI Integration | 5/10 | P1 |
| Productization | 7/10 | NEED ALIGNMENT |

---

# 4. 评审基线

原规格已经定义以下五层架构：

```text
L5 Operations
运维包：
告警规则库、SOP、巡检计划、应急预案、能耗基准、KPI

L4 Application
场景应用包：
场景模板、低代码页面、组件库、仪表盘、报表、移动端

L3 Template
模板包：
资产模板、空间模板、场景模板、工单模板、报表模板、大屏模板

L2 Capability
能力包：
标准能力、协议适配器映射、计算规则、联动规则、告警策略

L1 Ontology
本体包：
资产类型、属性、关系、空间层级、分类体系、枚举字典
```

该结构作为本次评审的基础，不予推翻。

---

# 5. P0 — 必须在 Scope Lock 前解决的问题

## P0-01 Core 与 Asset Package 边界

### 问题

当前规格同时涉及：

- 行业 Ontology
- Capability
- Template
- Application
- Operations
- Kubernetes
- PostgreSQL
- TimescaleDB
- Redis
- EMQX
- MinIO
- Neo4j
- Helm

如果 Asset Package 自身负责部署全部基础设施，将造成：

> Asset Package 反向绑定 Platform Infrastructure。

### Scope Lock 决策

必须明确：

```text
DT-Lite Core
    ├── Platform Runtime
    ├── Ontology Runtime
    ├── Capability Runtime
    ├── Template Runtime
    ├── Application Runtime
    ├── Operations Runtime
    └── Package Runtime

Industry Asset Package
    ├── Ontology Extension
    ├── Capability Extension
    ├── Template
    ├── Application
    └── Operations
```

**Asset Package 依赖 Core，不得携带或重建 Core。**

---

# 6. P0-02 正式 Asset Package Manifest

必须新增：

```text
asset-package.yaml
```

建议基线：

```yaml
apiVersion: dtlite.io/v1
kind: AssetPackage

metadata:
  id: smart-built-environment
  name: Smart Built Environment
  version: 1.0.0

spec:
  platform:
    minVersion: "4.18.0"
    maxVersion: "<5.0.0"

  ontology:
    version: "1.0.0"

  capabilities:
    version: "1.0.0"

  templates:
    version: "1.0.0"

  applications:
    version: "1.0.0"

  operations:
    version: "1.0.0"

  dependencies:
    - package: dtlite-core
      version: ">=4.18.0"

  scenarios:
    - community
    - mall
    - school
    - hospital
    - logistics
    - datacenter
    - industrial_park
```

Manifest 必须成为资产包的唯一正式身份入口。

---

# 7. P0-03 Dependency Graph

必须正式定义跨层依赖：

```text
Asset
  ↓
Point
  ↓
Capability
  ↓
Template
  ↓
Scene / Application
  ↓
Alarm
  ↓
SOP
  ↓
WorkOrder
  ↓
Verification
  ↓
KPI
```

典型链路：

```text
asset.dc.ups
    ↓
telemetry.battery_soh
    ↓
cap.common.telemetry.read
    ↓
tmpl.dc.ups
    ↓
scene.dc.infrastructure
    ↓
ALM-DC-002
    ↓
SOP-DC-002
    ↓
WorkOrder
```

必须支持：

- dependency validation
- missing reference detection
- orphan detection
- circular dependency detection
- version compatibility validation

---

# 8. P0-04 Naming Convention 冻结

当前规格存在两种形式：

```text
asset.power.transformer
```

以及：

```text
asset.common.power.transformer
```

必须冻结唯一规则。

推荐：

```text
asset.<domain>.<sub_domain>.<specific_type>
```

示例：

```text
asset.common.power.transformer
asset.hospital.medical.icu_monitor
asset.park.energy.steam_boiler
```

Capability 同理建议：

```text
cap.<domain>.<subdomain>.<capability>
```

例如：

```text
cap.common.telemetry.read
cap.hvac.cooling.optimize
cap.hospital.asset.tracking
cap.park.energy.multi_energy_synergy
```

一旦 Scope Lock，禁止在不同 Squad 中自行改变命名。

---

# 9. P0-05 资产数量与交付状态必须分离

原规格规划规模与实际展开定义存在差异。

必须统一采用：

```text
planned
draft
implemented
validated
production
deprecated
```

例如：

```yaml
catalog:
  asset_types:
    planned: 97
    implemented: 20
    validated: 15
    production: 10
```

告警与 SOP 同理。

禁止将：

> 规划数量

描述为：

> 已交付数量。

---

# 10. P0-06 Zero-Code 定义重新冻结

当前 YAML + Helm 更接近：

> Engineering Zero-Code

真正产品级 Zero-Code 必须做到：

```text
选择行业包
    ↓
选择场景
    ↓
选择模板
    ↓
填写业务参数
    ↓
自动生成
    ├── Assets
    ├── Points
    ├── Relations
    ├── Dashboard
    ├── Alarm
    ├── SOP
    └── Operations
```

最终用户不应该直接修改：

- Helm
- CRD
- PostgreSQL
- TimescaleDB
- EMQX
- Neo4j
- Redis

这些属于 Platform Runtime。

---

# 11. P0-07 Control Safety Contract

任何可写 Capability 都必须经过安全模型。

建议定义：

```text
C0 Read
C1 Parameter Write
C2 Start / Stop
C3 Safety Related Control
C4 Emergency Control
```

对应：

```text
Capability
    ↓
Control Policy
    ↓
Role
    ↓
Permission
    ↓
Approval
    ↓
Execution
    ↓
Audit
```

C3/C4 必须支持：

- 强制审批
- 双人复核
- 操作审计
- 防误操作
- 超时取消
- 回执确认
- 执行结果验证

---

# 12. P0-08 Scope Boundary

Asset Package 不应成为行业 ERP/HIS/WMS/POS/OA 的替代品。

DT-Lite 负责：

```text
Asset
Space
IoT
Digital Twin
Telemetry
Event
Alarm
Workflow
Visualization
Operational Intelligence
```

外部业务系统负责：

```text
ERP
HIS
WMS
MES
POS
HR
Finance
OA
```

通过 Integration Layer 连接。

---

# 13. L1 Ontology Contract

L1 必须正式定义：

```text
Identity
Location
Lifecycle
Telemetry
Control
Maintenance
Compliance
Provenance
```

建议：

```yaml
asset:
  identity:
    id:
    externalId:
    serialNumber:
    model:
    manufacturer:

  location:
    siteId:
    buildingId:
    floorId:
    spaceId:

  lifecycle:
    commissionedAt:
    warranty:
    status:
    retiredAt:

  telemetry:
    value:
    unit:
    quality:
    timestamp:
    source:

  control:
    writable:
    safetyLevel:
    permission:

  maintenance:
    lastMaintenance:
    nextMaintenance:
    cycle:

  compliance:
    certificate:
    inspection:

  provenance:
    adapter:
    gatewayId:
    sourceAddress:
```

---

# 14. P1 — Semantic Point Model

必须新增 Point Model。

```yaml
point:
  id: transformer.oil_temperature
  semanticType: Temperature
  datatype: float
  unit: degC
  writable: false
  qualityRequired: true
  sampleInterval: 5s
```

Point 是：

> Asset 与 Protocol Adapter 之间的语义桥梁。

没有 Point Semantic Model，BACnet / Modbus / OPC-UA / MQTT 无法真正实现协议解耦。

---

# 15. P1 — Protocol Binding Contract

必须从：

```text
assetType → protocol
```

进一步下沉为：

```text
Asset
 ↓
Point
 ↓
Protocol
 ↓
Adapter
 ↓
Address
```

例如：

```yaml
assetType: asset.mall.chiller

points:
  - semantic: supply_water_temperature
    protocol: bacnet
    objectType: analog-input
    objectInstance: 12

  - semantic: power
    protocol: modbus
    function: 03
    register: 40120
```

---

# 16. L2 Capability Contract

Capability 必须定义：

```text
id
version
input
output
precondition
permission
safetyLevel
timeout
idempotency
sideEffects
```

例如：

```yaml
capability:
  id: cap.hvac.cooling.optimize
  version: 1.0.0

  input:
    targetTemperature: number

  output:
    optimizedSetpoint: number

  permission:
    level: C2

  safety:
    approvalRequired: true
```

---

# 17. Capability 与 Algorithm 分离

必须避免：

```text
Capability = Algorithm
```

正确模型：

```text
Capability
    ↓
Algorithm Provider
    ├── Rule Based
    ├── PID
    ├── MPC
    ├── ML
    └── RL
```

例如：

```text
cap.hvac.cooling.optimize
        ↓
algorithm.mpc.v1
```

这样未来可以更换算法而不改变上层业务契约。

---

# 18. L3 Template Contract

Template 必须支持：

```text
Parameters
Defaults
Constraints
Bindings
Derived Properties
Rules
UI
Lifecycle
```

例如：

```yaml
template:
  id: tmpl.hvac.ahu

  parameters:
    coolingCapacity:
      type: number
      required: true

    controlMode:
      type: enum
      values:
        - auto
        - manual

  bindings:
    capabilities:
      - cap.common.telemetry.read
      - cap.hvac.cooling.optimize
```

---

# 19. L4 Application Contract

Application 应采用三层组件体系：

```text
Core UI
    ↓
Industry UI
    ↓
Scenario UI
```

Core：

```text
AssetTree
KPI
Trend
Alarm
Map
Topology
```

Industry：

```text
HVAC
Elevator
UPS
AGV
Energy
```

Scenario：

```text
Hospital ICU
Mall Retail
School
Industrial Park
```

禁止各行业 Squad 重复建设相同基础组件。

---

# 20. 3D / BIM / GIS Binding

资产模型必须支持：

```yaml
model:
  format: glb
  assetUrl:
  version:
  checksum:
  lod:
  boundingBox:
  coordinateSystem:
  origin:
  scale:

  semanticBindings:
    - nodeId:
      assetId:
```

需要建立：

```text
Asset
 ↕
BIM Element
 ↕
GLB Node
 ↕
GIS Geometry
```

---

# 21. L5 Operations 闭环模型

L5 不应只是规则库。

标准闭环：

```text
Event
 ↓
Alarm
 ↓
Diagnosis
 ↓
SOP
 ↓
WorkOrder
 ↓
Execution
 ↓
Verification
 ↓
Closure
 ↓
KPI
```

---

# 22. Alarm Contract

建议正式定义：

```yaml
alarmRule:
  id:
  version:
  assetType:
  point:
  expression:
  severity:
  debounce:
  hysteresis:
  suppression:
  escalation:
  sop:
  workOrder:
  acknowledgment:
  autoRecovery:
```

必须支持：

- debounce
- hysteresis
- suppression
- escalation
- acknowledgement
- recovery
- duplicate suppression

---

# 23. Alarm Severity

P0-P3 可以保留，但不应直接作为唯一风险模型。

建议：

```text
Impact
Probability
Urgency
Confidence
        ↓
Risk Score
        ↓
P0-P3
```

不同产业可通过 Profile 定义风险映射。

---

# 24. SOP Workflow 化

SOP 应从静态文档升级为可执行 Workflow：

```yaml
sop:
  id: SOP-DC-002

  steps:
    - id: receive
      action: acknowledge_alarm

    - id: inspect
      action: inspect_asset

    - id: isolate
      action: isolate_equipment

    - id: repair
      action: create_workorder

    - id: verify
      action: verify_recovery

    - id: close
      action: close_incident
```

---

# 25. Emergency Workflow

应急预案应具备：

```text
Trigger
 ↓
Incident
 ↓
Command Structure
 ↓
Tasks
 ↓
Communication
 ↓
Resources
 ↓
Execution
 ↓
Verification
 ↓
Report
```

---

# 26. Telemetry Profile

建议增加：

```yaml
telemetryProfile:
  realtime:
    interval: 5s

  standard:
    interval: 30s

  energy:
    interval: 60s

  event:
    mode: event-driven
```

并定义：

```text
raw retention
5-minute retention
hourly retention
daily retention
```

---

# 27. Data Volume Model

必须在 Asset Package 中定义：

```text
Asset Count
Point Count
Sampling Frequency
Telemetry/sec
Alarm/sec
Retention
Aggregation
Storage Policy
```

性能测试至少覆盖：

```text
1,000 assets
10,000 assets
50,000 assets
100,000 assets
```

---

# 28. Benchmark / Baseline 治理

能耗基准不能简单使用固定数字。

应考虑：

```text
Building Type
Climate Zone
Area
Operating Hours
Occupancy
Energy Source
```

`baselineAutoCalibration` 不建议默认开启。

推荐：

```yaml
baseline:
  mode: governed
  autoCalibration: false
  minObservationDays: 30
  approvalRequired: true
```

---

# 29. 安全与合规边界

Asset Package 可以提供：

```text
Compliance Mapping
Audit Rules
Data Classification
Retention Policy
Control Policy
```

但不得把：

> “支持合规”

等同于：

> “安装资产包后自动满足全部法规要求”。

所有法规映射必须标注：

```text
Reference
Requirement
System Control
Evidence
Validation Status
```

---

# 30. Package Versioning

必须定义：

```text
Package Version
Ontology Version
Capability Version
Template Version
Application Version
Operations Version
```

推荐采用 SemVer：

```text
MAJOR.MINOR.PATCH
```

规则：

### MAJOR

破坏性 Ontology / API / Capability Contract 变化。

### MINOR

向后兼容的新资产、新能力、新模板。

### PATCH

Bug Fix、规则修复、文档修复。

---

# 31. Upgrade / Migration Contract

必须支持：

```text
Installed Package
      ↓
Compatibility Check
      ↓
Migration Plan
      ↓
Backup
      ↓
Upgrade
      ↓
Validation
      ↓
Rollback
```

升级不得直接覆盖生产资产实例。

---

# 32. Package Signature / Supply Chain

Asset Package 必须支持：

```text
Manifest
Checksum
Signature
SBOM
Dependency Lock
Vulnerability Scan
```

建议：

```text
Package
 ↓
SBOM
 ↓
Signature
 ↓
Verification
 ↓
Install
```

---

# 33. QA Gate 扩展

当前 QA Gate 基础正确，但需要增加：

```text
Schema Validation
Reference Validation
Dependency Validation
Cycle Detection
Semantic Validation
Permission Validation
Safety Validation
Orphan Detection
Upgrade Compatibility
Performance Validation
Security Scan
```

---

# 34. Golden Asset 策略

不建议先追求 100 个资产全部完善。

应先建立 10～20 个 Golden Assets。

例如：

```text
Transformer
Power Meter
Environmental Sensor
Camera
Access Controller
AHU
Chiller
Elevator
UPS
Boiler
Energy Gateway
```

每一个 Golden Asset 必须贯通：

```text
Ontology
 ↓
Point
 ↓
Capability
 ↓
Adapter
 ↓
Template
 ↓
3D
 ↓
Application
 ↓
Alarm
 ↓
SOP
 ↓
Inspection
 ↓
WorkOrder
 ↓
KPI
 ↓
AI Agent
```

---

# 35. Golden Path Acceptance

建议至少完成一个：

```text
Chiller Golden Path
```

完整验证：

```text
设备接入
 ↓
自动发现
 ↓
Asset 创建
 ↓
Point Mapping
 ↓
Telemetry
 ↓
3D 映射
 ↓
Dashboard
 ↓
Alarm
 ↓
SOP
 ↓
WorkOrder
 ↓
Recovery
 ↓
KPI
```

只有 Golden Path 成功，才进入七大场景规模化扩展。

---

# 36. AI Agent Layer

当前五层可以保留，并建议增加：

```text
L6 Intelligence
```

结构：

```text
L6 Intelligence
    ├── AI Agent
    ├── RCA
    ├── Prediction
    ├── Optimization
    ├── Natural Language
    └── Decision Support
```

AI Agent 应通过标准 Tool Contract 使用 DT-Lite：

```text
get_asset
get_telemetry
get_alarm
get_relationship
run_diagnosis
run_capability
get_sop
create_workorder
generate_report
```

AI Agent 不应绕过平台权限直接控制设备。

---

# 37. Industry Extension Model

建议最终采用：

```text
Core Ontology
    ↓
Industry Extension
    ↓
Scenario Profile
```

而不是：

```text
Hospital HVAC
Mall HVAC
School HVAC
Park HVAC
```

应最大限度复用：

```text
Power
HVAC
Water
Fire
Security
Network
Space
Common Equipment
```

---

# 38. Scenario Activation

默认不应加载全部行业场景。

推荐：

```yaml
enabledScenarios: []
```

用户安装时选择：

```text
Community
Mall
School
Hospital
Logistics
Data Center
Industrial Park
```

仅加载所选 Profile。

---

# 39. Infrastructure Dependency Policy

建议分为：

## Core

```text
PostgreSQL
Redis
Object Storage
MQTT
```

## Optional

```text
TimescaleDB
Neo4j
Kafka
```

## Scenario-specific

```text
OPC-UA
BACnet
SNMP
HL7/FHIR
GIS
```

Asset Package 不应强制所有用户安装全部基础设施。

---

# 40. Integration Layer

必须形成：

```text
                 DT-Lite
                    │
       ┌────────────┴────────────┐
       │                         │
 Asset Package              Integration
       │                         │
 Ontology                 ERP / HIS / WMS
 Capability               MES / POS / OA
 Template                 SCADA / BMS
 Operations
```

Asset Package 负责孪生能力。

Integration Layer 负责企业系统连接。

---

# 41. 多 Squad 开发治理

不建议七个 Squad 完全独立定义标准。

建议增加：

```text
Architecture Governance Squad
```

负责：

```text
Ontology
Naming
Schema
Capability Contract
Versioning
Dependency
Security
QA
Manifest
```

七个行业 Squad 负责：

```text
Industry Extension
Scenario
Application
Operations
```

---

# 42. Phase 2 Scope Lock

Phase 2 不应直接定义为：

> 七个场景全部开发。

而应分为：

## Stage A — Golden Foundation

完成：

- Manifest
- Dependency Graph
- Golden Assets
- Point Model
- Capability Contract
- Adapter Binding
- Template Contract
- Alarm Contract
- SOP Workflow

## Stage B — Common Asset Pack

完成：

- Power
- HVAC
- Water
- Fire
- Security
- Space
- Energy

## Stage C — Industry Extensions

依次进入：

1. 产业园区
2. 数据中心
3. 商场
4. 学校
5. 医院
6. 物流
7. 社区

具体顺序应以 Core 复用率和业务价值为依据，而不是七组完全平行开发。

---

# 43. Scope Lock 禁止事项

Scope Lock 后，禁止：

1. 行业 Squad 私自修改 Core API。
2. 行业 Squad 私自修改 Ontology Naming。
3. 行业包直接创建 Platform Infrastructure。
4. Asset Package 内嵌独立数据库。
5. Asset Package 绕过权限执行设备控制。
6. 未定义 Manifest 的内容进入生产包。
7. 未通过 Schema Validation 的资产进入 Release。
8. 未绑定 SOP 的 P0 Alarm 进入 Production。
9. 未定义版本兼容性的 Package 进入 Production。
10. 用规划数量冒充交付数量。
11. 为单个行业重复创建 Core UI。
12. 为行业业务系统功能无限扩张 Asset Package 边界。

---

# 44. Release Gate

Asset Package Release 必须满足：

```text
[ ] Manifest valid
[ ] Version valid
[ ] Dependency valid
[ ] Naming valid
[ ] Schema valid
[ ] Point model valid
[ ] Capability contract valid
[ ] Adapter mapping valid
[ ] Template valid
[ ] Application reference valid
[ ] Alarm syntax valid
[ ] P0/P1 alarm has SOP
[ ] SOP executable
[ ] Permission validated
[ ] Safety validated
[ ] 3D semantic binding valid
[ ] No orphan objects
[ ] No circular dependencies
[ ] Upgrade compatibility verified
[ ] Security scan passed
[ ] SBOM generated
[ ] Package signature verified
[ ] Golden Asset tests passed
[ ] Performance tests passed
```

---

# 45. Acceptance Metrics

建议建立以下工程指标：

| 指标 | 目标 |
|---|---|
| Package install | ≤ 5 min（不含 Core） |
| Scenario activation | ≤ 5 min |
| 1000 assets provisioning | 定义并验证 |
| 10k assets | 性能基线 |
| 50k assets | 扩展性基线 |
| 100k assets | 极限基线 |
| Schema validation | 100% |
| Orphan reference | 0 |
| Circular dependency | 0 |
| P0 alarm without SOP | 0 |
| Unauthorized control | 0 |
| Package signature failure | 100% reject |
| Migration rollback | 可验证 |
| Golden Asset coverage | 100% |

---

# 46. 文件结构建议

最终 Asset Package 建议采用：

```text
smart-built-environment/
│
├── asset-package.yaml
├── README.md
├── CHANGELOG.md
├── LICENSE
│
├── ontology/
│   ├── assets/
│   ├── spaces/
│   ├── relationships/
│   ├── points/
│   └── dictionaries/
│
├── capabilities/
│   ├── common/
│   ├── hvac/
│   ├── energy/
│   └── industry/
│
├── bindings/
│   ├── bacnet/
│   ├── modbus/
│   ├── mqtt/
│   └── opcua/
│
├── templates/
│   ├── assets/
│   ├── spaces/
│   ├── scenes/
│   └── workflows/
│
├── applications/
│   ├── components/
│   ├── dashboards/
│   ├── scenes/
│   └── reports/
│
├── operations/
│   ├── alarms/
│   ├── sops/
│   ├── inspections/
│   ├── emergency/
│   └── kpi/
│
├── models/
│   ├── glb/
│   └── semantic-bindings/
│
├── scenarios/
│   ├── community/
│   ├── mall/
│   ├── school/
│   ├── hospital/
│   ├── logistics/
│   ├── datacenter/
│   └── industrial-park/
│
├── tests/
│   ├── schema/
│   ├── references/
│   ├── integration/
│   ├── golden-assets/
│   ├── security/
│   └── performance/
│
└── docs/
    ├── architecture/
    ├── user/
    └── compliance/
```

---

# 47. AgnesCode 执行规则

AgnesCode 在收到本文件后，不得立即进入大规模行业编码。

必须按照以下顺序执行：

```text
Step 1
读取当前 DT-Lite V4.0 Core 实际代码

Step 2
扫描已有：
Ontology Service
Capability Service
Template Service
Application Service
Operations Service
Deployment Service
Provisioning Service
Adapter Layer
Telemetry Pipeline
AI Agent

Step 3
建立：
Implemented / Partial / Missing Matrix

Step 4
逐项对照本 Review

Step 5
识别 Core Modification Required

Step 6
识别 Asset Package Only

Step 7
识别 Architecture Conflict

Step 8
提出最小 Core Change Set

Step 9
形成 Scope Lock Report

Step 10
获得 Scope Lock 后再进入 Engineering Implementation
```

---

# 48. AgnesCode 不得假设

AgnesCode 不得假设：

- SPEC 中描述的功能已经在 Core 中存在。
- YAML 示例就是正式 API。
- Helm values 就是 Asset Package Contract。
- 规划数量等于已实现数量。
- 所有场景都应该默认安装。
- 所有 Capability 都可以写入设备。
- 所有行业功能都属于 DT-Lite Core。
- 所有法规映射都等同于系统合规。
- 所有 KPI 数字都是系统保证值。

所有结论必须基于当前代码实际证据。

---

# 49. Architecture Alignment Matrix

AgnesCode 必须最终输出：

| Requirement | Core Existing | Partial | Missing | Asset Package Only | Core Change Required | Priority |
|---|---|---|---|---|---|---|
| Manifest | | | | | | P0 |
| Dependency Graph | | | | | | P0 |
| Ontology Contract | | | | | | P0 |
| Point Model | | | | | | P1 |
| Capability Contract | | | | | | P0 |
| Adapter Binding | | | | | | P1 |
| Template Contract | | | | | | P1 |
| Application Contract | | | | | | P1 |
| Alarm Contract | | | | | | P1 |
| SOP Workflow | | | | | | P1 |
| Control Safety | | | | | | P0 |
| Versioning | | | | | | P0 |
| Migration | | | | | | P0 |
| 3D Semantic Binding | | | | | | P1 |
| AI Agent Contract | | | | | | P1 |
| QA Gate | | | | | | P1 |

---

# 50. Scope Lock 输出物

Architecture Alignment 阶段必须产生以下文件：

```text
01_ARCHITECTURE_ALIGNMENT_REPORT.md
02_CORE_CHANGESET.md
03_ASSET_PACKAGE_CONTRACT.md
04_MANIFEST_SCHEMA.yaml
05_DEPENDENCY_GRAPH.md
06_GOLDEN_ASSET_SPEC.md
07_SCOPE_LOCK.md
08_PHASE2_IMPLEMENTATION_PLAN.md
```

其中：

> `07_SCOPE_LOCK.md`

是进入工程实现的唯一批准依据。

---

# 51. 最终 Scope Lock 判定规则

## PASS

满足：

- P0 全部关闭
- Core 边界明确
- Manifest 冻结
- Naming 冻结
- Dependency Graph 冻结
- Security Contract 冻结
- Versioning 冻结
- Golden Asset 至少完成 1 条端到端验证链
- QA Gate 可自动执行

## CONDITIONAL PASS

允许开始有限开发，但：

- P0 已关闭
- P1 尚有少量实现工作
- Golden Asset 已具备基础验证能力

仅允许：

> Foundation / Common Asset / Golden Path

不得七大场景全面并行。

## FAIL

存在任意：

- Core / Asset Boundary 未明确
- Control Safety 缺失
- Manifest 缺失
- Dependency 无法验证
- Naming 未冻结
- 版本策略未定义
- 关键权限绕过
- 大量规格与实际代码不一致

则：

> 禁止进入 Phase 2 大规模工程实现。

---

# 52. 最终架构目标

最终 DT-Lite V4.0 应形成：

```text
                         L6 Intelligence
                    AI Agent / RCA / AI
                              ↑
                         L5 Operations
              Alarm / SOP / WorkOrder / KPI
                              ↑
                         L4 Application
              Dashboard / Scene / Mobile / GIS
                              ↑
                          L3 Template
                  Asset / Space / Scene Template
                              ↑
                         L2 Capability
              Telemetry / Control / Analytics
                              ↑
                          L1 Ontology
            Asset / Point / Space / Relationship
                              ↑
                    Platform Runtime
                              ↑
                       DT-Lite Core
```

行业包：

```text
Smart Built Environment
        │
        ├── Common Foundation
        │
        ├── Community
        ├── Mall
        ├── School
        ├── Hospital
        ├── Logistics
        ├── Data Center
        └── Industrial Park
```

最终目标不是：

> 做 100 个资产。

而是：

> **建立一套能够持续复制行业资产、能力、模板、应用和运维闭环的数字孪生行业插件体系。**

---

# 53. 最终评审意见

本 Asset Package Specification：

**总体架构：批准保留。**

**五层模型：批准冻结为设计基线。**

**行业场景方向：批准。**

**资产与能力分类：需要统一。**

**Zero-Code：必须重新定义。**

**Package Manifest：必须新增。**

**Dependency Graph：必须新增。**

**Point Semantic Model：必须新增。**

**Control Safety：必须新增。**

**Version / Migration：必须新增。**

**Core / Asset Package Boundary：必须冻结。**

**Golden Asset：必须作为 Phase 2 第一工程目标。**

**七场景并行开发：暂缓。**

最终建议：

> **先完成 Architecture Alignment → Core Change Set → Asset Package Contract → Golden Asset → Scope Lock，再进入行业资产包大规模工程实现。**

---

# 54. Scope Lock 最终决策

**Current Status：**

```text
ARCHITECTURE:
        CONDITIONALLY APPROVED

ENGINEERING:
        HOLD FOR SCOPE LOCK

PHASE 2:
        NOT YET OPEN FOR FULL PARALLEL IMPLEMENTATION

NEXT GATE:
        Architecture Alignment Report

REQUIRED:
        Golden Asset End-to-End Validation

FINAL AUTHORITY:
        DT-Lite V4.0 Architecture Scope Lock
```

**本文件本身不是行业资产包最终实现规格，而是进入最终 Asset Package Contract 与 Phase 2 Engineering Scope Lock 的前置架构审计文件。**

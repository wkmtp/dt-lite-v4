# DT-Lite V4.0 Smart Park Industry Asset Package Specification v2.0

**文档类型**：Industry Asset Package Detailed Technical Specification  
**平台版本**：DT-Lite V4.0  
**行业样板**：Smart Park / Smart Built Environment  
**Package ID**：`dtlite.smart-park`  
**状态**：Production-Oriented Engineering Baseline / Assembly Contract Freeze Candidate  

## 1. 目的与定位

本规格以 Smart Park 作为 DT-Lite 第一个实际行业样板。目标不是制作一个传统“智慧园区大屏”，而是建立一套能够覆盖真实园区项目从**资产建模、存量系统接入、零代码装配、3D/BIM/GIS、实时数据、告警、运维、大屏、AI 到发布运行**的生产级行业资产包，同时提前冻结未来 Smart Factory 可以直接复用的 Universal Asset Assembly Contract。

既有设计已经确定 Smart Park 必须建立在 DT-Lite Core、Asset Framework、Runtime、Low-Code Application Layer 和 AI Framework 之上，而不是重新建设独立用户、租户、权限、数据库核心、API Gateway、Twin Runtime 或 Workflow Runtime。fileciteturn7file0L24-L48 既有架构评审同时指出，v1.0 更接近“行业知识模型 + 产品功能目录 + 工程计划”，需要进一步达到可安装、可验证、可升级、可治理的 Production Asset Package Contract。fileciteturn7file1L165-L189

本 v2.0 因此将规格从“资产目录”提升为完整交付合同。

## 2. 设计目标

### 2.1 生产目标

Smart Park v2.0 必须尽最大可能覆盖真实项目中的以下对象与工作：

- 园区、建筑、楼层、区域、房间、道路、停车、室外空间；
- HVAC、冷站、AHU、FCU、VAV、泵、阀、照明、电梯、扶梯、给排水、配电、消防等机电设施；
- 电表、水表、气表、热量表、光伏、储能、充电桩；
- 温湿度、CO2、PM2.5、VOC、噪声、气象等环境设备；
- 视频、门禁、闸机、停车设备、安全传感器；
- 资产台账、维保、巡检、工单、SOP、告警与事件；
- BIM/GLB/GIS 与数字孪生实体绑定；
- BMS/BAS、EMS、CCTV、门禁、停车、物业/FM/CMMS、ERP 等存量系统接入；
- 实时数据、历史数据、趋势、KPI、告警、报表；
- 园区驾驶舱、能源中心、设施中心、安防中心、环境中心、运维中心；
- AI 查询、分析、诊断、推荐及受控操作。

### 2.2 平台复用目标

Smart Park 只新增行业语义和行业模板，不复制平台引擎。未来 Smart Factory 必须继续使用相同的 Asset、Point、Capability、Relationship、Template、Integration、Scene、Dashboard、Workflow、AI Tool、Package 和 Assembly Runtime。

## 3. 总体架构

```text
DT-Lite Core
 ├─ Identity / Tenant / RBAC
 ├─ Entity / Relationship
 ├─ API / Service / Repository
 ├─ Event / Telemetry / Data
 ├─ Package Registry / Versioning
 └─ Runtime
        ↓
Universal Asset & Assembly Framework
 ├─ Asset Model
 ├─ Point Model
 ├─ Capability Contract
 ├─ Composite Asset
 ├─ Integration / Mapping
 ├─ Scene / Dashboard / Workflow
 ├─ KPI / Alarm / SOP
 ├─ AI Tool Contract
 └─ Assembly Recipe
        ↓
Smart Park Industry Package
 ├─ Ontology
 ├─ Asset Templates
 ├─ Point Catalog
 ├─ Capability Catalog
 ├─ Integration Profiles
 ├─ Scene Templates
 ├─ Dashboard Templates
 ├─ Workflow / SOP
 ├─ KPI / Alarm
 ├─ Scenario Templates
 └─ AI Agents
        ↓
Zero-Code Studio
        ↓
Project Instance
        ↓
Twin Runtime
```

## 4. Universal Asset Assembly Contract 1.0

### 4.1 一级对象

统一冻结：

```text
Asset
Point
Capability
Relationship
AssetTemplate
CompositeAsset
IntegrationProfile
MappingProfile
SceneTemplate
DashboardTemplate
Widget
KPIDefinition
AlarmDefinition
WorkflowTemplate
SOP
WorkOrder
AITool
ScenarioTemplate
AssemblyRecipe
AssetPackage
```

### 4.2 通用装配关系

```text
Asset
 ├─ instanceOf → AssetTemplate
 ├─ contains → Asset
 ├─ locatedIn → SpatialAsset
 ├─ hasPoint → Point
 ├─ supports → Capability
 ├─ mappedTo → ExternalObject
 └─ visualizedBy → SceneObject

ScenarioTemplate
 ├─ assets[]
 ├─ integrations[]
 ├─ scenes[]
 ├─ dashboards[]
 ├─ workflows[]
 ├─ kpis[]
 └─ ai[]

AssemblyRecipe
 ├─ inputs
 ├─ discovery
 ├─ mapping
 ├─ instantiate
 ├─ bind
 ├─ generate
 └─ publish
```

### 4.3 Composite Asset

Composite Asset 是园区和未来工厂统一的核心结构：

```text
Building
 ├─ Floor
 ├─ HVAC System
 │   ├─ Chiller
 │   ├─ AHU
 │   ├─ Pump
 │   └─ Valve
 ├─ Elevator
 └─ Meter
```

未来：

```text
ProductionLine
 ├─ Machine
 ├─ Robot
 ├─ Conveyor
 └─ PLC
```

二者必须使用同一个 Composite Asset Runtime。

## 5. Asset 五层行业模型

继承既有 L1 Ontology、L2 Capability、L3 Template、L4 Application、L5 Operations 五层模型；既有评审明确要求正式建立这五层契约。fileciteturn7file1L150-L160

```text
L5 Operations
  Alarm / WorkOrder / SOP / Workflow
       ↑
L4 Application
  Command Center / Energy / Facility / Security
       ↑
L3 Template
  Asset / Scene / Dashboard / Workflow / Scenario
       ↑
L2 Capability
  Telemetry / Control / Analytics / Diagnosis
       ↑
L1 Ontology
  Asset / Point / Space / Relationship
```

## 6. Smart Park Asset Taxonomy

```text
Smart Park
├─ Spatial
│  ├─ Park
│  ├─ Campus
│  ├─ Building
│  ├─ Floor
│  ├─ Zone
│  ├─ Room
│  ├─ Corridor
│  ├─ Road
│  └─ OutdoorArea
├─ Facility
│  ├─ HVAC
│  ├─ Chiller
│  ├─ CoolingTower
│  ├─ AHU
│  ├─ FCU
│  ├─ VAV
│  ├─ Pump
│  ├─ Valve
│  ├─ Elevator
│  ├─ Escalator
│  ├─ Lighting
│  ├─ ElectricalPanel
│  ├─ Transformer
│  ├─ Generator
│  ├─ UPS
│  ├─ FireSystem
│  └─ WaterSystem
├─ Energy
│  ├─ ElectricMeter
│  ├─ WaterMeter
│  ├─ GasMeter
│  ├─ HeatMeter
│  ├─ PV
│  ├─ Storage
│  └─ EVCharger
├─ Environment
│  ├─ TemperatureSensor
│  ├─ HumiditySensor
│  ├─ CO2Sensor
│  ├─ PM25Sensor
│  ├─ VOCSensor
│  ├─ NoiseSensor
│  └─ WeatherStation
├─ Security
│  ├─ Camera
│  ├─ AccessController
│  ├─ Door
│  ├─ Reader
│  ├─ Barrier
│  └─ SecuritySensor
├─ Mobility
│  ├─ ParkingLot
│  ├─ ParkingSpace
│  ├─ ParkingGate
│  ├─ TrafficSensor
│  └─ EVChargingStation
└─ Operations
   ├─ InspectionPoint
   ├─ MaintenancePlan
   ├─ WorkOrder
   ├─ SOP
   └─ ServiceRequest
```

## 7. Asset 通用 Schema

每个正式资产必须具备：

```text
identity
classification
metadata
properties
relationships
points
capabilities
lifecycle
externalMappings
sceneBindings
kpiProfile
alarmProfile
permissionProfile
maintenanceProfile
```

示例：

```yaml
apiVersion: dtlite.io/v1
kind: AssetTemplate
metadata:
  id: tmpl.smartpark.hvac.ahu
  version: 1.0.0
spec:
  type: HVAC.AHU
  properties:
    manufacturer: string
    model: string
    ratedAirflow: float
    installationDate: date
  points:
    - point.hvac.supplyAirTemperature
    - point.hvac.returnAirTemperature
    - point.hvac.fanStatus
    - point.hvac.fanSpeed
    - point.hvac.power
  capabilities:
    - cap.hvac.read
    - cap.hvac.start
    - cap.hvac.stop
    - cap.hvac.setMode
    - cap.hvac.diagnose
```

## 8. 空间资产

### Park

必须支持名称、编码、面积、地址、经纬度、类型、运营状态、建设信息、建筑集合、设备集合、能耗、告警、人员/车流等扩展属性。

### Building

基础属性至少包括名称、编码、面积、高度、楼层数、建筑类型、建成年份、运营状态；运行属性支持能耗、环境、人流、告警、设备健康度。

### Floor / Zone / Room

必须支持层级、面积、用途、占用状态、环境状态、关联设备和 3D 对象。

## 9. 设施资产

### 9.1 HVAC

设备族：Chiller、CoolingTower、AHU、FCU、VAV、Pump、Valve、Sensor、Controller。

典型 Point：

```text
runStatus
faultStatus
mode
supplyAirTemperature
returnAirTemperature
supplyAirHumidity
fanSpeed
valvePosition
airflow
pressure
power
energy
alarmCode
runtimeHours
```

典型 Capability：

```text
readTelemetry
start
stop
setMode
setTemperature
setFanSpeed
resetAlarm
analyzeEnergy
diagnose
```

### 9.2 Elevator / Escalator

必须支持状态、位置、方向、速度、负载、门状态、故障码、运行小时、维护状态等语义；普通低代码页面不得绕过安全策略执行危险控制。

### 9.3 Electrical / Water / Fire

必须允许以 Composite Asset 组织系统级资产，而不是只把设备平铺为独立 Asset。

## 10. Energy Asset Model

能源必须形成：

```text
Park
 ↓
Building
 ↓
EnergySystem
 ↓
Meter
 ↓
EnergyStream
 ↓
Point
```

支持 electricity、water、gas、heat、cooling、PV、storage、EV。

核心 KPI：

```text
Consumption
Demand
PeakDemand
PowerFactor
EnergyIntensity
Cost
CarbonEmission
CarbonIntensity
Daily / Monthly / Yearly Consumption
```

必须支持能源流向、分项、峰谷、同比环比、建筑排名、异常分析。

## 11. Environment Model

支持温湿度、CO2、PM2.5、VOC、噪声、压力、气象等。必须支持实时值、历史趋势、阈值、空间热力、超限告警、环境评分。

## 12. Security / Parking

### Camera

DT-Lite 保存身份、位置、状态、视频引用和事件引用，不把视频媒体本身强制纳入 Twin Core。

### Access

```text
Controller → Reader → Door → AccessEvent
```

### Parking

```text
ParkingLot → Space / Gate / Barrier / Charger
```

必须支持车位占用、可用数、利用率、事件和充电利用率。

## 13. Point Semantic Contract

Point 是协议和业务 Asset 之间的稳定语义层。Point 不得直接等同 MQTT Topic、Modbus Register、BACnet Object 或 OPC UA Node。

```yaml
kind: PointDefinition
metadata:
  id: point.hvac.supply_air_temperature
  version: 1.0.0
spec:
  semanticType: Temperature
  datatype: float
  unit: degC
  writable: false
  qualityRequired: true
  historical: true
  aggregation: [avg, min, max]
```

## 14. Integration Framework

存量系统接入优先。统一链路：

```text
External System
 ↓
Connector
 ↓
Protocol Adapter
 ↓
External Object
 ↓
Mapping Profile
 ↓
DT-Lite Asset / Point
 ↓
Twin
```

第一阶段协议：MQTT、REST、WebSocket；行业适配预留 BACnet、Modbus TCP、OPC UA、SNMP、Webhook。

必须支持：认证、超时、重试、限流、轮询、Webhook、分页、映射、错误映射、健康检查、审计。

## 15. 存量系统 Profile

至少提供：

```text
BMS/BAS Profile
EMS Profile
CCTV Profile
Access Control Profile
Parking Profile
FM/CMMS Profile
ERP Profile
Generic REST Profile
Generic MQTT Profile
```

每个 Profile 必须定义：

```text
connection
authentication
discovery
externalObject
mapping
telemetry
event
command
healthCheck
errorHandling
```

## 16. Discovery / Mapping / Commissioning

生产级接入流程必须为：

```text
Connect
 ↓
Health Check
 ↓
Discover
 ↓
Classify
 ↓
Auto Match
 ↓
Preview
 ↓
Manual Correction
 ↓
Validate
 ↓
Test Read
 ↓
Test Command（如允许）
 ↓
Approve
 ↓
Publish
 ↓
Monitor
```

用户不能通过修改代码完成正常项目映射。

## 17. BIM / GIS / GLB

BIM/GIS/3D 与 Twin 必须分工：

```text
BIM/GIS → Geometry / Spatial Reference
DT-Lite → Semantic / State / Relationship / Capability / Operation
```

最终：

```text
Geometry + Semantic + Live State = Digital Twin Object
```

GLB 作为标准运行时模型；Scene Object 只能通过 Entity Binding 获取状态，不允许业务代码散落直接操作 Mesh。

## 18. Scene Template

```text
SceneTemplate
├─ camera
├─ lighting
├─ terrain
├─ models
├─ entityBindings
├─ stateVisualization
├─ interaction
└─ navigation
```

必须支持园区总览、建筑楼层、设备定位、告警定位、状态着色、属性面板、从大屏钻取到设备。

## 19. Dashboard / Large Screen

Dashboard 是一等装配对象。

```text
Dashboard
├─ layout
├─ theme
├─ widgets
├─ dataBindings
├─ filters
├─ interactions
├─ drillDown
├─ permissions
└─ refreshPolicy
```

Widget 至少包括：KPI Card、趋势、柱状、饼图、Gauge、表格、状态、告警、地图、3D Scene、视频、排名、热力图、Energy Flow、AI Panel。

必须提供标准大屏：

1. Park Command Center
2. Energy Center
3. Facility Center
4. Security Center
5. Environment Center
6. Parking Center
7. Operations Center
8. Asset Health Center

大屏必须能通过 Dashboard Designer 无代码复制、编辑、绑定、发布。

## 20. KPI Framework

KPI 不得硬编码在页面。

```text
KPI Definition
 ↓
Metric Query
 ↓
Aggregation
 ↓
Threshold
 ↓
Widget Binding
```

设施类 KPI：Availability、Online Rate、Fault Rate、MTBF、MTTR；能源类 KPI：Consumption、Intensity、Peak Demand、Carbon；运营类 KPI：Open WorkOrders、SLA、Response Time。

## 21. Alarm Framework

等级：INFO、WARNING、MAJOR、CRITICAL。

生命周期：

```text
Raised → Acknowledged → Investigating → Resolved → Verified → Closed
```

Alarm Profile 必须能够指定条件、持续时间、去抖、恢复条件、升级、通知、工单、SOP、审计。

## 22. Workflow / SOP / WorkOrder

统一闭环：

```text
Event
 ↓
Rule
 ↓
Alarm
 ↓
Workflow
 ↓
Task / SOP
 ↓
WorkOrder
 ↓
Execution
 ↓
Verification
 ↓
Close
```

示例：HVAC 高温 → 告警 → 查询风机/阀/过滤器 → AI 辅助诊断 → 创建工单 → 维修 → 验证。

## 23. Control Safety Contract

任何写操作必须声明：

```text
Capability
Permission
SafetyLevel
Preconditions
ApprovalPolicy
ExecutionTimeout
FeedbackRequired
AuditRequired
Rollback / Recovery
```

强制链路：

```text
UI / AI
 ↓
Tool Contract
 ↓
Permission
 ↓
Safety Policy
 ↓
Approval
 ↓
Command Runtime
 ↓
External System
 ↓
Feedback
 ↓
Audit
```

## 24. Zero-Code Studio

必须提供：

### Asset Designer
创建/继承/组合 Asset Template、Point、Capability、Relationship。

### Integration Designer
连接、发现、映射、验证、发布。

### Scene Designer
导入模型、识别对象、绑定 Asset、配置状态表现。

### Dashboard Designer
拖拽 Widget、选择数据源、绑定 KPI/Point、配置筛选与钻取。

### Workflow Designer
事件、条件、动作、审批、任务、SOP。

### Publish Center
版本、校验、依赖、发布、回滚。

## 25. Scenario Template

Scenario 是“真实项目”的装配蓝图。

```yaml
kind: ScenarioTemplate
metadata:
  id: scenario.smartpark.office-park
  version: 1.0.0
spec:
  assetTemplates: []
  integrationProfiles: []
  sceneTemplates: []
  dashboardTemplates: []
  workflowTemplates: []
  kpis: []
  alarms: []
  aiAgents: []
```

第一批场景：Office Park、Commercial Complex、Residential Community、Campus、Hospital、Logistics Park、Data Center、Industrial Park。既有规格也明确要求这些场景应在 Golden Foundation 和 Golden Path 之后逐步启用，而不是七个场景并行开发。fileciteturn7file3L302-L398

## 26. Assembly Recipe

Recipe 必须让最终用户通过 UI 完成项目实例化。

```yaml
kind: AssemblyRecipe
metadata:
  id: recipe.smartpark.standard
spec:
  inputs:
    park: required
    buildings: required
    bim: optional
    bms: optional
    ems: optional
  steps:
    - validateInput
    - importSpatial
    - discoverExternalObjects
    - classify
    - autoMap
    - userConfirm
    - instantiateAssets
    - bindPoints
    - bind3D
    - generateDashboards
    - generateWorkflows
    - generateAI
    - validate
    - publish
```

## 27. Package Manifest

```yaml
apiVersion: dtlite.io/v1
kind: AssetPackage
metadata:
  id: dtlite.smart-park
  version: 2.0.0
spec:
  platform:
    minVersion: 4.0.0
  contracts:
    assembly: 1.0.0
    asset: 1.0.0
    point: 1.0.0
    capability: 1.0.0
    integration: 1.0.0
  modules:
    ontology: 2.0.0
    templates: 2.0.0
    integrations: 2.0.0
    scenes: 2.0.0
    dashboards: 2.0.0
    workflows: 2.0.0
    ai: 2.0.0
```

既有评审已经要求正式 Asset Package Manifest、Dependency Graph、版本、迁移和 Golden Asset。fileciteturn7file1L150-L160

## 28. Package 目录

```text
smart-park/
├─ package.yaml
├─ schemas/
├─ ontology/
├─ assets/
├─ points/
├─ capabilities/
├─ relationships/
├─ integrations/
│  ├─ bms/
│  ├─ ems/
│  ├─ cctv/
│  ├─ access/
│  ├─ parking/
│  └─ fm/
├─ templates/
│  ├─ assets/
│  ├─ scenes/
│  ├─ dashboards/
│  ├─ workflows/
│  └─ scenarios/
├─ kpis/
├─ alarms/
├─ sops/
├─ ai/
├─ recipes/
├─ migrations/
├─ tests/
└─ docs/
```

## 29. API 契约

行业 API 必须复用 Core 的 API → Service → Repository → ORM 边界，不允许行业 Controller 直接操作数据库。

核心资源：

```text
/assets
/assets/{id}
/assets/{id}/points
/assets/{id}/capabilities
/integrations
/integrations/test
/integrations/discover
/mappings/validate
/mappings/publish
/scenes
/dashboards
/scenarios
/scenarios/{id}/instantiate
/alarms
/workorders
/commands/execute
```

## 30. Data / Telemetry

Telemetry 必须区分：

```text
Raw Telemetry
 ↓
Normalized Point Value
 ↓
Twin State
 ↓
Time Series
 ↓
KPI / Alarm / Analytics
```

每个值至少考虑：timestamp、value、quality、source、ingestTime、unit、sequence；写入异常、重复、迟到、断线恢复必须有明确策略。

## 31. 多租户与权限

Smart Park 完全继承 DT-Lite Core TenantContext。行业包不得自建租户认证，不得信任客户端 tenant_id，不得绕过 Repository。所有控制能力必须执行 RBAC/Permission/Safety/Audit。

## 32. AI Agent

第一商业版本至少：

```text
Park Assistant
Energy Agent
Facility Agent
Operations Agent
```

工具：

```text
queryAssets
queryPoints
queryEnergy
queryAlarms
queryWorkOrders
queryEnvironment
queryParking
analyzeEnergy
diagnoseEquipment
createWorkOrder
navigateScene
openDashboard
```

AI Tool 必须声明 inputSchema、outputSchema、permission、readOnly、requiresApproval、audit。

## 33. AI 典型闭环

```text
“今天哪个楼宇能耗异常？”
 ↓
queryEnergy
 ↓
KPI Engine
 ↓
Anomaly Analysis
 ↓
Result + Dashboard Drilldown
```

控制场景必须经过用户确认/审批和安全策略，不允许 AI 直接越权控制设备。

## 34. Smart Factory Compatibility Freeze

未来 Smart Factory 必须复用：

```text
Asset Model
Point Model
Capability Contract
Relationship Model
Composite Asset
Integration Framework
Mapping Framework
Scene Engine
Dashboard Engine
Workflow Engine
KPI Engine
Alarm Engine
AI Tool Contract
Package Manifest
Assembly Recipe
Validation / Migration
```

Factory 只新增：

```text
Factory
Workshop
ProductionArea
ProductionLine
Machine
Robot
Conveyor
PLC
SCADA
MES
WMS
QMS
Material
Product
OEE
```

因此：

```text
Smart Park: Building → HVAC → BMS
Smart Factory: Line → Machine → PLC → MES
```

只是行业语义不同，装配语法不变。

## 35. Smart Park / Smart Factory 对照

| 通用层 | Smart Park | Smart Factory |
|---|---|---|
| Spatial Asset | Park/Building/Floor/Room | Factory/Workshop/Area |
| Physical Asset | HVAC/Elevator/Pump | Machine/Robot/Conveyor |
| Point | Temperature/Power/Status | Speed/Pressure/Cycle |
| Composite Asset | Building System | Production Line |
| Integration | BMS/EMS/CCTV | PLC/SCADA/MES |
| KPI | Energy Intensity | OEE |
| Alarm | Facility Alarm | Machine Alarm |
| Workflow | Maintenance | Production/Maintenance |
| Dashboard | Park Command Center | Factory Command Center |
| AI | Park Assistant | Factory Assistant |
| Assembly Engine | **Same** | **Same** |

## 36. Golden Assets

至少建立以下跨层 Golden Assets：

### Golden Asset 1 — AHU

验证：Asset → Point → MQTT/REST → Twin → 3D → Dashboard → Alarm → Workflow → AI。

### Golden Asset 2 — Electric Meter

验证：Meter → Energy Point → Time Series → KPI → Energy Dashboard → Anomaly。

### Golden Asset 3 — Building

验证：Building → Floor → Room → BIM/GLB → Aggregated Energy → Command Center。

### Golden Asset 4 — Camera

验证：Camera → External Stream Reference → 3D Location → Security Dashboard → Event。

### Golden Asset 5 — Parking Space

验证：Parking Space → Occupancy Point → Map/3D → Parking Dashboard。

## 37. Golden Scenario

必须优先完成 Office Park Golden Scenario，而不是同时开发全部行业场景。既有路线已经确定 Stage A Golden Foundation、Stage B Common Asset Pack、Stage C HVAC/Chiller Golden Path、Stage D Smart Park MVP，再逐步扩展其他 Scenario。fileciteturn7file3L302-L398

Golden Scenario：

```text
1 Park
2 Buildings
10+ Floors
100+ Rooms
HVAC
Meters
Sensors
BMS
EMS
BIM/GLB
```

必须能够通过 Studio：

```text
Create Project
→ Select Scenario
→ Import BIM/GLB
→ Connect BMS/EMS
→ Discover
→ Map
→ Instantiate
→ Generate Scene
→ Generate Dashboards
→ Generate Alarms/Workflows
→ Enable AI
→ Validate
→ Publish
```

## 38. Zero-Code Acceptance

“Zero-Code”定义为：最终行业实施人员在正常项目配置阶段不修改 Python/TypeScript/SQL，不直接修改生产数据库，不手工编写 YAML/JSON；开发人员可以使用 Schema/Manifest/Recipe 完成 Package 开发，但这些工程文件不能作为最终用户 UI 的替代品。既有 Scope Lock 也明确禁止将 YAML/Helm 当最终用户 UI。fileciteturn7file3L402-L436

## 39. Validation Gate

发布前必须执行：

```text
Manifest
Dependency
Schema
Naming
Point
Capability
Mapping
Binding
Template
Application
Alarm
SOP
Permission
Safety
3D
AI Tool
Migration
Security
Performance
Golden Asset
```

既有 Release Gate 已明确要求 Manifest、Version、Dependency、Schema、Point、Capability、Binding、Template、Application、Alarm、SOP、Permission、Safety、3D、AI Tool、升级兼容、安全、SBOM、签名、Golden Asset 和性能测试。fileciteturn7file3L440-L469

## 40. Versioning / Upgrade / Migration

所有 Package、Schema、Template、Integration Profile、Dashboard、Workflow、AI Tool 必须独立版本化。

升级规则：

```text
Draft
→ Validate
→ Publish
→ Install
→ Upgrade
→ Verify
→ Rollback if needed
```

禁止无 Migration 的生产 Schema 破坏性修改。模板升级不得无条件修改已有实例。

## 41. Performance Baseline

第一商业版本建议目标：

```text
ordinary API p95 < 500 ms
alarm propagation p95 < 2 s
dashboard initial load < 3 s
standard optimized 3D scene < 5 s
```

大规模项目必须通过独立 Benchmark 再确定正式 SLA；上述数值是工程基线而非所有部署规模的绝对承诺。

## 42. Deployment

支持：

```text
Cloud
Private
Edge
Hybrid
```

典型：

```text
Cloud / Central Platform
        ↕
Park Edge Gateway
        ↕
BMS / EMS / IoT / Video / Access / Parking
```

## 43. 安全边界

禁止：

- 行业包私改 Core；
- 绕过 TenantContext；
- 通过 URL/query/header 注入租户上下文；
- AI 绕过权限执行写操作；
- 低代码页面直接连接 PLC/BMS；
- 未审计的控制命令；
- 在行业包内部复制 Auth、Tenant、Workflow Runtime。

## 44. Engineering Rules

```text
PARK-001  Platform First
PARK-002  No Independent System
PARK-003  Every business object is an Asset
PARK-004  Every Asset has Schema and Version
PARK-005  Point is protocol-independent semantic layer
PARK-006  Protocol logic belongs to Adapter
PARK-007  Integration uses Mapping Profile
PARK-008  Reusable projects must be Scenario/Template driven
PARK-009  Dashboard is schema-driven
PARK-010  Scene is entity-binding-driven
PARK-011  Workflow is event/rule driven
PARK-012  AI is Tool Contract driven
PARK-013  Control requires Permission + Safety + Audit
PARK-014  Industry logic never enters Core
PARK-015  Smart Factory reuses the same Assembly Contract
```

## 45. 工程实施阶段

### Stage A — Universal Assembly Foundation

```text
Manifest
Registry
Dependency Graph
Point Model
Capability Contract
Template Contract
Integration Contract
Alarm Contract
SOP Contract
Versioning
Migration
Validation
```

### Stage B — Common Smart Park Assets

```text
Park
Building
Floor
Room
Equipment
Meter
Sensor
Energy
Environment
Security
```

### Stage C — Golden Path

优先：HVAC / Chiller / AHU。

### Stage D — Commercial MVP

```text
3D Overview
Energy Dashboard
Park / Building / Equipment
MQTT
REST
BMS/EMS basic integration
Alarm
AI Q&A
```

### Stage E — Production Expansion

Security、Parking、Fire、Property/FM、PV、Storage、EV、BIM/GIS 深化。

### Stage F — Advanced Intelligence

RCA、Prediction、Optimization、Energy Optimization、Predictive Maintenance、AI Workflow、Controlled Automation。该阶段与既有路线一致。fileciteturn7file3L386-L398

## 46. Acceptance Matrix

| 类别 | 必须通过 |
|---|---|
| Asset | Park/Building/Floor/Room/Equipment/HVAC/Meter/Sensor |
| Point | Semantic Point + quality + history |
| Integration | MQTT/REST + BMS/EMS profiles |
| Discovery | 自动发现/分类/映射/验证 |
| 3D | GLB/BIM binding + state visualization |
| Dashboard | Command/Energy/Facility/Alarm/Environment |
| Operations | Alarm/WorkOrder/SOP/Workflow |
| AI | Query/Analysis/Diagnosis/Tool contract |
| Security | Tenant/RBAC/Safety/Audit |
| Zero-Code | Golden Scenario 全流程无代码配置 |
| Package | Manifest/Dependency/Version/Migration |
| Quality | Golden Asset/E2E/Performance/Security |
| Factory | 不修改 Assembly Engine 即可新增 Factory Package |

## 47. 最终架构冻结

Smart Park 的最终定位：

```text
One Platform
+ One Twin Runtime
+ One Asset Model
+ One Assembly Model
+ One Integration Model
+ One Low-Code Studio
+ One Dashboard Engine
+ One Workflow Engine
+ One AI Tool Contract
+
Multiple Industry Asset Packages
```

Smart Park 是第一个生产级行业验证和商业化样板；不是平台边界。既有产品定义同样明确，Smart Park 的价值在于以 Digital Twin + IoT + AI + Low-Code 形成可视化、智能化和自动化管理。fileciteturn7file4L518-L556

因此本规格的核心工程结论是：

> **先冻结 Universal Asset Assembly Contract，再用 Smart Park 的真实生产需求验证它；Smart Park 的行业差异通过 Asset / Capability / Template / Integration Profile / Scenario / Application 实现，而不是通过复制平台。**

## 48. Release Decision

进入 AgnesCode 大规模工程实现前必须先完成：

```text
Architecture Alignment
→ Contract Review
→ Schema Review
→ Golden Asset Review
→ Assembly E2E Review
→ Scope Lock
→ Task Breakdown
→ Engineering
```

不得直接从本规格一次性生成全部代码。既有工程执行规范要求 AgnesCode 采用 Phase Driven Development，每个 Phase 依次完成 Design → Task List → Code → Test → Review → Commit。fileciteturn7file9L1197-L1238

**Document Status: Production-Oriented Engineering Baseline / Ready for Architecture Alignment & Scope Lock Review**

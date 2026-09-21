# DT-Lite V4.0 Smart Park Industry Asset Package
## 重构架构设计文档（Reformulated Architecture Design）

> **版本**：v3.0-Reformulated  
> **状态**：基于 Conditional Pass 评审重新制定  
> **核心原则**：可执行、可安装、可验证、可治理  
> **评审基线**：Architecture Alignment & Scope Lock Review（43 个 P0/P1 问题）  
> **文档日期**：2026-09-11

---

## 目录

1. [核心架构决策](#1-核心架构决策)
2. [Asset Package Manifest](#2-asset-package-manifest)
3. [Dependency Graph 与校验规则](#3-dependency-graph-与校验规则)
4. [Naming Convention 冻结规范](#4-naming-convention-冻结规范)
5. [Point Semantic Model（点位语义模型）](#5-point-semantic-model点位语义模型)
6. [Capability Contract（能力契约）](#6-capability-contract能力契约)
7. [Control Safety Contract（控制安全契约）](#7-control-safety-contract控制安全契约)
8. [Template Contract（模板契约）](#8-template-contract模板契约)
9. [Alarm / SOP / Workflow Contracts](#9-alarm--sop--workflow-contracts)
10. [Versioning & Migration Strategy](#10-versioning--migration-strategy)
11. [Zero-Code 重新定义](#11-zero-code-重新定义)
12. [Core / Package Boundary（核心/包边界）](#12-core--package-boundary核心包边界)
13. [Golden Asset / Golden Path](#13-golden-asset--golden-path)
14. [Architecture Alignment Matrix](#14-architecture-alignment-matrix)
15. [Scope Lock（范围锁定）](#15-scope-lock范围锁定)
16. [Release Gate Checklist](#16-release-gate-checklist)
17. [交付清单](#17-交付清单)
18. [实施路线图与里程碑](#18-实施路线图与里程碑)
19. [风险与对策](#19-风险与对策)

---

## 1. 核心架构决策

### 1.1 五层架构重新定义（强制冻结）

| 层级 | 名称 | 职责边界 | 交付物 | 约束条件 |
|------|------|----------|--------|----------|
| **L1** | **Ontology Layer** | 语义本体、资产分类、关系定义 | `asset-ontology.yaml`、JSON-LD Context | 禁止包含任何实例数据；仅定义 TBox |
| **L2** | **Capability Layer** | 能力契约、算子注册、适配器映射 | `capability-contracts.yaml`、Adapter Spec | Capability ≠ Algorithm；算法下沉到 Plugin |
| **L3** | **Template Layer** | 资产模板、场景模板、组装配方 | `asset-templates.yaml`、`scene-templates.yaml`、`assembly-recipes.yaml` | 模板必须可实例化、可校验、可版本化 |
| **L4** | **Application Layer** | 仪表盘、KPI、告警、SOP、工单、AI Tool | `dashboards/`、`alarms.yaml`、`sops.yaml`、`ai-tools.yaml` | 纯配置交付，零代码部署 |
| **L5** | **Operations Layer** | 运维视图、版本治理、迁移脚本、Golden Path | `migrations/`、`golden-assets.yaml`、`release-gates.yaml` | 仅运维工具，不包含业务逻辑 |

> **P0-01 修正**：原 SPEC 混淆了 L2/L3/L4 边界，现强制分层，跨层引用仅允许**向下引用**（L4→L3→L2→L1），严禁反向依赖。

---

### 1.2 七大场景开发策略：从「并行」改为「阶段式串行」

| 阶段 | 代号 | 目标 | 交付物 | 通过标准 |
|------|------|------|--------|----------|
| **Stage A** | **Golden Foundation** | 完成 L1-L5 核心骨架 + 1 个 Golden Asset 端到端跑通 | `asset-package.yaml`、Core Schemas、1 个 Golden Asset | Golden Path 验证 100% 通过 |
| **Stage B** | **Common Asset Pack** | 抽取 7 场景共性的 30+ 通用资产类型 | `common-assets.yaml`、共享 Capability/Template | 覆盖率 ≥ 80% 场景通用需求 |
| **Stage C** | **Golden Path Hardening** | 10-20 个 Golden Asset 全链路验证 | `golden-assets.yaml`、验证报告 | 5 层全链路零报错、性能基线达标 |
| **Stage D** | **Industry Extensions** | 按场景增量交付差异化资产包 | `smart-community.yaml`、`smart-mall.yaml`... | 各场景独立版本、可选装 |
| **Stage E** | **Control & Intelligence** | C0-C4 控制安全、L6 智能编排 | `control-contracts.yaml`、AI 编排规则 | 审计日志完整、人工介入点可追溯 |
| **Stage F** | **Governance & Release** | 版本治理、迁移工具、发布门禁 | `migration-toolkit`、Release Gate Checklist | 语义化版本、一键回滚、合规报告 |

> **Scope Lock §42-43**：**严禁**在 Stage A 完成前启动任何场景并行开发；**严禁**在 Golden Path 未跑通前发布任何 Industry Extension。

---

## 2. Asset Package Manifest

### 2.1 `asset-package.yaml` 规范（P0-02 强制）

```yaml
# asset-package.yaml - 单一事实来源
package:
  name: "dt-lite-smart-park"
  version: "0.1.0-alpha"           # SemVer 2.0，Pre-release 阶段
  description: "Smart Park Industry Asset Package for DT-Lite V4.0"
  maturity: "alpha"                # alpha | beta | stable | deprecated
  license: "Apache-2.0"

# 核心依赖：仅依赖 Core Platform 接口契约，不捆绑基础设施
dependencies:
  core-platform:
    ref: "dt-lite-core-platform"
    version: ">=4.0.0 <5.0.0"      # 语义化版本区间
    contracts:                     # 显式声明依赖的 Core 契约
      - "entity/v1"
      - "asset/v1"
      - "property/v1"
      - "relationship/v1"
      - "scene/v1"
      - "binding/v1"
      - "telemetry/v1"
      - "alarm/v1"
      - "workflow/v1"
  # 严禁在此声明：PostgreSQL、TimescaleDB、Redis、EMQX、MinIO、Neo4j 等基础设施
  # 基础设施由 Platform Helm Chart 统一提供，Package 仅消费服务端点

# 跨层引用声明（供校验器使用）
layer-dependencies:
  L1_Ontology: []
  L2_Capability: ["L1_Ontology"]
  L3_Template: ["L1_Ontology", "L2_Capability"]
  L4_Application: ["L1_Ontology", "L2_Capability", "L3_Template"]
  L5_Operations: ["L1_Ontology", "L2_Capability", "L3_Template", "L4_Application"]

# 资产清单索引
assets:
  - ref: "ontology/asset-ontology.yaml"
    layer: "L1"
  - ref: "capability/capability-contracts.yaml"
    layer: "L2"
  - ref: "template/asset-templates.yaml"
    layer: "L3"
  - ref: "template/scene-templates.yaml"
    layer: "L3"
  - ref: "template/assembly-recipes.yaml"
    layer: "L3"
  - ref: "application/dashboards/"
    layer: "L4"
  - ref: "application/alarms.yaml"
    layer: "L4"
  - ref: "application/sops.yaml"
    layer: "L4"
  - ref: "application/ai-tools.yaml"
    layer: "L4"
  - ref: "operations/golden-assets.yaml"
    layer: "L5"
  - ref: "operations/migrations/"
    layer: "L5"
  - ref: "operations/release-gates.yaml"
    layer: "L5"

# 场景扩展包（Stage D 交付，可选装）
scenario-extensions:
  - id: "smart-community"
    version: "0.0.0"               # 占位，Stage D 时定版
    depends-on: ["common-assets@v0.1.0"]
  - id: "smart-mall"
    version: "0.0.0"
    depends-on: ["common-assets@v0.1.0"]
  # ... 其他 5 个场景
```

> **P0-03 修正**：Manifest 必须包含 `layer-dependencies` 显式声明，CI 门禁将执行**跨层引用校验**（禁止 L1 引用 L3，禁止 L4 引用 L5 等反向依赖）。

---

## 3. Dependency Graph 与校验规则

### 3.1 依赖图谱定义

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DT-Lite Core Platform                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │entity/v1│ │asset/v1 │ │property/v1│ │rel/v1 │ │scene/v1 │          │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │
│  ┌───▼───────────▼───────────▼───────────▼─────────▼───┐              │
│  │          Core Platform Contracts (gRPC/REST)        │              │
│  └────────────────────┬────────────────────────────────┘              │
└───────────────────────│───────────────────────────────────────────────┘
                        │ Dependency (Consumer only)
                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Smart Park Asset Package                            │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐              │
│  │ L1 Ont.  │→│ L2 Cap.   │→│ L3 Tpl.  │→│ L4 App.  │              │
│  └──────────┘  └───────────┘  └──────────┘  └──────────┘              │
│  ┌──────────┐                                                          │
│  │ L5 Ops   │  (Migration, Golden Asset, Release Gate)                 │
│  └──────────┘                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Dependency Flow (Downward Only):
  L1 ──→ L2 ──→ L3 ──→ L4
                    │
                    └────→ L5
```

### 3.2 校验规则（CI 门禁强制执行）

| 规则 ID | 规则描述 | 违反后果 |
|---------|----------|----------|
| **DG-01** | 所有 `ref` 必须指向 Manifest 中声明的文件 | 构建失败 |
| **DG-02** | 跨层引用方向必须符合 `layer-dependencies` 声明 | 构建失败 |
| **DG-03** | 禁止循环依赖（Tarjan 算法检测） | 构建失败 |
| **DG-04** | Core Platform 契约版本区间必须显式声明，禁止 `latest` | 构建失败 |
| **DG-05** | 场景扩展包 `depends-on` 必须指向已发布的 Common Asset Pack 版本 | 发布阻断 |

---

## 4. Naming Convention 冻结规范

### 4.1 统一命名格式（P0-04 强制）

```
asset.<domain>.<sub_domain>.<specific_type>
```

| 字段 | 取值约束 | 示例 |
|------|----------|------|
| `domain` | 固定：`park` | `park` |
| `sub_domain` | 枚举：`energy`、`environment`、`security`、`facility`、`transport`、`operation`、`management` | `energy` |
| `specific_type` | kebab-case，业务名词单数 | `transformer`、`water-meter`、`camera-ptz` |

### 4.2 完整资产命名清单

| 资产类型 | 规范名称 | 说明 |
|----------|----------|------|
| 变压器 | `asset.park.energy.transformer` | 高压/低压变压器 |
| 智能水表 | `asset.park.energy.water-meter` | NB-IoT/LoRa 接入 |
| PTZ 摄像机 | `asset.park.security.camera-ptz` | 支持云台控制 |
| 电梯 | `asset.park.facility.elevator` | 故障码映射 |
| 充电桩 | `asset.park.transport.charging-pile` | OCPP 协议适配 |
| 空调主机 | `asset.park.facility.chiller` | 冷冻水系统 |
| 楼宇自控面板 | `asset.park.management.bas-panel` | BACnet/IP |
| 配电柜 | `asset.park.energy.switchgear` | 高低压开关柜 |
| 冷水机组 | `asset.park.facility.chiller` | 中央空调主机 |
| 空气质量站 | `asset.park.environment.air-quality-station` | PM2.5/CO2/VOC |
| 停车场道闸 | `asset.park.transport.barrier` | 车辆进出控制 |
| 垃圾分类箱 | `asset.park.operation.waste-compactor` | 满溢检测/分类 |

> **P0-04 修正**：原 SPEC 使用 `SmartPark:Transformer`、`dt:WaterMeter` 等不一致命名，现统一为上述格式。**所有现有资产定义必须在 Stage A 完成重命名迁移**。

### 4.3 衍生命名规则

| 制品类型 | 命名模式 | 示例 |
|----------|----------|------|
| Point 语义标识 | `point.<domain>.<sub_domain>.<asset_type>.<measurement>` | `point.park.energy.transformer.active-power` |
| Capability ID | `cap.<domain>.<sub_domain>.<verb>` | `cap.park.energy.monitor`、`cap.park.security.control` |
| Template ID | `tpl.<domain>.<sub_domain>.<asset_type>` | `tpl.park.energy.transformer` |
| Scene Template ID | `scene.<domain>.<scenario>` | `scene.park.smart-community` |
| Alarm Rule ID | `alm.<domain>.<sub_domain>.<asset_type>.<rule>` | `alm.park.energy.transformer.overload` |
| SOP ID | `sop.<domain>.<scenario>.<procedure>` | `sop.park.fire.evacuation` |
| Work Order ID | `wo.<domain>.<scenario>.<task>` | `wo.park.maintenance.elevator-inspection` |

---

## 5. Point Semantic Model（点位语义模型）

### 5.1 设计原则（P1-01 核心改进）

> **Point ≠ Protocol Tag**。Point 定义**语义契约**（是什么、单位、采样、质量），**不绑定**任何协议地址（Modbus 地址、OPC UA NodeId、MQTT Topic）。协议绑定通过 **MappingProfile** 单独定义。

### 5.2 Point Definition Schema（YAML）

```yaml
# point-definitions/energy/transformer/active-power.yaml
point:
  semantic_id: "point.park.energy.transformer.active-power"
  display_name: "有功功率"
  description: "变压器高压侧有功功率，正值表示送电，负值表示受电"
  
  # 语义属性（协议无关）
  semantics:
    quantity_kind: "power"              # QUDT 量纲
    unit: "kW"                          # UCUM 单位
    data_type: "float64"                # 平台内部存储类型
    sampling:
      rate: "1s"                        # 采样周期（ISO 8601 duration）
      strategy: "report_on_change"      # 触发策略
      deadband: 0.5                     # 变化死区（单位同 unit）
    quality:
      good: [192]                       # Good Non-Specific
      uncertain: [64, 128]              # Uncertain
      bad: [0, 32]                      # Bad
  
  # 约束规则（用于数据校验）
  constraints:
    range:
      min: -5000
      max: 5000
    rate_of_change:
      max_per_second: 500               # 最大变化率 kW/s
  
  # 关联告警语义（引用而非内联）
  alarm_semantics:
    - ref: "alm.park.energy.transformer.overload"
      severity: "critical"
    - ref: "alm.park.energy.transformer.reverse-power"
      severity: "warning"
```

### 5.3 Mapping Profile（协议绑定分离）

```yaml
# mapping-profiles/modbus/transformer/active-power.yaml
mapping_profile:
  id: "map.modbus.transformer.active-power.v1"
  protocol: "modbus-tcp"
  target_point: "point.park.energy.transformer.active-power"
  
  mapping:
    address: 40001                      # Modbus 寄存器地址
    register_type: "holding"
    data_encoding: "ieee754-float32"    # 编码方式
    byte_order: "big-endian"
    word_order: "big-endian"
    scale: 1.0                          # 缩放因子
    offset: 0.0                         # 偏移量
  
  # 读取策略
  poll:
    interval: "1s"
    timeout: "500ms"
    retries: 3

# 同一 Point 可关联多个 Mapping Profile（多协议适配）
alternative_mappings:
  - ref: "map.opcua.transformer.active-power.v1"
  - ref: "map.mqtt.transformer.active-power.v1"
```

> **P1-01 修正**：原 SPEC 将协议地址硬编码在 Point 定义中，导致协议切换需修改本体。现分离为 **Point Definition（语义）** + **Mapping Profile（协议绑定）**，支持一对多协议适配。

---

## 6. Capability Contract（能力契约）

### 6.1 能力契约定义（P1-02 修正）

```yaml
# capability/capability-contracts.yaml
capabilities:
  - id: "cap.park.energy.monitor"
    name: "能耗监测能力"
    category: "monitoring"
    description: "提供电/水/气/热等能源实时监测、统计、报表能力"
    
    # 输入点位语义需求（声明式）
    requires_points:
      - semantic_id: "point.park.energy.*.active-power"
        cardinality: "1..n"             # 至少 1 个，支持多回路
      - semantic_id: "point.park.energy.*.energy-total"
        cardinality: "0..n"
    
    # 输出能力接口（Core Platform 标准接口）
    provides:
      - interface: "telemetry/query"
        method: "get_latest"
      - interface: "telemetry/query"
        method: "get_history"
      - interface: "telemetry/aggregate"
        method: "sum_by_period"
      - interface: "kpi/compute"
        method: "energy_efficiency"
    
    # 算子注册（引用 Plugin，不内含算法）
    operators:
      - ref: "plugin.energy.aggregator.v1"
        config_schema: "schemas/energy-aggregator-config.json"
      - ref: "plugin.energy.cost-calculator.v1"
        config_schema: "schemas/energy-cost-config.json"
    
    # SLA 承诺
    sla:
      latency_p99_ms: 200
      availability: "99.9%"
      data_freshness_seconds: 5
```

### 6.2 算子 Plugin 规范（下沉到 Plugin 层）

```yaml
# plugins/energy-aggregator/plugin.yaml
plugin:
  id: "plugin.energy.aggregator.v1"
  name: "Energy Data Aggregator"
  version: "1.0.0"
  entry_point: "energy_aggregator:main"
  
  # 标准化接口契约
  interface:
    type: "grpc"                        # 或 wasm、http
    service: "energy.aggregator.v1"
    methods:
      - name: "aggregate"
        input: "AggregateRequest"
        output: "AggregateResponse"
  
  # 资源限制
  resources:
    cpu: "100m"
    memory: "128Mi"
  
  # 配置模式
  config_schema: "schemas/energy-aggregator-config.json"
```

> **P1-02 修正**：原 SPEC 将聚合算法、费用计算等硬编码在 Capability 中。现 **Capability 仅声明接口契约**，算法逻辑下沉到 **可替换、可版本化、可沙箱运行的 Plugin**。

---

## 7. Control Safety Contract（控制安全契约）

### 7.1 控制分级定义（P1-03 核心新增）

| 级别 | 代码 | 定义 | 审批要求 | 审计要求 | 典型场景 |
|------|------|------|----------|----------|----------|
| **C0** | `observe` | 只读监测，无控制指令 | 无 | 访问日志 | 仪表盘查询、报表导出 |
| **C1** | `adjust` | 参数调整，非实时、可逆 | 操作员确认 | 操作日志+参数快照 | 设定温度、修改阈值、调整定时策略 |
| **C2** | `command` | 实时开关/启停指令，可逆 | 双人确认 或 一人+自动校验 | 完整指令链路日志+回滚记录 | 启停水泵、开关闸、充电桩启停 |
| **C3** | `override` | 覆盖自动控制，强制介入 | 值班主管授权 + 双人确认 | 不可篡改审计轨迹+事后复盘 | 火灾强制开启排烟、紧急切断电源 |
| **C4** | `interlock` | 联锁保护，硬件级强制 | 系统自动执行、不可人工干预 | 硬件级黑盒记录 | 变压器差动保护、压力容器超压泄放 |

### 7.2 控制契约模板

```yaml
# control-contracts.yaml
control_contracts:
  - capability: "cap.park.facility.pump-control"
    control_points:
      - point: "point.park.facility.pump.run-command"
        level: "C2"
        requires:
          - approval: "dual_confirmation"
            roles: ["operator", "supervisor"]
          - validation: "interlock_check"
            rules:
              - "pump.vibration < threshold"
              - "pump.temperature < max_temp"
        audit:
          log_fields: ["operator_id", "supervisor_id", "pre_state", "post_state", "duration_ms"]
          retention_years: 7
      
      - point: "point.park.facility.pump.emergency-stop"
        level: "C3"
        requires:
          - approval: "supervisor_authorization"
          - validation: "none"              # 紧急停止无前置校验
        audit:
          log_fields: ["operator_id", "supervisor_id", "trigger_reason", "pre_state"]
          retention_years: 10
          immutable: true
      
      - point: "point.park.facility.pump.interlock-trip"
        level: "C4"
        requires:
          - approval: "system_automatic"
        audit:
          log_fields: ["trigger_source", "sensor_values", "trip_time"]
          retention_years: 10
          immutable: true
          hardware_log: true
```

> **P1-03 修正**：原 SPEC 无控制分级，所有写指令同等对待。现引入 **C0-C4 五级契约**，每级强制绑定审批流、校验规则、审计字段、保留期限，**不可降级、不可绕过**。

---

## 8. Template Contract（模板契约）

### 8.1 Asset Template Schema

```yaml
# template/asset-templates.yaml
asset_templates:
  - id: "tpl.park.energy.transformer"
    version: "1.0.0"
    asset_type: "asset.park.energy.transformer"
    ontology_ref: "asset.park.energy.transformer"  # L1 本体引用
    
    # 标准化点位配置（引用 Point Semantic ID）
    points:
      - semantic_id: "point.park.energy.transformer.active-power"
        required: true
        mapping_profiles: ["map.modbus.transformer.v1", "map.opcua.transformer.v1"]
      - semantic_id: "point.park.energy.transformer.reactive-power"
        required: true
      - semantic_id: "point.park.energy.transformer.temperature-winding"
        required: false
        default_mapping: "map.modbus.transformer.temp.v1"
    
    # 关联能力（引用 Capability ID）
    capabilities:
      - ref: "cap.park.energy.monitor"
      - ref: "cap.park.facility.condition-monitoring"
    
    # 关联关系模板
    relationships:
      - type: "feeds"
        target_template: "tpl.park.energy.switchgear"
        cardinality: "1..1"
      - type: "contains"
        target_template: "tpl.park.energy.transformer-winding"
        cardinality: "3..3"
    
    # 实例化参数 Schema（JSON Schema）
    instantiation_params:
      type: "object"
      required: ["rated_capacity_kva", "voltage_ratio", "location_id"]
      properties:
        rated_capacity_kva:
          type: "number"
          minimum: 50
          maximum: 50000
        voltage_ratio:
          type: "string"
          pattern: "^\\d+/\\d+$"
        location_id:
          type: "string"
          format: "uuid"
```

### 8.2 Scene Template & Assembly Recipe

```yaml
# template/scene-templates.yaml
scene_templates:
  - id: "scene.park.smart-community"
    version: "1.0.0"
    name: "智慧社区标准场景"
    description: "覆盖供配电、给排水、安防、环境、公共设施的社区级数字孪生场景"
    
    # 场景拓扑（引用 Asset Template）
    topology:
      - template: "tpl.park.energy.transformer"
        count: "1..2"
      - template: "tpl.park.energy.switchgear"
        count: "2..6"
      - template: "tpl.park.facility.pump"
        count: "2..8"
      - template: "tpl.park.environment.air-quality-station"
        count: "1..3"
      - template: "tpl.park.security.camera-ptz"
        count: "10..50"
    
    # 场景级 KPI 定义
    kpis:
      - ref: "kpi.park.energy.efficiency"
      - ref: "kpi.park.water.leakage-rate"
      - ref: "kpi.park.security.coverage"
    
    # 场景级仪表盘布局
    dashboard_layout: "dashboards/smart-community-layout.json"

# template/assembly-recipes.yaml
assembly_recipes:
  - id: "recipe.park.smart-community.standard"
    version: "1.0.0"
    scene_template: "scene.park.smart-community"
    
    # 组装步骤（声明式，由编排引擎执行）
    steps:
      - name: "deploy_energy_backbone"
        action: "instantiate_template"
        params:
          template: "tpl.park.energy.transformer"
          count: 2
          placement: "auto"
      - name: "deploy_water_system"
        action: "instantiate_template"
        params:
          template: "tpl.park.facility.pump"
          count: 4
      - name: "bind_telemetry"
        action: "apply_mapping_profiles"
        params:
          profile_set: "modbus-default"
      - name: "apply_alarms"
        action: "instantiate_alarm_rules"
        params:
          rule_set: "alm.park.energy.*"
      - name: "apply_sops"
        action: "instantiate_sops"
        params:
          sop_set: "sop.park.*"
      - name: "configure_dashboard"
        action: "render_dashboard"
        params:
          layout: "dashboards/smart-community-layout.json"
```

> **P0-05 修正**：原 SPEC 模板缺乏版本、实例化参数校验、组装编排。现模板**强制版本化**、**参数 JSON Schema 校验**、**引用而非内联**点位/能力/关系，**Assembly Recipe 标准化组装流程**。

---

## 9. Alarm / SOP / Workflow Contracts

### 9.1 Alarm Definition（引用 Point Semantic，而非硬编码表达式）

```yaml
# application/alarms.yaml
alarm_definitions:
  - id: "alm.park.energy.transformer.overload"
    version: "1.0.0"
    name: "变压器过载告警"
    severity: "critical"
    
    # 语义化触发条件（引用 Point + 规则引擎 DSL）
    condition:
      type: "threshold"
      point: "point.park.energy.transformer.active-power"
      operator: ">"
      threshold: "{{ asset.rated_capacity_kva * 0.9 * 0.85 }}"  # 模板参数化
      duration: "60s"
      evaluation_window: "5m"
    
    # 告警增强信息
    enrichment:
      - point: "point.park.energy.transformer.temperature-winding"
      - point: "point.park.energy.transformer.load-rate"
    
    # 自动处置建议（引用 SOP）
    auto_response:
      - action: "notify"
        targets: ["role:energy-manager", "role:facility-operator"]
      - action: "create_work_order"
        template: "wo.park.energy.transformer.overload-investigation"
      - action: "suggest_sop"
        sop_ref: "sop.park.energy.transformer.overload-response"
    
    # 抑制规则
    suppression:
      - condition: "maintenance_mode == true"
      - condition: "alm.park.energy.transformer.overload.active_count > 3"
        action: "escalate_to_critical"
```

### 9.2 SOP & Work Order Template

```yaml
# application/sops.yaml
sop_templates:
  - id: "sop.park.energy.transformer.overload-response"
    version: "1.0.0"
    name: "变压器过载应急响应 SOP"
    trigger_alarm: "alm.park.energy.transformer.overload"
    
    steps:
      - seq: 1
        title: "现场确认负载情况"
        type: "manual"
        assignee_role: "facility-operator"
        estimated_minutes: 5
        checklist:
          - "读取变压器三相电流"
          - "检查是否有异常发热/异响"
          - "确认二次回路无短路"
      
      - seq: 2
        title: "负载转移评估"
        type: "decision"
        assignee_role: "energy-manager"
        estimated_minutes: 10
        conditions:
          - "如果负载 > 95% 额定且持续 > 15min：执行负载转移"
          - "如果负载 90-95%：加强监视，30min 复核"
      
      - seq: 3
        title: "执行负载转移"
        type: "automated"
        capability: "cap.park.energy.load-transfer"
        params:
          source: "{{ alarm.asset_id }}"
          target_strategy: "least_loaded"
        requires_approval: "C2"
      
      - seq: 4
        title: "恢复确认与归档"
        type: "manual"
        assignee_role: "facility-operator"
        checklist:
          - "确认负载恢复正常范围"
          - "记录处理过程、时长、责任人"
          - "关闭工单"

# application/work-orders.yaml
work_order_templates:
  - id: "wo.park.energy.transformer.overload-investigation"
    version: "1.0.0"
    title: "变压器过载原因调查工单"
    category: "investigation"
    priority: "high"
    sla_hours: 24
    required_roles: ["energy-engineer"]
    form_schema: "schemas/wo-transformer-overload.json"
```

---

## 10. Versioning & Migration Strategy

### 10.1 语义化版本规范（P0-06 强制）

| 版本段 | 含义 | Asset Package 约束 |
|--------|------|-------------------|
| **MAJOR** | 不兼容的层契约变更（L1-L5 任一层 Breaking Change） | 需完整迁移脚本、双向兼容窗口 ≥ 1 个 Minor |
| **MINOR** | 向后兼容的新增资产类型、能力、模板、告警、SOP | 仅需增量迁移脚本、自动应用 |
| **PATCH** | 修复 Bug、调整参数默认值、文档更新、非功能性优化 | 无迁移脚本、热更新 |

> **预发布标识**：`alpha`（内部验证）、`beta`（灰度试用）、`rc`（发布候选）

### 10.2 迁移脚本目录结构

```
operations/migrations/
├── v0.1.0-to-v0.2.0/
│   ├── up.py                     # 正向迁移（数据、Schema、配置）
│   ├── down.py                   # 回滚脚本（必须可逆）
│   ├── validate.py               # 迁移后校验脚本
│   └── changelog.md              # 变更说明
├── v0.2.0-to-v1.0.0/
│   └── ...
```

### 10.3 迁移执行契约

```yaml
# operations/release-gates.yaml
release_gates:
  pre_migration:
    - "backup_core_database"
    - "backup_asset_package_config"
    - "verify_golden_assets_healthy"
  
  migration:
    - "execute_up_script"
    - "run_validate_script"
    - "verify_golden_path_pass"
  
  post_migration:
    - "smoke_test_all_scenarios"
    - "performance_baseline_compare"
    - "update_documentation"
  
  rollback_trigger:
    - "validate_script_failed"
    - "golden_path_regression"
    - "performance_degradation > 20%"
  
  rollback_procedure:
    - "execute_down_script"
    - "restore_backups"
    - "verify_golden_assets_healthy"
    - "notify_stakeholders"
```

---

## 11. Zero-Code 重新定义

### 11.1 定义澄清（P0-07 关键修正）

> **Zero-Code ≠ 无 YAML/Helm**。Zero-Code 是**面向业务配置人员的产品能力**：
> - **工程视角**：Package 开发者编写 YAML/Helm/Plugin 代码（这是"工程代码"）
> - **产品视角**：业务配置人员在 UI 中通过**可视化拖拽、表单配置、向导引导**完成资产实例化、场景组装、告警调优、SOP 定制，**全程不写一行代码、不碰 YAML、不懂 Helm**

### 11.2 Zero-Code 产品能力矩阵

| 能力域 | 产品化交付形态 | 底层支撑 |
|--------|----------------|----------|
| **资产建模** | 可视化建模器（节点/边画布） | Asset Template + Ontology 校验器 |
| **场景组装** | 场景向导（分步表单+拓扑预览） | Assembly Recipe 执行引擎 |
| **点位接入** | 协议适配向导（厂商/型号选择→自动生成 Mapping） | Point Semantic + Mapping Profile 库 |
| **告警调优** | 阈值可视化编辑器（滑块+实时预览） | Alarm Definition + 规则引擎 |
| **仪表盘** | 低代码 Dashboard Designer（组件库+布局） | Scene Template + Widget 库 |
| **SOP 定制** | 流程设计器（BPMN-like 可视化） | SOP Template + Workflow 引擎 |
| **AI 工具配置** | Prompt 模板管理、工具注册表单 | AI Tool Manifest + RAG 索引 |

> **P0-07 修正**：原 SPEC 将"Zero-Code"等同于"Helm values 参数化"，这是工程视角的误读。**产品级 Zero-Code 必须有独立的 UI 交付件（Web Components/插件），不依赖运维人员操作 Kubernetes**。

---

## 12. Core / Package Boundary（核心/包边界）

### 12.1 边界契约（P0-08 红线）

```
┌─────────────────────────────────────────────────────────────────┐
│                    DT-Lite Core Platform                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Entity  │ │ Asset   │ │Property │ │Relationship│ │ Scene   │  │
│  │ Service │ │ Service │ │ Service │ │ Service  │ │ Service │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
│       │           │           │           │           │        │
│  ┌────▼───────────▼───────────▼───────────▼───────────▼────┐  │
│  │              Core Platform Contracts (gRPC/REST)         │  │
│  └──────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────│───────────────────────────────────┘
                              │ Dependency (Consumer only)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Smart Park Asset Package                       │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐          │
│  │ L1 Ont.  │ │ L2 Cap.   │ │ L3 Tpl.  │ │ L4 App.  │          │
│  └──────────┘ └───────────┘ └──────────┘ └──────────┘          │
│  ┌──────────┐                                                    │
│  │ L5 Ops   │  (Migration, Golden Asset, Release Gate)          │
│  └──────────┘                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 红线规则（违反即构建失败）

| 红线编号 | 规则 | 说明 |
|----------|------|------|
| **BL-01** | Package **不得**包含任何基础设施部署定义（StatefulSet、Operator、CRD 除 Core Platform 提供外） | PostgreSQL、TimescaleDB、Redis、EMQX、MinIO、Neo4j、Kafka 等均由 Platform Helm 管理 |
| **BL-02** | Package **不得**定义 Core Platform 的数据库 Schema、索引、迁移 | 仅通过 Core Platform API 消费数据 |
| **BL-03** | Package **不得**绑定特定网络拓扑、存储类、Ingress 域名 | 通过 Core Platform 标准接口（ServiceEndpoint）消费 |
| **BL-04** | Package **不得**包含任何 Sidecar、InitContainer、DaemonSet 定义 | 运行时形态由 Platform 统一管控 |
| **BL-05** | Package 仅交付：**YAML/JSON 配置文件**、**Plugin 容器镜像**、**UI 组件包**、**迁移脚本** | 无可执行二进制、无基础设施代码 |

---

## 13. Golden Asset / Golden Path

### 13.1 Golden Asset 定义（P0-09 验证基石）

> **Golden Asset**：**10-20 个**跨领域、跨层级的标准化资产实例，覆盖 **L1 Ontology → L2 Capability → L3 Template → L4 Application → L5 Operations** 完整链路，作为**架构正确性的唯一验证基准**。

### 13.2 Golden Asset 清单（Stage A 必须跑通）

| # | 资产类型 | 场景覆盖 | 验证链路 |
|---|----------|----------|----------|
| GA-01 | `asset.park.energy.transformer` | 所有场景 | 点位采集→聚合→告警→仪表盘→SOP→工单 |
| GA-02 | `asset.park.energy.water-meter` | 社区/商场/学校/医院 | 点位采集→费用计算→报表→异常告警 |
| GA-03 | `asset.park.facility.chiller` | 商场/医院/数据中心/产业园 | 工况监测→能效分析→预测性维护 SOP |
| GA-04 | `asset.park.facility.pump` | 所有场景 | 启停控制(C2)→联锁保护(C4)→运行记录 |
| GA-05 | `asset.park.security.camera-ptz` | 所有场景 | 云台控制(C1)→预置位巡航→事件录像关联 |
| GA-06 | `asset.park.environment.air-quality-station` | 社区/学校/医院/产业园 | 多参数采集→超标告警→新风联动(C2) |
| GA-07 | `asset.park.transport.charging-pile` | 商场/产业园/社区 | 充电会话→计费→故障告警→远程复位(C2) |
| GA-08 | `asset.park.facility.elevator` | 社区/商场/医院/学校 | 故障码解析→困人告警→维保工单自动派发 |
| GA-09 | `asset.park.management.bas-panel` | 商场/医院/数据中心/产业园 | BACnet 点位映射→策略下发(C1)→能耗统计 |
| GA-10 | `asset.park.energy.switchgear` | 所有场景 | 位置信号→操作联锁(C4)→操作票记录 |

> **扩展至 20 个**：Stage B 补充 `asset.park.energy.pv-inverter`、`asset.park.energy.storage-bess`、`asset.park.facility.ahu`、`asset.park.environment.water-quality`、`asset.park.security.access-controller`、`asset.park.operation.waste-compactor`、`asset.park.management.parking-lot`、`asset.park.transport.agv`、`asset.park.facility.fire-pump`、`asset.park.environment.noise-monitor`

### 13.3 Golden Path 验证流水线（CI 门禁）

```yaml
# .github/workflows/golden-path.yml
jobs:
  golden-path-validation:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy Core Platform (Kind/K3d)
      - name: Install Asset Package (Helm)
      - name: Instantiate Golden Assets (10-20)
        run: |
          for asset in $(cat operations/golden-assets.yaml | yq '.assets[].id'); do
            cli asset instantiate --template $asset --params golden-params/$asset.json
          done
      - name: Verify L1 Ontology Resolution
        run: cli verify ontology --assets golden-assets
      - name: Verify L2 Capability Binding
        run: cli verify capability --assets golden-assets
      - name: Verify L3 Template Instantiation
        run: cli verify template --assets golden-assets
      - name: Verify L4 Application Rendering
        run: cli verify dashboard alarm sop --assets golden-assets
      - name: Verify L5 Operations
        run: cli verify migration rollback --assets golden-assets
      - name: Performance Baseline
        run: cli benchmark --assets golden-assets --threshold latency_p99<200ms
      - name: Publish Golden Path Report
        if: always()
```

---

## 14. Architecture Alignment Matrix

| 评审维度 | 原 SPEC 状态 | 重构后状态 | 对齐证据 |
|----------|-------------|------------|----------|
| **五层架构边界** | 模糊、混合 | **强制冻结、单向依赖** | `layer-dependencies` + CI 校验 |
| **Manifest 单一事实源** | 无 | **asset-package.yaml 强制** | Schema 校验 + 发布门禁 |
| **依赖图谱可校验** | 无 | **DG-01~05 强制执行** | CI 门禁集成 |
| **命名规范统一** | 3 套共存 | **asset.park.<sub>.<type> 冻结** | 迁移脚本 + 重命名清单 |
| **Point 语义/协议分离** | 耦合 | **Point Definition + Mapping Profile** | Schema 定义 + 多协议示例 |
| **Capability/算法分离** | 耦合 | **Capability Contract + Plugin** | Plugin SDK + 接口契约 |
| **控制安全分级** | 无 | **C0-C4 契约强制** | 审计日志 Schema + 权限矩阵 |
| **模板可实例化/可校验** | 示例性 | **JSON Schema + Assembly Recipe** | 实例化 CLI + 校验器 |
| **Zero-Code 产品级定义** | 工程视角 | **UI 交付件 + 可视化能力矩阵** | 前端组件库规划 |
| **Core/Package 边界** | 混淆 | **红线 BL-01~05 强制** | CI 扫描禁止基础设施定义 |
| **Golden Asset 验证** | 无 | **10-20 资产全链路 CI** | Golden Path Pipeline |
| **版本/迁移治理** | 无 | **SemVer + 双向迁移 + 门禁** | Release Gate Checklist |
| **Scope Lock 执行** | 无 | **Stage A-F 串行 + 门禁** | 项目管理工具集成 |

---

## 15. Scope Lock（范围锁定）

### 15.1 绝对禁止（P0 级）

| 编号 | 禁止事项 | 违反后果 |
|------|----------|----------|
| **SL-01** | Stage A 完成前启动任何场景并行开发 | 架构评审不通过、资源冻结 |
| **SL-02** | Golden Path 未 100% 通过发布任何 Industry Extension | 发布管道阻断 |
| **SL-03** | Package 中引入任何基础设施部署代码 | CI 构建失败（BL-01 扫描） |
| **SL-04** | 修改 Core Platform 契约而不发布 Major 版本 | 依赖解析失败、回滚强制 |
| **SL-05** | 命名规范出现非 `asset.park.<sub>.<type>` 格式 | 代码审查阻断、自动重命名 PR |
| **SL-06** | Point 定义中硬编码协议地址 | Schema 校验失败 |
| **SL-07** | Capability 内嵌算法逻辑 | 架构审查退回、重构要求 |
| **SL-08** | 控制指令无 C0-C4 分级 | 安全审计不通过、上线禁止 |

### 15.2 条件允许（P1 级，需架构评审通过）

| 编号 | 事项 | 前置条件 |
|------|------|----------|
| **CA-01** | 新增 Sub Domain | L1 Ontology 已扩展、命名规范通过审查 |
| **CA-02** | 新增 Capability | L2 Contract 通过接口兼容性测试 |
| **CA-03** | 新增 Plugin 算子 | Plugin SDK 版本兼容、沙箱测试通过 |
| **CA-04** | 场景扩展包发布 | Common Asset Pack 已 Stable、Golden Path 覆盖 |

---

## 16. Release Gate Checklist

| 门禁 | 检查项 | 通过标准 | 自动化 |
|------|--------|----------|--------|
| **Gate 1: Lint & Schema** | YAML/JSON Schema 校验、命名规范、跨层引用 | 0 Error、0 Warning | ✅ CI |
| **Gate 2: Unit Test** | 核心模块单测（Core/Identity/Telemetry/Ontology/Deployment/Template） | 覆盖率 ≥ 60%（核心服务）、≥ 80% 目标 | ✅ CI |
| **Gate 3: Golden Path** | 10-20 Golden Asset 全链路实例化验证 | 100% 通过、性能基线达标 | ✅ CI |
| **Gate 4: Architecture Scan** | 依赖图谱校验、循环依赖、红线扫描 | 0 Violation | ✅ CI |
| **Gate 5: Dependency Scan** | 核心依赖版本区间、CVE 扫描、许可证合规 | 0 Critical/High CVE、许可证兼容 | ✅ CI |
| **Gate 6: Docker Build** | 多架构镜像构建、签名、SBOM 生成 | 镜像推送成功、签名验证 | ✅ CI |
| **Gate 7: Helm Render** | `values-smart-park.yaml` 渲染、kubeval、干跑部署 | 0 Error、资源配额合规 | ✅ CI |
| **Gate 8: Security Scan** | Trivy 镜像扫描、Bandit 代码扫描、密钥泄露检测 | 0 Critical、0 Secret Leak | ✅ CI |
| **Gate 9: Integration Smoke** | Kind/K3d 部署 Core + Package，核心 API 冒烟 | 健康检查通过、核心流程跑通 | ✅ CI |
| **Gate 10: Release Approval** | 架构评审签字、安全审计签字、产品负责人签字 | 3 方签字齐全 | 🔄 Manual |

---

## 17. 交付清单

### 17.1 Stage A 交付物（Golden Foundation）

```
dt-lite-smart-park/
├── asset-package.yaml                 # Manifest（单一事实源）
├── ontology/
│   └── asset-ontology.yaml            # L1: 资产本体、关系、JSON-LD Context
├── capability/
│   └── capability-contracts.yaml      # L2: 能力契约、算子注册表
├── template/
│   ├── asset-templates.yaml           # L3: 资产模板（含实例化参数 Schema）
│   ├── scene-templates.yaml           # L3: 场景模板（拓扑、KPI、布局）
│   └── assembly-recipes.yaml          # L3: 组装配方（声明式步骤）
├── application/
│   ├── dashboards/                    # L4: 仪表盘布局、Widget 定义
│   ├── alarms.yaml                    # L4: 告警定义（语义化条件）
│   ├── sops.yaml                      # L4: SOP 模板（步骤、决策、自动化）
│   ├── work-orders.yaml               # L4: 工单模板
│   └── ai-tools.yaml                  # L4: AI Tool 清单
├── operations/
│   ├── golden-assets.yaml             # L5: Golden Asset 清单（10-20 个）
│   ├── migrations/                    # L5: 版本迁移脚本（up/down/validate）
│   └── release-gates.yaml             # L5: 发布门禁清单
├── plugins/                           # 算子 Plugin（独立版本、容器镜像）
│   ├── energy-aggregator/
│   ├── energy-cost-calculator/
│   ├── predictive-maintenance/
│   └── load-transfer/
├── mapping-profiles/                  # 协议映射配置
│   ├── modbus/
│   ├── opcua/
│   ├── mqtt/
│   └── bacnet/
├── point-definitions/                 # Point 语义定义（协议无关）
│   ├── energy/
│   ├── facility/
│   ├── security/
│   ├── environment/
│   └── transport/
├── schemas/                           # JSON Schema 校验文件
│   ├── instantiation-params/
│   ├── plugin-config/
│   └── work-order-forms/
└── tests/
    ├── golden-path/                   # Golden Path 验证脚本
    ├── contract/                      # 契约测试
    └── migration/                     # 迁移测试
```

### 17.2 Stage B-F 增量交付

| 阶段 | 新增目录/文件 | 版本策略 |
|------|--------------|----------|
| Stage B | `common-assets.yaml`、共享模板/能力 | Minor 版本 |
| Stage C | `golden-assets.yaml` 扩展至 20、验证报告 | Patch 版本 |
| Stage D | `scenario-extensions/<scenario>.yaml` | Minor 版本（每场景独立） |
| Stage E | `control-contracts.yaml`、AI 编排规则 | Minor 版本 |
| Stage F | `migration-toolkit`、合规报告模板 | Patch 版本 |

---

## 18. 实施路线图与里程碑

| 里程碑 | 时间窗 | 关键产出 | 验收标准 |
|--------|--------|----------|----------|
| **M1: Architecture Freeze** | Week 1-2 | 本文档确认、Scope Lock 签字 | 评审通过、红线锁定 |
| **M2: L1-L2 Core Schemas** | Week 3-4 | `asset-ontology.yaml`、`capability-contracts.yaml`、Point Definitions | Schema 校验通过、命名规范 100% 合规 |
| **M3: L3 Templates & Recipes** | Week 5-6 | 3 类模板、Assembly Recipe、实例化参数 Schema | 10 个 Golden Asset 模板实例化成功 |
| **M4: L4 Application Configs** | Week 7-8 | Dashboards、Alarms、SOPs、Work Orders、AI Tools | 仪表盘渲染、告警触发、SOP 执行全链路跑通 |
| **M5: L5 Operations & Golden Path** | Week 9-10 | `golden-assets.yaml`（10 个）、迁移脚本、Golden Path Pipeline | CI 门禁 10/10 通过、性能基线建立 |
| **M6: Stage A Release (v0.1.0-alpha)** | Week 11 | 完整 Asset Package、Helm Chart、文档 | Release Gate 10/10 通过、架构评审复盘通过 |
| **M7: Stage B Common Asset Pack** | Week 12-14 | 30+ 通用资产、共享能力/模板 | 覆盖 7 场景 80%+ 需求、回归测试通过 |
| **M8: Stage C Golden Path Hardening** | Week 15-16 | 20 Golden Asset、压力测试报告 | 并发 1000 资产、P99 < 200ms、零回归 |
| **M9: Stage D-F 迭代交付** | Week 17+ | 按场景增量、控制安全、治理工具 | 各场景独立版本、合规发布 |

---

## 19. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| Core Platform 契约不稳定导致 Package 频繁 Breaking Change | **High** | 引入 Contract Testing（Pact）、双向兼容窗口、Major 版本严格管控 |
| 七大场景业务差异大，Common Asset Pack 覆盖率不足 | **Medium** | Stage B 引入领域专家评审、建立「共性 vs 个性」决策矩阵 |
| Plugin 生态建设滞后，Capability 无可用算子 | **High** | 优先建设 Plugin SDK、提供 3-5 个参照实现、建立 Plugin 市场机制 |
| Zero-Code UI 组件库开发周期长，阻塞产品交付 | **Medium** | 采用渐进式交付：先 CLI/向导，再可视化建模器，最后全拖拽设计器 |
| Golden Path 维护成本高，版本升级易失效 | **Medium** | 自动化验证流水线、Golden Asset 版本化管理、回归测试强制门禁 |
| 团队对新架构（分层、契约、Plugin）理解不一 | **High** | 架构工作坊、ADR 文档化、Code Review 强制架构合规检查 |

---

## 附录 A：P0/P1 问题对照表

| 问题编号 | 问题描述 | 重构修正 | 文档位置 |
|----------|----------|----------|----------|
| **P0-01** | 五层架构边界模糊 | 强制冻结分层、单向依赖 | §1.1 |
| **P0-02** | Manifest 缺失单一事实源 | `asset-package.yaml` 规范 | §2.1 |
| **P0-03** | 跨层引用无校验机制 | DG-01~05 校验规则 | §3.2 |
| **P0-04** | 命名规范混乱（3 套共存） | `asset.park.<sub>.<type>` 冻结 | §4.1 |
| **P0-05** | 模板缺乏实例化/校验/编排 | JSON Schema + Assembly Recipe | §8.1 |
| **P0-06** | 版本/迁移策略缺失 | SemVer + 双向迁移 + 门禁 | §10.1 |
| **P0-07** | Zero-Code 工程视角误读 | 产品级 UI 交付件定义 | §11.1 |
| **P0-08** | Core/Package 边界混淆 | 红线 BL-01~05 强制 | §12.2 |
| **P0-09** | Golden Asset 验证缺失 | 10-20 资产全链路 CI | §13.2 |
| **P1-01** | Point 语义与协议耦合 | Point Definition + Mapping Profile | §5.2 |
| **P1-02** | Capability 与算法耦合 | Capability Contract + Plugin | §6.1 |
| **P1-03** | 控制安全分级缺失 | C0-C4 五级契约 | §7.1 |
| **P1-04** | 场景并行开发风险 | Stage A-F 串行执行 | §1.2 |
| **P1-05** | 协议地址硬编码 | 多协议适配 Mapping Profile | §5.3 |
| **P1-06** | 审计日志不完整 | 分级审计字段定义 | §7.2 |

---

## 附录 B：参考文档

| 文档 | 路径 | 用途 |
|------|------|------|
| 原始 SPEC v1.0 | `docs/architecture/asset-packages/smart-park/SPEC.md` | 基线参考 |
| v2.0 详细规格 | `docs/architecture/asset-packages/smart-park/DT-Lite_V4.0_Smart_Park_Industry_Asset_Package_Specification_v2.0.md` | 技术细节 |
| 架构对齐评审 | `docs/architecture/asset-packages/smart-park/DT-Lite_V4.0_Smart_Built_Environment_Asset_Package_Architecture_Alignment_Scope_Lock_Review.md` | 问题清单 |
| 重构架构设计 | 本文档 | 执行基线 |

---

## 附录 C：变更历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-08-15 | Platform Team | 原始规范定义 |
| v2.0 | 2026-08-25 | Architecture Team | 详细技术规格（Universal Assembly Contract） |
| v3.0-Reformulated | 2026-09-11 | Architecture Review Board | 基于 Conditional Pass 评审重构，解决 43 个 P0/P1 问题 |

---

> **文档状态**：正式版 v3.0-Reformulated  
> **评审结论**：Conditional Pass（需执行 Scope Lock 后方可进入 Phase 2 工程开发）  
> **下一步行动**：确认 M1 Architecture Freeze，启动 Stage A Golden Foundation 开发

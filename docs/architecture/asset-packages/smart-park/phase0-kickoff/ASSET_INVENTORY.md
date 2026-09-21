# Smart Park v1.0 制品清单确认单

**负责人**: Industry Lead
**截止**: Day 3 (Sep 23) 09:00
**优先级**: P0

---

## 🎯 目标

确认 Smart Park v1.0 Asset Package 全部 8 类制品来源、数量、路径，确保与 Freeze Report 基线一致。

---

## 📋 制品清单总览

| # | 制品类型 | 最小数量 | 来源文档 | 交付路径 | 状态 |
|---|----------|----------|----------|----------|------|
| 1 | `asset-package.yaml` | 1 份 | Freeze Report §Package Directory Structure | `packages/smart-park/v1.0/` | 📋 待创建 |
| 2 | AssetTemplate | ≥ 20 个 | Freeze Report §15 类最小量 | `packages/smart-park/v1.0/templates/assets/` | 📋 待创建 |
| 3 | CompositeAssetTemplate | ≥ 10 个 | Freeze Report §Composite Asset | `packages/smart-park/v1.0/templates/composite/` | 📋 待创建 |
| 4 | IntegrationProfile | ≥ 8 个 | Freeze Report §External Integration | `packages/smart-park/v1.0/profiles/integration/` | 📋 待创建 |
| 5 | MappingProfile | ≥ 200 个 | Freeze Report §200+ Mappings | `packages/smart-park/v1.0/profiles/mappings/` | 📋 待创建 |
| 6 | ScenarioTemplate | 10 个 | Freeze Report §Golden Scenarios | `packages/smart-park/v1.0/scenarios/` | 📋 待创建 |
| 7 | `values-smart-park.yaml` | 1 份 | Freeze Report §Helm Deployment | `packages/smart-park/v1.0/helm/` | 📋 待创建 |
| 8 | `release-smart-park-v1.0.sh` | 1 份 | 自编 | `packages/smart-park/v1.0/` | 📋 待创建 |

---

## 📊 详细制品溯源

### **1. AssetTemplate (≥20 个)**

| ID | 资产类型 | 代码 | 来源 UAA | 关键属性 | 状态 |
|----|----------|------|----------|----------|------|
| AT-01 | 建筑 | `asset.park.building` | UAA-02 | name, area, floors, coordinates | 📋 |
| AT-02 | 电梯 | `asset.park.elevator` | UAA-02 | speed, capacity, floor, status | 📋 |
| AT-03 | 空调 | `asset.park.hvac` | UAA-03 | temp, humidity, mode, power | 📋 |
| AT-04 | 照明 | `asset.park.lighting` | UAA-03 | brightness, color, schedule | 📋 |
| AT-05 | 消防烟感 | `asset.park.fire.smoke_detector` | UAA-06 | alarm, battery, last_test | 📋 |
| AT-06 | 消防喷淋 | `asset.park.fire.sprinkler` | UAA-06 | status, flow, pressure | 📋 |
| AT-07 | 视频监控 | `asset.park.security.camera` | UAA-05 | resolution, fov, recording | 📋 |
| AT-08 | 门禁 | `asset.park.security.access_control` | UAA-05 | door_state, lock_state, audit | 📋 |
| AT-09 | 停车道闸 | `asset.park.parking.barrier` | UAA-04 | status, vehicle_count, plate | 📋 |
| AT-10 | 充电桩 | `asset.park.parking.charger` | UAA-04 | power, status, connector_type | 📋 |
| AT-11 | 水表 | `asset.park.utility.water_meter` | UAA-03 | flow, total, quality | 📋 |
| AT-12 | 电表 | `asset.park.utility.electric_meter` | UAA-03 | voltage, current, power_factor | 📋 |
| AT-13 | 燃气表 | `asset.park.utility.gas_meter` | UAA-03 | flow, pressure, concentration | 📋 |
| AT-14 | 热力表 | `asset.park.utility.heat_meter` | UAA-03 | temp_supply, temp_return, flow | 📋 |
| AT-15 | 配电箱 | `asset.park.electrical.distribution_panel` | UAA-03 | circuit_count, load, status | 📋 |
| AT-16 | 变压器 | `asset.park.electrical.transformer` | UAA-03 | capacity, temp, load_percent | 📋 |
| AT-17 | 锅炉 | `asset.park.hvac.boiler` | UAA-03 | temp_supply, temp_return, flame | 📋 |
| AT-18 | 冷却塔 | `asset.park.hvac.cooling_tower` | UAA-03 | temp_supply, temp_return, fan | 📋 |
| AT-19 | 电梯群控 | `asset.park.elevator.group_controller` | UAA-02 | dispatch_algorithm, stats | 📋 |
| AT-20 | 能源看板 | `asset.park.dashboard.energy` | UAA-06 | kpi_realtime, kpi_daily | 📋 |

### **2. CompositeAssetTemplate (≥10 个)**

| ID | 组合资产 | 组成 | 继承能力 | 状态 |
|----|----------|------|----------|------|
| CAT-01 | 楼层 | 建筑 + 空调 + 照明 + 电梯 | 环境监测、能耗管理 | 📋 |
| CAT-02 | 会议室 | 门禁 + 照明 + 空调 + 投影 | 预约管理、环境调节 | 📋 |
| CAT-03 | 停车场 | 道闸 + 充电桩 + 监控 | 车辆管理、充电调度 | 📋 |
| CAT-04 | 能源系统 | 电表 + 水表 + 燃气表 + 热力表 | 能耗统计、异常告警 | 📋 |
| CAT-05 | 消防系统 | 烟感 + 喷淋 + 监控 + 门禁 | 火灾预警、应急疏散 | 📋 |
| CAT-06 | 安防系统 | 监控 + 门禁 + 道闸 | 入侵检测、人员追踪 | 📋 |
| CAT-07 | HVAC 系统 | 空调 + 锅炉 + 冷却塔 | 温控优化、节能调度 | 📋 |
| CAT-08 | 配电系统 | 变压器 + 配电箱 | 负荷监控、故障预警 | 📋 |
| CAT-09 | 公共区域 | 照明 + 空调 + 监控 + 门禁 | 环境舒适、节能运行 | 📋 |
| CAT-10 | 数据中心 | 精密空调 + UPS + 监控 | 温度控制、能耗优化 | 📋 |

### **3. IntegrationProfile (≥8 个)**

| ID | 协议 | 系统类别 | 适配场景 | 状态 |
|----|------|----------|----------|------|
| IP-01 | BACnet/IP | 楼宇自控 | HVAC、照明、门禁 | 📋 |
| IP-02 | BACnet/MSTP | 楼宇自控 | 老旧楼宇改造 | 📋 |
| IP-03 | Modbus TCP | 工业/能源 | 电表、水表、PLC | 📋 |
| IP-04 | Modbus RTU | 工业/能源 | 串口设备网关 | 📋 |
| IP-05 | OPC UA | 工业/数据中心 | 服务器、SCADA | 📋 |
| IP-06 | MQTT | IoT/边缘 | 传感器、边缘网关 | 📋 |
| IP-07 | REST/HTTP | 应用集成 | 第三方 API、Webhook | 📋 |
| IP-08 | OCPP | 电动汽车 | 充电桩管理 | 📋 |

### **4. MappingProfile (≥200 个)**

**按协议分类**:
- BACnet: 50+ 映射（点类型全覆盖）
- Modbus: 40+ 映射（寄存器类型全覆盖）
- OPC UA: 30+ 映射（节点类型全覆盖）
- MQTT: 40+ 映射（Topic 模式全覆盖）
- REST: 30+ 映射（API 端点全覆盖）
- OCPP: 10+ 映射（充电会话全覆盖）

**按场景分类**:
- 能源管理: 50+ 映射
- 环境控制: 40+ 映射
- 安防消防: 40+ 映射
- 停车充电: 30+ 映射
- 楼宇自控: 40+ 映射

### **5. ScenarioTemplate (10 个)**

| ID | 场景名称 | 覆盖子域 | 关键流程 | 状态 |
|----|----------|----------|----------|------|
| GS-01 | 能源看板 | utility | 实时能耗 → KPI → 告警 | 📋 |
| GS-02 | 环境舒适度 | hvac,lighting | 温度/照度 → 自动调节 | 📋 |
| GS-03 | 消防预警 | fire | 烟感 → 确认 → 联动 | 📋 |
| GS-04 | 安防入侵 | security | 监控 → 识别 → 告警 | 📋 |
| GS-05 | 停车引导 | parking | 空位 → 导航 → 道闸 | 📋 |
| GS-06 | 充电管理 | parking | 预约 → 充电桩 → 结算 | 📋 |
| GS-07 | 会议预约 | meeting | 预约 → 环境准备 → 释放 | 📋 |
| GS-08 | 能耗优化 | energy | 需求响应 → 负荷调节 | 📋 |
| GS-09 | 设备运维 | maintenance | 告警 → SOP → 工单 | 📋 |
| GS-10 | 零代码端到端 | all | BIM → 接入 → 发布 → 零代码 | 📋 |

---

## ✅ 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | 全部 8 类制品入库 | `ls packages/smart-park/v1.0/` |
| 2 | AssetTemplate ≥ 20 个 | 计数验证 |
| 3 | CompositeAssetTemplate ≥ 10 个 | 计数验证 |
| 4 | IntegrationProfile ≥ 8 个 | 计数验证 |
| 5 | MappingProfile ≥ 200 个 | 计数验证 |
| 6 | ScenarioTemplate = 10 个 | 计数验证 |
| 7 | `helm lint` 通过 | `helm lint packages/smart-park/v1.0/helm/` |
| 8 | 4 环境渲染无报错 | `helm template` × 4 |

---

## 📅 交付时间表

| 日期 | 任务 | 交付物 |
|------|------|--------|
| **Day 1 (Sep 21)** | 制品清单确认 | 本文档 |
| **Day 2 (Sep 22)** | 开始创建制品 | AssetTemplate × 5 |
| **Day 3 (Sep 23)** | 继续创建制品 | AssetTemplate × 10 + Composite × 5 |
| **Day 4 (Sep 24)** | 完成核心制品 | 全部 Template + Profile |
| **Day 5 (Sep 25)** | 最终验收 | 完整制品包 + 渲染测试 |

---

## 📎 关联文档

- `p004-smart-park-packaging.md`
- Freeze Report §Smart Park Production Baseline
- UAA-02~UAA-09 Final Reports

---

**文档版本**: v1.0
**创建时间**: 2026-09-21 20:05
**负责人**: Industry Lead (dt_manager 代理)

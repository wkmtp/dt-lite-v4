# DT-Lite V4.0 Task 15: Adapter Layer 开发工作指令

**指令生效时间**: 2026-09-07 即刻  
**执行角色**: dt_code (并行开发团队)  
**下次同步会议**: 2026-09-08 10:00 (Day 1 进度汇报)

---

## 🎯 核心目标

**Task 15: Adapter Layer** — 构建协议中立的适配器运行时，实现 BACnet/Modbus/MQTT/OPC-UA 适配器，打通物理设备到数字孪生的数据通道。

---

## 📋 并行工作流分配 (4 个并行泳道)

| 泳道 | 负责模块 | 关键交付物 | 预估工时 | 优先级 |
|------|---------|-----------|----------|--------|
| **A** | **Adapter Core Runtime** | `ProtocolAdapter` 抽象基类、AdapterRegistry、生命周期管理、健康检查 | 1 周 | P0 |
| **B** | **BACnet Adapter** | `BACnetAdapter` 实现 (基于 bacpypes3)、读/写/订阅、设备发现 | 2 周 | P0 |
| **C** | **Modbus Adapter** | `ModbusAdapter` 实现 (基于 pymodbus)、RTU/TCP、寄存器映射 | 1.5 周 | P0 |
| **D** | **MQTT/OPC-UA Adapter + 共享设施** | `MQTTAdapter` (EMQX 集成)、`OPCUAAdapter` (asyncua)、Capability-Adapter 匹配引擎 (ADR-008) | 2 周 | P0 |

---

## 🔧 详细任务拆解

### 泳道 A: Adapter Core Runtime (基础设施先行)

```python
# 目标文件结构 (services/adapter/)
services/adapter/
├── __init__.py
├── contracts.py          # ProtocolAdapter 抽象基类、NormalizedTelemetry/Command 契约
├── registry.py           # AdapterRegistry: 注册、发现、生命周期
├── runtime.py            # AdapterRuntime: 启动/停止、连接池、重试/熔断
├── health.py             # 健康检查、指标暴露
├── exceptions.py         # AdapterError, ConnectionError, ProtocolError
├── models.py             # AdapterConfig, DeviceMapping, CapabilityMatch
├── matching.py           # Capability-Adapter 匹配引擎 (ADR-008 核心)
└── factories.py          # 协议工厂: 根据 capability 创建适配器实例
```

**必须遵守的架构约束 (ARCH-*)**:
- ✅ **ARCH-002**: AI/Service 不直接操作 DB → Adapter 通过 Repository 读取 Device/DataPoint
- ✅ **ARCH-003**: Metadata 驱动 → 适配器配置来自 `DataSource`/`Connection`/`Device` 模型 (JSONB)
- ✅ **ARCH-005**: 配置优先 → 无硬编码协议逻辑，全部通过 Schema 定义
- ❌ **禁止**: 在 Adapter 中引入 `services.telemetry` 直接调用 (应通过契约/事件总线)

**验收标准**:
- [ ] `ProtocolAdapter` 定义: `connect()`, `disconnect()`, `read()`, `write()`, `subscribe()`, `health_check()`
- [ ] `AdapterRegistry` 支持多租户隔离、动态注册/注销
- [ ] `AdapterRuntime` 管理连接池、指数退避重试、熔断器模式
- [ ] 单测覆盖 ≥85%，集成测试覆盖启动/停止/重连流程

---

### 泳道 B: BACnet Adapter (优先级最高)

```python
# 目标文件结构 (services/adapter/bacnet/)
services/adapter/bacnet/
├── __init__.py
├── adapter.py            # BACnetAdapter 实现 ProtocolAdapter
├── client.py             # bacpypes3 封装: 设备发现、ReadProperty、WriteProperty、COV 订阅
├── mapping.py            # DataPoint.key → BACnet ObjectType/Instance/Property 映射
├── discovery.py          # Who-Is/I-Am 设备自动发现
├── cov.py                # Change of Value 订阅管理
└── test_bacnet_adapter.py
```

**关键技术决策**:
- 使用 `bacpypes3` (Python 3.11+ 原生 async 支持)
- 映射规则存储在 `DataPoint.extra_data`:
  ```json
  {
    "bacnet": {
      "object_type": "analogInput",
      "object_instance": 1,
      "property": "presentValue"
    }
  }
  ```
- COV 订阅生命周期由 `AdapterRuntime` 管理，设备离线自动清理

**验收标准**:
- [ ] 读取单个/批量 DataPoint 成功率 ≥99.9%
- [ ] 写入命令 (Command Intent → BACnet WriteProperty) 往返延迟 <200ms
- [ ] COV 订阅自动重订阅、网络抖动不丢数据
- [ ] 设备发现 (Who-Is) 可配置网络段、并发限制

---

### 泳道 C: Modbus Adapter

```python
# 目标文件结构 (services/adapter/modbus/)
services/adapter/modbus/
├── __init__.py
├── adapter.py            # ModbusAdapter 实现 ProtocolAdapter
├── client.py             # pymodbus 封装: RTU/TCP、线圈/寄存器读写
├── mapping.py            # DataPoint.key → Modbus 地址映射 (功能码、地址、数据类型)
├── framing.py            # RTU/TCP 帧处理、CRC 校验
└── test_modbus_adapter.py
```

**映射规则** (`DataPoint.extra_data`):
```json
{
  "modbus": {
    "function_code": 3,           // 01=线圈, 03=保持寄存器, 04=输入寄存器
    "address": 100,               // 0-based
    "data_type": "uint16",        // uint16, int16, uint32, float32, bool
    "byte_order": "big",          // big, little, swap
    "scale": 0.1,                 // 原始值 * scale = 物理值
    "offset": 0
  }
}
```

**验收标准**:
- [ ] 支持 RTU (串口) + TCP (以太网) 双模式
- [ ] 批量读取优化 (连续地址合并请求)
- [ ] 数据类型自动转换 (含字节序、缩放)
- [ ] 连接池复用、断线自动重连

---

### 泳道 D: MQTT/OPC-UA Adapter + Capability-Adapter 匹配引擎

#### D1: MQTT Adapter (复用 EMQX)
```python
# services/adapter/mqtt/adapter.py
# 订阅 topic → 解析 payload (JSON/Protobuf) → NormalizedTelemetry
# 写入: Command Intent → 构造 topic/payload → EMQX 发布
```

#### D2: OPC-UA Adapter
```python
# services/adapter/opcua/adapter.py
# 基于 asyncua: Read/Write/MonitoredItems (订阅)
# 映射: DataPoint.key → NodeId (ns=2;s=Temperature)
```

#### D3: Capability-Adapter 匹配引擎 (ADR-008) — **跨泳道共享组件**
```python
# services/adapter/matching.py
class CapabilityAdapterMatcher:
    """
    输入: CapabilityDefinition (key, data_type, unit, semantic_tags)
    输出: 兼容的 Adapter 类型列表 + 映射模板建议
    
    匹配规则:
    1. semantic_tags 交集非空 → 高优先级
    2. data_type 兼容 (numeric → float32/int16 等)
    3. unit 兼容性检查 (温度: celsius/fahrenheit/kelvin)
    4. 协议原生支持度评分
    """
    async def match(self, capability: CapabilityDefinition) -> List[AdapterMatch]:
        ...
```

**验收标准**:
- [ ] 匹配引擎 API: `POST /api/v1/adapter/match` 返回排序后的适配器推荐
- [ ] MQTT Adapter 对接 EMQX 认证/ACL、QoS 1/2
- [ ] OPC-UA Adapter 支持安全模式 (Basic256Sha256 Sign/Encrypt)
- [ ] 所有适配器通过统一 `AdapterRuntime` 管理

---

## 🔗 跨泳道依赖与同步点

| 同步点 | 时间 | 参与者 | 产出 |
|--------|------|--------|------|
| **S1: 接口契约冻结** | Day 1 | 全员 | `services/adapter/contracts.py` 定稿 |
| **S2: 映射 Schema 评审** | Day 3 | A+B+C+D | `DataPoint.extra_data` 映射规范文档化 |
| **S3: AdapterRuntime 集成测试** | Day 7 | A+B | 启动/停止/重连/健康检查全流程跑通 |
| **S4: 端到端数据流验证** | Day 14 | 全员 | Device → Adapter → Telemetry Ingestion → Query 全链路 |
| **S5: ADR-008 评审通过** | Day 10 | A+D | 匹配引擎设计文档 + 实现 |

---

## 🧪 测试要求 (每泳道必须)

```bash
# 单元测试
pytest services/adapter/.../test_*.py -v --cov=services.adapter --cov-report=term-missing

# 集成测试 (需 docker-compose up postgres redis emqx)
pytest tests/adapter/ -v -k "integration"

# 契约测试 (所有适配器必须通过)
pytest tests/adapter/test_contracts.py -v
```

**契约测试清单** (每个 Adapter 必须实现):
- [ ] `test_connect_disconnect_lifecycle`
- [ ] `test_read_single_datapoint`
- [ ] `test_read_batch_datapoints`
- [ ] `test_write_command`
- [ ] `test_subscribe_unsubscribe`
- [ ] `test_reconnection_after_network_failure`
- [ ] `test_health_check_reports_correct_status`
- [ ] `test_tenant_isolation`

---

## 📦 部署与运维交付物

| 产出 | 位置 | 说明 |
|------|------|------|
| **Adapter Dockerfile** | `services/adapter/Dockerfile` | 多阶段构建、非 root 用户 |
| **docker-compose 片段** | `deployment/docker/adapter.yml` | 可独立启动、依赖 emqx/postgres |
| **K8s Deployment** | `deployment/kubernetes/adapter/` | HPA (CPU>70%)、PodDisruptionBudget |
| **Prometheus Metrics** | `services/adapter/health.py` | `adapter_connected_devices`, `adapter_messages_total`, `adapter_errors_total` |
| **Grafana Dashboard** | `deployment/grafana/dashboards/adapter.json` | 连接数、吞吐、错误率、延迟 P50/P95/P99 |

---

## ⚠️ 红线规则 (违者代码审查拦截)

| 红线 | 检查方式 |
|------|----------|
| **Adapter 直接 import services.telemetry** | `grep -r "services.telemetry" services/adapter/` 必须为空 |
| **硬编码协议地址/端口/寄存器** | 所有配置必须来自 `DataSource`/`Connection`/`Device.extra_data` |
| **绕过 TenantAwareRepository** | 所有 DB 查询必须通过 Repository，且带 `tenant_id` |
| **在 Adapter 中处理业务逻辑** | Adapter 只做协议转换，不做阈值判断、告警、聚合 |
| **同步阻塞调用** | 所有 I/O 必须 async/await，禁用 `time.sleep()`, `requests` |

---

## 📅 里程碑检查点

| 日期 | 里程碑 | 验收标准 |
|------|--------|----------|
| **Day 3** | 接口契约冻结 | `contracts.py` 评审通过，全员签字 |
| **Day 7** | Core Runtime 可运行 | `AdapterRegistry` + `AdapterRuntime` 单测全绿，可注册 Mock Adapter |
| **Day 10** | BACnet Adapter 读写通 | 对真实/模拟 BACnet 设备读写成功，COV 订阅稳定 1 小时 |
| **Day 14** | Modbus/MQTT Adapter 并行就绪 | 两者单测全绿，集成测试通过 |
| **Day 21** | 端到端数据流打通 | 真实设备 → Adapter → Telemetry Ingestion → Query API 全链路验证 |
| **Day 28** | Task 15 交付 | 所有验收标准通过、文档完整、K8s 部署包就绪 |

---

## 🚀 立即开始行动 (今日)

1. **全员**: 克隆最新代码，`make dev` 启动基础设施，跑通现有测试基线
2. **泳道 A**: 创建 `services/adapter/contracts.py` 草案，发起接口评审会议 (30 分钟)
3. **泳道 B**: 调研 `bacpypes3` API，编写 `BACnetAdapter` 骨架代码
4. **泳道 C**: 调研 `pymodbus` async 用法，确认 RTU/TCP 连接参数映射
5. **泳道 D**: 设计 `CapabilityAdapterMatcher` 接口，与 Ontology/Template 团队确认语义标签体系

---

## 📞 协作渠道

| 场景 | 渠道 | 响应 SLA |
|------|------|----------|
| 阻塞问题 (依赖未就绪) | 立即 @dt_manager + 相关泳道负责人 | 2 小时内响应 |
| 架构分歧 | 发起架构评审会议 (记录 ADR) | 同天解决 |
| 代码审查 | GitLab MR + 自动 CI (ruff + pytest + contract test) | 4 小时内 Review |
| 部署/环境问题 | @DevOps on-call | 1 小时内响应 |

---

*指令发布: dt_manager*  
*执行角色: dt_code (并行开发团队)*
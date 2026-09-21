# DT-Lite V4.0 Phase 2 — Task 16 Telemetry Pipeline Enhancement
## 并行开发指令（给 dt_code）

---

## 🎯 任务目标

将 Telemetry 服务从"基础写入/查询"升级为**生产级高性能时序数据管道**，支撑：
- 百万点位/秒 写入吞吐
- 秒级聚合查询（1s/1m/1h/1d 连续聚合）
- 数据质量评分与异常检测
- Adapter Layer 直连零拷贝写入
- 多租户隔离的数据保留策略

---

## 🏊 四条并行泳道

| Swimlane | 负责模块 | 核心交付物 | 预估工时 |
|----------|----------|------------|----------|
| **S1: Core Ingestion** | `services/telemetry/ingestion/` | BatchWriter、分区路由、背压控制、写入指标 | 3d |
| **S2: Continuous Aggregates** | `services/telemetry/aggregates/` | TimescaleDB 连续聚合策略、物化视图、自动刷新、降采样保留 | 3d |
| **S3: Data Quality** | `services/telemetry/quality/` | 质量评分引擎、阈值规则、异常标记、质量报告 API | 2d |
| **S4: Query API & Adapter Integration** | `services/telemetry/query/` + Adapter 链接 | 统一查询 DSL、下推聚合、Adapter→Telemetry 直连、端到端测试 | 3d |

> **并行原则**：四泳道**同步启动**，每日站会同步进度，第 3/6/9 天强制同步检查点。

---

## 🔴 红线（违规即阻断合并）

| 编号 | 红线描述 | 验证方式 |
|------|----------|----------|
| R1 | **严禁**在 telemetry 核心引入任何协议相关代码（bacnet/modbus/mqtt/opcua） | `grep -r "bacnet\|modbus\|mqtt\|opcua" services/telemetry --include="*.py" \| grep -v test \| grep -v ".pyc"` 为空 |
| R2 | **严禁**绕过 TenantAwareRepository 直接操作 TimescaleDB | 所有 DB 操作必须通过 `TelemetryRepository` |
| R3 | **严禁**同步阻塞 I/O（`time.sleep`、`requests`、未 await 的 asyncpg） | `ruff check --select=ASYNC` + 人工审查 |
| R4 | **严禁**硬编码保留策略/分区间隔，必须通过 `TelemetryConfig` (Pydantic Settings) 配置 | 配置项在 `services/telemetry/config.py` 统一定义 |
| R5 | **严禁**修改 Task 1-14 任何冻结服务（core, identity, twin, activation, deployment, provisioning, ontology, template, adapter） | `git diff --name-only HEAD~15..HEAD \| grep -E "core\|identity\|twin\|activation\|deployment\|provisioning\|ontology\|template\|adapter" \| grep -v test` 为空 |
| R6 | **严禁**在查询 API 暴露内部 TimescaleDB 表结构（chunk、hypertable 名称） | API 响应只返回标准化字段：`asset_id, property, timestamps, values, quality, aggregates` |
| R7 | **严禁**Adapter 写入绕过批处理缓冲区直接单条插入 | Adapter 调用 `TelemetryIngestClient.batch_write()` |

---

## ✅ 验收标准

### S1: Core Ingestion
- [ ] `BatchWriter` 支持 `max_batch_size=10000`、`flush_interval_ms=100`、`max_pending_batches=100`
- [ ] 背压：队列满时 `batch_write()` 返回 `BackPressureError`，Adapter 指数退避重试
- [ ] 分区路由：按 `asset_id` 一致性哈希分片到 TimescaleDB 分区
- [ ] 指标导出：`telemetry_ingest_batch_total`, `telemetry_ingest_latency_seconds`, `telemetry_backpressure_total`
- [ ] 单元测试覆盖 ≥ 90%，集成测试验证 100k points/s 写入不丢数据

### S2: Continuous Aggregates
- [ ] 创建 4 级连续聚合：`1s_raw → 1m → 1h → 1d`（TimescaleDB `continuous_aggregate`）
- [ ] 自动刷新策略：`refresh_lag = '30s'`，`refresh_interval = '1m'`
- [ ] 保留策略：`1s` 保留 7 天，`1m` 保留 90 天，`1h` 保留 2 年，`1d` 保留 10 年（可配置）
- [ ] 压缩：`segmentby asset_id, property`，`orderby time DESC`，`compress_chunk_time_interval = '7d'`
- [ ] 迁移脚本：`database/migrations/versions/phase2_telemetry_aggregates.py` 幂等可重跑

### S3: Data Quality
- [ ] 质量维度：完整性、及时性、有效性、一致性、准确性（五维评分 0-100）
- [ ] 规则引擎：JSON Schema 定义阈值（如 `min/max`, `rate_of_change`, `staleness_seconds`）
- [ ] 实时标记：写入管道同步打质量标签 `quality: GOOD|UNCERTAIN|BAD`，写入 `telemetry_quality` 表
- [ ] API：`GET /api/v1/telemetry/quality/report?asset_id=&timerange=` 返回评分明细
- [ ] 告警集成：质量评分 < 60 触发 `TelemetryQualityAlert` 事件（发布到 Redis Stream）

### S4: Query API & Adapter Integration
- [ ] 统一查询 DSL：`TelemetryQuery(asset_ids, properties, timerange, aggregate=raw|1m|1h|1d, limit, offset)`
- [ ] 下推聚合：查询自动路由到对应连续聚合视图，不扫描原始 chunk
- [ ] Adapter 集成：`BACnetAdapter/ModbusAdapter/MQTTAdapter/OPCUAAdapter` 均实现 `telemetry_push()` 调用 `TelemetryIngestClient.batch_write()`
- [ ] 端到端测试：4 协议适配器各跑 1 万点位 × 1 小时，零数据丢失，P99 延迟 < 500ms
- [ ] API 文档：OpenAPI 3.1 完整注解，`/docs` 可直接试用

---

## 📦 交付物清单

### 代码新增/修改
```
services/telemetry/
├── config.py                    # TelemetryConfig (Pydantic Settings)
├── ingestion/
│   ├── __init__.py
│   ├── batch_writer.py          # BatchWriter + BackPressureError
│   ├── partition_router.py      # 一致性哈希分片
│   ├── metrics.py               # Prometheus 指标
│   └── client.py                # TelemetryIngestClient (Adapter 调用入口)
├── aggregates/
│   ├── __init__.py
│   ├── continuous_agg.py        # 连续聚合定义 + 刷新管理
│   ├── retention.py             # 保留策略执行器
│   └── compression.py           # 压缩策略
├── quality/
│   ├── __init__.py
│   ├── engine.py                # QualityEngine 五维评分
│   ├── rules.py                 # 规则定义 + JSON Schema 验证
│   ├── markers.py               # 实时质量标记写入
│   └── api.py                   # 质量报告 API
├── query/
│   ├── __init__.py
│   ├── dsl.py                   # TelemetryQuery DSL
│   ├── executor.py              # 查询执行器（下推聚合）
│   └── api.py                   # 统一查询 API (9 端点)
├── repository.py                # TelemetryRepository (TenantAware)
├── models.py                    # SQLAlchemy 2.x 模型
└── main.py                      # FastAPI 应用入口 + lifespan
```

### 数据库迁移
```
database/migrations/versions/
├── phase2_telemetry_core.py           # 核心表：telemetry_raw, telemetry_quality
├── phase2_telemetry_aggregates.py     # 连续聚合视图 + 保留/压缩策略
└── phase2_telemetry_indexes.py        # 查询优化索引
```

### 测试
```
tests/telemetry/
├── test_ingestion.py              # BatchWriter、背压、分区路由
├── test_aggregates.py             # 连续聚合刷新、保留、压缩
├── test_quality.py                # 五维评分、规则引擎、告警
├── test_query.py                  # DSL、下推聚合、分页
├── test_adapter_integration.py    # 4 协议适配器端到端写入
└── test_performance.py            # 100k points/s 基准测试
```

### 部署与运维
```
deployment/
├── docker/
│   ├── telemetry.Dockerfile
│   └── docker-compose.telemetry.yml    # 含 TimescaleDB、Redis、Prometheus、Grafana
├── kubernetes/
│   ├── telemetry-deployment.yaml
│   ├── telemetry-service.yaml
│   ├── telemetry-hpa.yaml              # 基于 CPU/队列长度自动扩缩容
│   └── telemetry-servicemonitor.yaml   # Prometheus 监控
└── grafana/
    └── telemetry-dashboard.json        # 写入吞吐、延迟、质量分布、存储增长
```

---

## 🔄 同步检查点

| 检查点 | 时间 | 内容 | 产出 |
|--------|------|------|------|
| **CP1** | Day 3 EOD | S1 核心写入链路跑通，S2 连续聚合建表完成，S3 规则引擎骨架，S4 DSL 定稿 | 架构评审会（30min），确认接口契约 |
| **CP2** | Day 6 EOD | S1 压测达标，S2 保留/压缩生效，S3 质量标记写入管道联通，S4 Adapter 集成 2/4 完成 | 集成测试报告，发现问题清单 |
| **CP3** | Day 9 EOD | 全链路端到端跑通，4 协议适配器零丢包，文档完善，部署包就绪 | **Task 16 完整交付评审** |

---

## 📋 里程碑

| 里程碑 | 标准 | 验收人 |
|--------|------|--------|
| **M1: Ingestion Ready** | 100k points/s 写入，P99 < 200ms，零丢包 | dt_manager |
| **M2: Aggregates Live** | 4 级连续聚合自动刷新，保留/压缩策略生效 | dt_manager |
| **M3: Quality Online** | 实时质量评分写入，报告 API 可用，告警触发 | dt_manager |
| **M4: Query GA** | 统一 DSL 查询，下推聚合正确，OpenAPI 文档完整 | dt_manager |
| **M5: Adapter Integrated** | 4 协议适配器端到端 1 小时稳定运行 | dt_manager |
| **M6: Task 16 Complete** | 所有验收项 ✅，部署包通过预发验证 | dt_manager |

---

## 🛠 技术栈锁定（不可变更）

| 组件 | 版本 | 说明 |
|------|------|------|
| TimescaleDB | 2.14+ (PG 16) | 连续聚合、压缩、分区原生支持 |
| SQLAlchemy | 2.0.30+ | Async ORM，`asyncpg` 驱动 |
| Redis | 7.2+ | Stream 用于质量告警、背压通知 |
| Prometheus Client | 0.19+ | 指标导出 |
| Pydantic | 2.8+ | Settings + DSL 验证 |
| FastAPI | 0.111+ | lifespan 替代 on_event |

---

## 🔗 依赖与接口契约

### Adapter → Telemetry （S4 定义，S1 实现）
```python
# services/telemetry/ingestion/client.py
class TelemetryIngestClient:
    async def batch_write(self, points: list[TelemetryPoint]) -> BatchWriteResult:
        """Adapter 唯一调用入口，内部走 BatchWriter 缓冲区"""
    
    async def health_check(self) -> HealthStatus:
        """Adapter 启动探活调用"""
```

### TelemetryPoint 标准载荷
```python
# services/telemetry/models.py
class TelemetryPoint(BaseModel):
    asset_id: UUID
    property_code: str
    timestamp: datetime  # UTC, timezone-aware
    value: float | int | bool | str
    quality: Quality = Quality.GOOD  # GOOD|UNCERTAIN|BAD
    source_adapter: str  # "bacnet"|"modbus"|"mqtt"|"opcua"
    metadata: dict = Field(default_factory=dict)
```

### 查询 DSL（S4 定义）
```python
# services/telemetry/query/dsl.py
class TelemetryQuery(BaseModel):
    asset_ids: list[UUID]
    property_codes: list[str]
    timerange: TimeRange  # start/end UTC
    aggregate: Aggregate = Aggregate.RAW  # RAW|1M|1H|1D
    limit: int = 10000
    offset: int = 0
    quality_filter: Quality | None = None
```

---

## 🚀 启动命令（dt_code 执行）

```bash
# 1. 创建特性分支
git checkout -b feat/task16-telemetry-pipeline

# 2. 四泳道并行开发（每泳道一个子目录或并行终端）
# S1
cd services/telemetry/ingestion && # 编写 BatchWriter...

# S2
cd services/telemetry/aggregates && # 编写连续聚合迁移...

# S3
cd services/telemetry/quality && # 编写质量引擎...

# S4
cd services/telemetry/query && # 编写 DSL + Adapter 集成...

# 3. 每日同步：git push origin feat/task16-telemetry-pipeline && 在群里同步进度
# 4. CP1/CP2/CP3 按时发起评审
```

---

## 📝 备注

1. **TimescaleDB 独立实例**：生产环境必须独立部署，不与元数据 PostgreSQL 共库。开发环境 `docker-compose.telemetry.yml` 已包含。
2. **Adapter 回溯改造**：Task 15 已交付的 4 个适配器需在 S4 中加入 `telemetry_push()` 调用，属于 Task 16 范围，不计入 Task 15 变更。
3. **零代码就绪**：所有配置（保留、压缩、质量规则、分区数）均通过 `TelemetryConfig` 环境变量驱动，支撑后续 Ontology→Template→Deployment 零代码链路。
4. **性能基线**：预发环境跑 100k points/s × 4 小时稳定性测试，通过才能合并主干。

---

**指令生效时间**：即时  
**首个同步检查点 (CP1)**：Day 3 EOD  
**预计完工**：Day 9 EOD  
**评审人**：dt_manager

---

> **dt_code 注意**：严格遵守红线 R1-R7，四泳道并行推进，遇阻塞立即在群里同步。每日 EOD 推送进度分支，CP1/CP2/CP3 准时评审。Task 16 完成后自动进入 Task 17 (AI Agent & RAG) 排期。
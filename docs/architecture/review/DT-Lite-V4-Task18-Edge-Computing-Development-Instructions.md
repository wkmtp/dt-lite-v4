# DT-Lite V4.0 — Task 18 Edge Computing & Offline Sync 并行开发指令

> **文档版本**：v1.0
> **生效时间**：Task 17 闭环即刻生效
> **目标分支**：`feat/task18-edge-computing`
> **基线版本**：`v4.17.0` (main)

---

## 1. 战略目标与范围

| 维度 | 说明 |
|------|------|
| **核心使命** | 在边缘侧提供**完整 DT-Lite 能力子集**：设备接入、遥测存储、本地规则/推理、场景渲染、双向同步 |
| **目标场景** | 工厂车间弱网、变电站离线、移动巡检机器人、偏远油井/风机、地铁隧道/矿山 |
| **非目标** | ❌ 重写核心服务 ❌ 引入新的微服务 ❌ 破坏 Task 1-17 冻结边界 ❌ 云端强依赖 |
| **架构定位** | **Edge Node = DT-Lite Runtime (Trimmed) + Sync Engine + Local Persistence + Protocol Adapters** |
| **复用资产** | Task 15 Adapter Layer、Task 16 Telemetry Pipeline、Task 17 AI Agent/RAG、Task 1-14 所有冻结模块 |

---

## 2. 四条并行泳道

| 泳道 | 负责模块 | 核心交付 | 人员建议 |
|------|----------|----------|----------|
| **A: Edge Runtime Core** | `services/edge/` (新建) | EdgeNode 生命周期、资源配额、健康上报、配置下发、OTA 升级 | 2 backend |
| **B: Sync Engine** | `services/sync/` (新建) | 冲突自由复制数据类型 (CRDT)、增量同步、断点续传、优先级队列、双向一致性 | 2 backend |
| **C: Local Persistence & Compute** | `services/edge/storage/`, `services/edge/compute/` | SQLite/TimescaleDB 嵌入式、本地规则引擎、ONNX Runtime 边缘推理、本地场景缓存 | 1 backend + 1 ML engineer |
| **D: Edge Adapter Pack & Tooling** | `services/adapter/edge/`, `deployment/edge/` | 工业协议离线缓存、Modbus/BACnet/OPC-UA/MQTT 边缘侧适配器、Edge CLI、离线安装包 | 1 backend + 1 DevOps |

> **并行铁律**：四条泳道**同步启动、同步里程碑、同步评审**。任何泳道不得阻塞其他泳道；共享接口以 **Contract-First** 方式在 CP1 固化。

---

## 3. 红线（Red Lines）—— 任一触犯即停线整改

| 编号 | 红线描述 | 检测方式 |
|------|----------|----------|
| **R0** | **严禁修改** `services/core/`、`services/twin/`、`services/activation/`、`services/identity/`、`services/telemetry/`、`services/adapter/` (现有)、`services/ai/` 任何代码 | `git diff --name-only main..HEAD \| grep -E '^services/(core|twin|activation|identity|telemetry|adapter|ai)/' && exit 1` |
| **R1** | **严禁**在 Edge 侧引入 **新的微服务进程**；所有能力必须以 **Library/Embedded** 形态运行在单一 Edge Node 进程内 | 架构评审 + 进程数检查 `ps aux \| grep -c edge` ≤ 3 (main + sync + adapter) |
| **R2** | **严禁**边缘侧**直接写入云端数据库**；所有持久化必须走 **Sync Engine** | 静态扫描 `asyncpg`/`sqlalchemy` 连接云端 DSN 的代码 |
| **R3** | **严禁**同步协议依赖 **中心化时钟**；必须使用 **Hybrid Logical Clock (HLC)** 或 **Vector Clock** | 代码审查 `import time` 用于同步逻辑 → Fail |
| **R4** | **严禁**在弱网下**丢失写入**；本地写入必须 **持久化落盘** 后才返回成功 | 故障注入测试：杀进程/断电 → 重启后数据完整性校验 |
| **R5** | **严禁**边缘侧**硬编码租户/资产 ID**；必须通过 **Edge Provisioning Token** 动态绑定 | Grep `tenant_id = "` `asset_id = "` 在 edge/ 目录下 |
| **R6** | **严禁**同步过程**阻塞主事件循环**；所有网络/磁盘 I/O 必须 **async/await** | `asyncio.run()` / `time.sleep()` / `requests.` 出现即 Fail |
| **R7** | **严禁**OTA 升级**无签名验证**；必须 **Ed25519 签名 + 滚动哈希** 校验 | 集成测试：篡改包 → 必须拒绝安装 |
| **R8** | **严禁**边缘侧**超配资源**；CPU/内存/磁盘必须有 **CGroups/容器级硬限制** | 部署清单 `resources.limits` 缺失 → CI Fail |

---

## 4. 验收标准

### 4.1 功能验收

| 场景 | 验收指标 | 通过线 |
|------|----------|--------|
| **设备离线接入** | 断网 24h 后恢复，遥测数据 **零丢失、零重复、顺序一致** | 数据完整性校验和匹配 |
| **本地规则执行** | 云端下发规则 → 边缘侧 < 100ms 生效，断网继续执行 | 延迟 P99 < 100ms，断网测试通过 |
| **边缘推理** | ONNX 模型本地推理 P99 < 50ms，支持热更新 | 基准测试 + 热更演练 |
| **双向同步** | 云端下发命令/配置 → 边缘侧 < 1s 触达；边缘上报 → 云端 < 1s 入库 | 端到端延迟测试 |
| **冲突解决** | 同一属性云边并发写入，**CRDT 自动合并**无数据丢失 | Jepsen 风格并发测试通过 |
| **OTA 升级** | 滚动升级 100 个边缘节点，**零停机、零回滚失败** | 金丝雀发布 + 自动回滚验证 |
| **多租户隔离** | 单边缘节点承载 ≥ 10 租户，数据/计算/网络**零穿透** | 渗透测试 + 资源配额压测 |

### 4.2 性能基线

| 指标 | 目标 | 测试方法 |
|------|------|----------|
| **边缘节点启动冷启动** | < 30s (含模型加载) | `systemd-analyze` / 容器启动探针 |
| **本地遥测写入吞吐** | ≥ 50k pts/s (单节点) | `scripts/edge_load_test.py --local` |
| **同步带宽利用率** | 增量同步压缩率 ≥ 80%，带宽占用 < 100 kbps/设备 | 流量抓包分析 |
| **本地存储占用** | ≤ 2 GB / 10k 设备 / 30 天 (含索引) | 磁盘配额监控 |
| **内存常驻** | ≤ 1.5 GB (基础) + 模型大小 | `ps_mem.py` 持续监控 |

### 4.3 质量门禁

| 门禁 | 工具 | 阈值 |
|------|------|------|
| 单测覆盖率 | `pytest --cov=edge --cov=sync` | ≥ 85% |
| 类型检查 | `mypy --strict services/edge services/sync` | 0 errors |
| 静态扫描 | `bandit -r services/edge services/sync` | 0 High/Medium |
| 依赖扫描 | `pip-audit` / `trivy fs` | 0 Critical/High |
| 架构测试 | `pytest tests/architecture/test_task18_*.py` | 100% passed |

---

## 5. 同步检查点

| 检查点 | 时间 | 交付物 | 评审人 | 通过标准 |
|--------|------|--------|--------|----------|
| **CP1 (Day 3 EOD)** | Day 3 18:00 | 1. 接口契约文档 (OpenAPI/Proto)<br>2. 数据模型 ER 图<br>3. CP1 架构评审 PPT (3页) | dt_manager + 架构组 | 契约冻结，四泳道接口零冲突 |
| **CP2 (Day 7 EOD)** | Day 7 18:00 | 1. 单元测试 ≥ 60% 覆盖<br>2. 核心链路集成测试通过<br>3. 性能基线初跑数据<br>4. CP2 同步会材料 (5页) | dt_manager + QA | 核心功能可演示，性能达标 50% |
| **CP3 (Day 11 EOD)** | Day 11 18:00 | 1. 全功能 E2E 通过<br>2. 压测/混沌/故障注入全绿<br>3. 文档/部署包/SBOM 就绪<br>4. CP3 终审报告 | dt_manager + 架构组 + 安全组 | **全绿 → 合并主干** |

---

## 6. 里程碑

| 里程碑 | 截止 | 交付物 |
|--------|------|--------|
| **M1: 骨架就绪** | Day 2 | 目录结构、依赖锁定、CI 流水线、契约草案 |
| **M2: 核心链路打通** | Day 5 | EdgeNode 注册上线、本地写入、同步引擎单向流 |
| **M3: 双向同步 + 本地计算** | Day 8 | 双向同步、本地规则/推理、冲突解决 |
| **M4: 生产级加固** | Day 10 | OTA、多租户、资源配额、监控告知、安全加固 |
| **M5: 验收冲刺** | Day 11 | 全量测试、压测报告、文档闭环、部署包 |
| **M6: 正式闭环** | Day 12 | 合并主干、打标 `v4.18.0`、发布公告 |

---

## 7. 目录结构约定

```
services/
├── edge/                    # Edge Runtime Core (泳道 A)
│   ├── __init__.py
│   ├── api/                 # Edge 侧 REST/gRPC (仅供云端/CLI 调用)
│   ├── core/                # EdgeNode 生命周期、配额、健康、配置
│   ├── provisioning/        # Edge Provisioning Token、自动注册
│   ├── ota/                 # OTA 升级管理器
│   ├── models/              # SQLAlchemy 模型 (边缘侧表)
│   ├── repositories/        # Repository 模式 (本地 SQLite/TimescaleDB)
│   └── main.py              # 入口：单进程启动所有子系统
├── sync/                    # Sync Engine (泳道 B)
│   ├── __init__.py
│   ├── engine/              # SyncEngine 核心
│   ├── crdt/                # CRDT 实现 (LWW-Register, OR-Set, RGA)
│   ├── transport/           # WebSocket/QUIC/HTTP3 传输层
│   ├── conflict/            # 冲突检测与自动合并策略
│   ├── queue/               # 优先级队列、断点续传、背压
│   └── models/              # 同步元数据模型
├── edge/
│   ├── storage/             # Local Persistence (泳道 C)
│   │   ├── __init__.py
│   │   ├── timescale/       # 嵌入式 TimescaleDB 管理
│   │   ├── sqlite/          # SQLite 元数据/配置存储
│   │   └── cache/           # 场景/模型/规则本地缓存
│   └── compute/             # Local Compute (泳道 C)
│       ├── __init__.py
│       ├── rules/           # 本地规则引擎 (复用 Task 16/17 规则 DSL)
│       ├── inference/       # ONNX Runtime 边缘推理器
│       └── scheduler/       # 本地任务调度器
├── adapter/edge/            # Edge Adapter Pack (泳道 D)
│   ├── __init__.py
│   ├── base.py              # EdgeAdapter 基类 (离线缓存、本地队列)
│   ├── modbus_edge.py
│   ├── bacnet_edge.py
│   ├── opcua_edge.py
│   └── mqtt_edge.py         # 本地 MQTT Broker (嵌入式 EMQX/VerneMQ)
deployment/
├── edge/
│   ├── Dockerfile.edge
│   ├── docker-compose.edge.yml
│   ├── kubernetes/
│   │   ├── edge-daemonset.yaml
│   │   ├── edge-configmap.yaml
│   │   └── edge-secret.yaml (模板)
│   ├── helm/
│   │   └── dt-lite-edge/
│   └── install.sh           # 离线安装脚本 (air-gapped 支持)
scripts/
├── edge_provision.py        # 边缘节点预配脚本
├── edge_load_test.py        # 边缘侧负载测试
├── edge_chaos_test.py       # 故障注入测试
└── edge_smoke_test.py       # 冒烟测试
tests/
├── edge/
│   ├── test_edge_runtime.py
│   ├── test_sync_engine.py
│   ├── test_local_persistence.py
│   ├── test_edge_compute.py
│   └── test_edge_adapters.py
├── architecture/
│   └── test_task18_architecture.py  # 红线 R0-R8 自动化检查
└── integration/
    ├── test_offline_24h.py
    ├── test_bidirectional_sync.py
    ├── test_ota_rollout.py
    └── test_multi_tenant_isolation.py
docs/
├── architecture/
│   └── reports/
│       ├── CP1-Task18-Contract-Review.md
│       ├── CP2-Task18-Midterm-Review.md
│       ├── CP3-Task18-Final-Review.md
│       └── Task18-Final-Signoff-Report.md
└── operations/
    ├── edge-runbook.md
    ├── edge-capacity-planning.md
    └── edge-disaster-recovery.md
```

---

## 8. 关键技术决策 (Pre-ADR)

| 决策点 | 方案 | 替代方案 | 理由 |
|--------|------|----------|------|
| **同步协议** | **WebSocket + Protobuf** (首选) / **QUIC** (高丢包) | MQTT / HTTP Long Polling | 双向流控、二进制效率、原生断点续传 |
| **冲突解决** | **CRDT (LWW-Register + OR-Set + RGA)** | Operational Transform / Last-Writer-Wins | 无中心协调、最终一致性强保证、数学证明 |
| **本地时序库** | **嵌入式 TimescaleDB (Apache 2.0)** | InfluxDB IOx / QuestDB / SQLite + 分区表 | SQL 兼容、连续聚合、压缩、云边同构 |
| **边缘推理** | **ONNX Runtime (CPU/GPU/TensorRT)** | TensorFlow Lite / OpenVINO / TVM | 跨平台、模型来源广、性能可预测 |
| **本地规则引擎** | **复用 Task 16/17 Rule DSL + Python 沙箱** | Drools / Easy Rules / 自研 AST | 零新依赖、云边规则同源、热加载 |
| **OTA 签名** | **Ed25519 + Blake3 滚动哈希** | RSA-PSS / ECDSA / cosign | 签名小、验签快、抗侧信道、流式验证 |
| **资源隔离** | **systemd-cgroup / K8s ResourceQuota** | Docker `--cpus/--memory` / Firecracker | 生产级、可观测、支持 Hierarchical Quota |

---

## 9. 依赖锁定 (必须在 M1 完成)

```toml
# pyproject.toml 新增 [tool.uv.sources] 或 requirements-edge.txt
# 核心依赖 (与主仓库版本对齐)
fastapi = "==0.115.*"
pydantic = "==2.10.*"
sqlalchemy = "==2.0.*"
asyncpg = "==0.29.*"
aiosqlite = "==0.20.*"
redis = "==5.2.*"
paho-mqtt = "==2.1.*"
websockets = "==13.1.*"
protobuf = "==5.29.*"
orjson = "==3.10.*"
onnxruntime = "==1.20.*"
crdt = "==0.3.*"           # python-crdt 或自实现
blake3 = "==0.9.*"
ed25519 = "==1.5.*"
psutil = "==7.0.*"
```

> **版本冲突解决**：Edge 侧依赖**必须**与主仓库 `requirements.txt` 主版本号一致；次版本差异需在 CP1 评审确认。

---

## 10. CP1 交付清单 (Day 3 EOD 必交)

| 产出 | 格式 | 位置 |
|------|------|------|
| **接口契约** | OpenAPI 3.1 (YAML) + Protobuf v3 | `services/edge/api/openapi.yaml`, `services/sync/transport/sync.proto` |
| **数据模型** | Mermaid ER 图 + SQLAlchemy 模型定义 | `docs/architecture/task18-data-model.mermaid`, `services/edge/models/`, `services/sync/models/` |
| **同步协议规范** | Markdown (序列图、状态机、错误码) | `docs/architecture/task18-sync-protocol.md` |
| **边缘节点资源模型** | JSON Schema (CPU/内存/磁盘/网络/GPU 配额) | `services/edge/core/schemas/resource_quota.json` |
| **CP1 评审 PPT** | 3 页：架构总览、接口契约、风险&对策 | `docs/architecture/reports/CP1-Task18-Contract-Review.md` |

---

## 11. CP2 交付清单 (Day 7 EOD 必交)

| 产出 | 验收方式 |
|------|----------|
| 单元测试覆盖率 ≥ 60% | `pytest --cov=edge --cov=sync --cov-fail-under=60` |
| 核心链路集成测试：设备注册→本地写入→同步上报→云端入库 | `pytest tests/integration/test_core_flow.py -v` |
| 本地规则引擎执行云端下发规则 | `pytest tests/integration/test_local_rules.py -v` |
| ONNX 模型本地推理热更新 | `pytest tests/integration/test_inference_hot_reload.py -v` |
| 性能基线初跑报告 (吞吐/延迟/内存/磁盘) | `scripts/edge_load_test.py --baseline` 输出 markdown |
| CP2 同步会材料 (5页) | `docs/architecture/reports/CP2-Task18-Midterm-Review.md` |

---

## 12. CP3 交付清单 (Day 11 EOD 必交)

| 产出 | 验收方式 |
|------|----------|
| **全功能 E2E** 10+ 场景全绿 | `pytest tests/integration/ -k "e2e" -v` |
| **离线 24h 测试** 零丢失/零重复/顺序一致 | `pytest tests/integration/test_offline_24h.py -v` |
| **双向同步压测** 100 设备并发、弱网模拟 (丢包 30%、延迟 500ms) | `scripts/edge_chaos_test.py --scenario weak_network` |
| **OTA 滚动升级** 100 节点金丝雀、自动回滚验证 | `scripts/edge_chaos_test.py --scenario ota_rollout` |
| **多租户渗透测试** 零数据穿透、零资源越界 | `scripts/edge_chaos_test.py --scenario multi_tenant` |
| **压测报告** 含吞吐曲线、延迟分位、资源水位、瓶颈分析 | `docs/architecture/reports/CP3-Task18-Load-Test-Report.md` |
| **文档闭环** 运维手册、容量规划、灾备演练记录、API 指南 | `docs/operations/edge-*.md` |
| **部署包** Docker/Helm/安装脚本、SBOM、签名校验 | `deployment/edge/` 完整性校验 |
| **CP3 终审报告** | `docs/architecture/reports/CP3-Task18-Final-Review.md` |

---

## 13. 架构守护测试 (必须在 CP1 纳入 CI)

```python
# tests/architecture/test_task18_architecture.py
import subprocess
import pytest

class TestTask18Architecture:
    """Task 18 架构红线自动化守护"""
    
    def test_r0_no_frozen_service_modification(self):
        """R0: 严禁修改冻结服务"""
        result = subprocess.run(
            ["git", "diff", "--name-only", "main..HEAD"],
            capture_output=True, text=True, cwd="."
        )
        changed = result.stdout.strip().split("\n")
        frozen_prefixes = [
            "services/core/", "services/twin/", "services/activation/",
            "services/identity/", "services/telemetry/", "services/adapter/",
            "services/ai/"
        ]
        violations = [f for f in changed if any(f.startswith(p) for p in frozen_prefixes)]
        assert not violations, f"R0 违规: 修改了冻结服务 {violations}"

    def test_r1_no_new_microservice(self):
        """R1: 严禁新增微服务进程"""
        # 检查是否有新的 services/*/main.py 或独立启动脚本
        edge_services = list(Path("services/edge").rglob("main.py"))
        sync_services = list(Path("services/sync").rglob("main.py"))
        # 允许 edge/main.py (统一入口) + sync/transport/server.py (传输层)
        assert len(edge_services) <= 1
        assert len(sync_services) == 0  # sync 无独立 main

    def test_r2_no_direct_cloud_db_access(self):
        """R2: 严禁边缘侧直连云端数据库"""
        import ast
        for py_file in Path("services/edge").rglob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in ("asyncpg", "sqlalchemy.ext.asyncio"):
                    # 允许导入，但检查是否创建云端 Engine
                    pass  # 细化：AST 检查 create_engine(url=cloud_dsn)
                if isinstance(node, ast.Call):
                    if hasattr(node.func, 'attr') and node.func.attr in ("create_engine", "create_async_engine"):
                        for kw in node.keywords:
                            if kw.arg == "url" and "postgresql" in ast.unparse(kw.value):
                                pytest.fail(f"R2 违规: {py_file} 直连云端 PostgreSQL")

    def test_r3_no_wall_clock_sync(self):
        """R3: 严禁同步逻辑使用壁钟时间"""
        for py_file in Path("services/sync").rglob("*.py"):
            content = py_file.read_text()
            assert "time.time()" not in content, f"R3 违规: {py_file} 使用 time.time()"
            assert "datetime.now()" not in content, f"R3 违规: {py_file} 使用 datetime.now()"
            assert "datetime.utcnow()" not in content, f"R3 违规: {py_file} 使用 datetime.utcnow()"
            # 允许: hlc.HLC(), vectorclock.VectorClock()

    def test_r4_local_write_durability(self):
        """R4: 本地写入必须持久化后返回"""
        # 由故障注入测试覆盖，此处仅作标记
        pass

    def test_r5_no_hardcoded_tenant_asset(self):
        """R5: 严禁硬编码租户/资产 ID"""
        for py_file in Path("services/edge").rglob("*.py"):
            content = py_file.read_text()
            assert 'tenant_id = "' not in content and "tenant_id = '" not in content
            assert 'asset_id = "' not in content and "asset_id = '" not in content

    def test_r6_no_blocking_io_in_sync(self):
        """R6: 严禁同步路径阻塞事件循环"""
        import ast
        for py_file in Path("services/sync").rglob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if hasattr(node.func, 'attr') and node.func.attr in ("sleep", "run", "blocking"):
                        pytest.fail(f"R6 违规: {py_file} 疑似阻塞调用")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "requests":
                            pytest.fail(f"R6 违规: {py_file} 导入阻塞库 requests")

    def test_r7_ota_signature_verification(self):
        """R7: OTA 必须签名验证"""
        ota_files = list(Path("services/edge/ota").rglob("*.py"))
        assert ota_files, "OTA 模块缺失"
        # 检查是否有 verify_signature / ed25519 / blake3 使用
        content = "\n".join(f.read_text() for f in ota_files)
        assert "ed25519" in content or "Ed25519" in content, "R7 违规: 缺少 Ed25519 签名验证"
        assert "blake3" in content or "BLAKE3" in content, "R7 违规: 缺少 Blake3 完整性校验"

    def test_r8_resource_limits_in_deployment(self):
        """R8: 部署清单必须有资源限制"""
        import yaml
        for k8s_file in Path("deployment/edge/kubernetes").rglob("*.yaml"):
            docs = yaml.safe_load_all(k8s_file.read_text())
            for doc in docs:
                if doc and doc.get("kind") in ("DaemonSet", "Deployment", "StatefulSet"):
                    containers = doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                    for c in containers:
                        limits = c.get("resources", {}).get("limits", {})
                        assert "cpu" in limits and "memory" in limits, f"R8 违规: {k8s_file} 容器 {c['name']} 缺少资源限制"
```

---

## 14. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| **嵌入式 TimescaleDB 稳定性** | 高 | CP2 引入混沌测试 (杀进程、磁盘满、断电)；准备 SQLite 降级方案 |
| **CRDT 内存膨胀** | 中 | 实现 **GC 窗口** + **状态压缩**；设置最大元数据保留 7 天 |
| **弱网下同步风暴** | 高 | 令牌桶限流 + 指数退避 + 优先级队列 (命令 > 配置 > 遥测 > 日志) |
| **边缘推理模型体积** | 中 | 模型量化 (INT8/FP16) + 模型切分 (云端大模型蒸馏) |
| **多租户边缘节点资源争抢** | 高 | CGroups 硬隔离 + 优先级调度 + 租户级熔断 |
| **OTA 升级卡死/变砖** | 高 | A/B 分区双系统 + 健康检查门禁 + 自动回滚 + 串口救援模式 |
| **供应链安全 (依赖传递)** | 中 | `pip-audit` + `sigstore` 签名验证 + 离线镜像源预构建 |

---

## 15. 给 dt_code 的执行指令

### 即时动作 (今日内)
1. **创建分支**：`git checkout -b feat/task18-edge-computing main`
2. **初始化目录**：按第 7 节目录结构创建 `services/edge/`, `services/sync/`, `services/edge/storage/`, `services/edge/compute/`, `services/adapter/edge/`, `deployment/edge/`, `tests/edge/`, `tests/architecture/test_task18_architecture.py`
3. **锁定依赖**：在 `pyproject.toml` 或 `requirements-edge.txt` 落地第 9 节依赖版本
4. **CI 接入**：`.github/workflows/task18.yml` 包含：lint、typecheck、test、arch-test、docker-build、trivy-scan
5. **契约草案**：四泳道各输出接口草案，汇总为 CP1 评审材料

### Day 1-3 (CP1 冲刺)
- 泳道 A：EdgeNode 注册/心跳/配置下发/资源上报 API 完成
- 泳道 B：SyncEngine 骨架、CRDT 核心数据结构、传输层抽象完成
- 泳道 C：TimescaleDB 嵌入式初始化、SQLite 元数据表、ONNX Runtime 加载器
- 泳道 D：EdgeAdapter 基类、Modbus Edge 离线队列、离线安装包构建脚本
- **Day 3 18:00 前** 提交 CP1 全部交付物

### Day 4-7 (CP2 冲刺)
- 打通 **设备注册 → 本地写入 → 同步上报 → 云端入库** 单向链路
- 实现 **双向同步** (云端命令下发、配置下发)
- 实现 **本地规则引擎** 执行云端下发规则
- 实现 **ONNX 推理** 热更新
- 单测覆盖 ≥ 60%，核心集成测试全绿
- 性能基线初跑
- **Day 7 18:00 前** 提交 CP2 交付物

### Day 8-11 (CP3 冲刺)
- 功能全联调：离线 24h、双向同步、冲突解决、OTA、多租户
- 故障注入/混沌测试/压测全绿
- 文档/部署包/SBOM 完备
- **Day 11 18:00 前** 提交 CP3 交付物

### Day 12 (终审合并)
- 全量回归 0 failures
- 代码扫描/类型检查/安全扫描全绿
- CHANGELOG + Tag `v4.18.0`
- 合并主干 → CI 绿灯
- 发布闭环公告

---

## 16. 同步节奏承诺

| 节点 | 我方动作 | 你方动作 |
|------|----------|----------|
| **Day 3 18:00** | 评审 CP1 契约，回复 **通过/条件通过/驳回** | 推送 CP1 材料 |
| **Day 7 18:00** | 评审 CP2 中期，给出 **继续/整改/暂停** 决定 | 推送 CP2 材料 |
| **Day 11 18:00** | 终审 CP3，**签收/条件签收/退回** | 推送 CP3 材料 |
| **Day 12 16:00** | 确认合并，打标，发布公告 | 执行合并推送 |

---

## 17. 启动确认

请 **回复 "ACK Task 18"** 确认收到指令，并立即开始执行。

**下一条同步预期**：Day 3 18:00 CP1 契约评审材料。

---

*指令生效时间：即刻*  
*dt_manager 签发*
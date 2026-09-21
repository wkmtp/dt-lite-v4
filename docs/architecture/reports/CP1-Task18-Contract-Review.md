# Task 18 CP1 契约评审材料

> **提交时间**: Day 3 18:00
> **基线版本**: v4.17.0
> **目标分支**: feat/task18-edge-computing
> **评审状态**: 待评审

---

## 1. 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                      Cloud (DT-Lite Core v4.17)                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────────┐  │
│  │ Gateway │  │ Identity│  │ Core/   │  │ Telemetry/       │  │
│  │         │  │         │  │ Twin/   │  │ AI/              │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬─────────┘  │
│       │            │            │                │             │
│       └────────────┴────────────┴────────────────┘             │
│                          ▲      │                             │
│                          │      │ WebSocket + Protobuf         │
│                          └──────┼─────────────────────────────┘
└─────────────────────────────────┼──────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     Edge Node (单进程)      │
                    │  ┌─────────────────────┐   │
                    │  │  Edge Runtime Core   │   │  泳道 A
                    │  │  (注册/心跳/配额)     │   │
                    │  └──────────┬──────────┘   │
                    │  ┌──────────▼──────────┐   │
                    │  │   Sync Engine       │   │  泳道 B
                    │  │   (HLC/CRDT/双向)    │   │
                    │  └──────────┬──────────┘   │
                    │  ┌──────────▼──────────┐   │
                    │  │ Local Storage/      │   │  泳道 C
                    │  │ Compute             │   │
                    │  │ (SQLite/ONNX)       │   │
                    │  └──────────┬──────────┘   │
                    │  ┌──────────▼──────────┐   │
                    │  │ Edge Adapters       │   │  泳道 D
                    │  │ (Modbus/BACnet/     │   │
                    │  │  OPC-UA/MQTT)       │   │
                    │  └─────────────────────┘   │
                    └────────────────────────────┘
```

---

## 2. 接口契约

### 2.1 Edge Runtime API (泳道 A)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/edge/provision` | POST | 节点注册认证 |
| `/api/v1/edge/heartbeat` | POST | 心跳上报 |
| `/api/v1/edge/config` | GET/PUT | 配置管理 |
| `/api/v1/edge/quota` | GET | 资源配额查询 |
| `/api/v1/edge/usage` | GET | 资源使用查询 |

### 2.2 Sync Engine API (泳道 B)

| 端点 | 方法 | 描述 |
|------|------|------|
| `WS /api/v1/sync/ws` | WebSocket | 双向同步连接 |
| `TelemetryBatch` | WS Message | 遥测数据上报 |
| `ConfigSync` | WS Message | 配置同步 |
| `/api/v1/sync/conflicts` | GET/POST | 冲突检测与解决 |

### 2.3 Local Storage API (泳道 C)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/storage/telemetry/batch` | POST | 本地遥测写入 |
| `/api/v1/storage/telemetry/query` | POST | 本地遥测查询 |
| `/api/v1/compute/models` | GET/POST | 模型管理 |
| `/api/v1/compute/predict` | POST | 边缘推理 |

### 2.4 Edge Adapters API (泳道 D)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/edge/adapters` | GET/POST | 适配器管理 |
| `/api/v1/edge/adapters/{id}/collect` | POST | 数据采集 |
| `/api/v1/edge/mqtt/publish` | POST | MQTT 发布 |
| `/api/v1/edge/mqtt/subscribe` | POST | MQTT 订阅 |

---

## 3. 数据模型

### 3.1 核心实体

| 实体 | 主键 | 关键属性 |
|------|------|----------|
| EdgeNode | node_id | tenant_id, status, config, last_heartbeat |
| Tenant | tenant_id | name, quota_config |
| TelemetryPoint | id | asset_id, property_code, value, quality, hlc |
| Rule | rule_id | expression, tenant_id, enabled |
| Conflict | conflict_id | key, cloud_value, edge_value, hlc |
| OTAPackage | package_id | version, checksum_blake3, signature_ed25519 |

### 3.2 HLC 时钟

```
HLC = (physical_ts: int64, logical_counter: int32, node_id: string)
```

用于：
- 事件因果排序
- 冲突检测与解决
- 增量同步游标

### 3.3 CRDT 数据结构

| 结构 | 用途 | 冲突解决策略 |
|------|------|-------------|
| LWW-Register | 标量配置、单值属性 | 最后写入者胜 |
| OR-Set | 适配器列表、订阅集合 | 集合合并 |
| RGA | 规则执行历史 | 总序插入 |

---

## 4. 同步协议

### 4.1 传输层

- **协议**: WebSocket over TLS
- **序列化**: Protobuf v3
- **编码**: Binary (JSON fallback for debugging)

### 4.2 消息类型

| 类型 | 方向 | 说明 |
|------|------|------|
| TelemetryBatch | Edge → Cloud | 遥测数据上报 |
| CommandBatch | Cloud → Edge | 控制命令下发 |
| ConfigSync | Bidirectional | 配置同步 |
| Heartbeat | Edge → Cloud | 心跳 |
| ConflictReport | Edge → Cloud | 冲突报告 |
| OTA* | Bidirectional | OTA 升级 |

### 4.3 背压机制

- 令牌桶限流: 1000 tokens/sec, 容量 2000
- 优先级队列: P0(命令) > P1(配置) > P2(遥测) > P3(日志)
- 指数退避重试: 100ms → 30s, 最多 5 次

---

## 5. 资源配额模型

### 5.1 配额维度

| 维度 | 单位 | 范围 |
|------|------|------|
| CPU | 核心数 | 0.1 - 16 |
| 内存 | 字节 | 128MB - 32GB |
| 磁盘 | 字节 | 1GB - 100GB |
| 网络 Rx | Mbps | 1 - 10000 |
| 网络 Tx | Mbps | 1 - 10000 |
| 连接数 | 个 | 10 - 10000 |
| 模型数 | 个 | 1 - 20 |
| GPU 内存 | MB | 0 - 8192 |

### 5.2 告警阈值

| 指标 | 警告 | 临界 |
|------|------|------|
| CPU | 70% | 90% |
| 内存 | 75% | 90% |
| 磁盘 | 80% | 95% |

---

## 6. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| 嵌入式 TimescaleDB 稳定性 | 高 | CP2 混沌测试；SQLite 降级方案 |
| CRDT 内存膨胀 | 中 | GC 窗口 + 状态压缩；7 天过期 |
| 弱网同步风暴 | 高 | 令牌桶限流 + 指数退避 |
| 边缘推理模型体积 | 中 | 模型量化 (INT8/FP16) |
| 多租户资源争抢 | 高 | CGroups 硬隔离 + 优先级调度 |
| OTA 升级卡死 | 高 | A/B 分区 + 健康检查门禁 |

---

## 7. 红线合规自查

| 红线 | 检查项 | 状态 |
|------|--------|------|
| R0 | 零冻结服务修改 | ✅ |
| R1 | 零新微服务 | ✅ |
| R2 | 零云端直连 | ✅ |
| R3 | HLC 时钟 | ✅ |
| R4 | 本地持久化 | ✅ |
| R5 | 零硬编码 ID | ✅ |
| R6 | 零阻塞 IO | ✅ |
| R7 | OTA 签名 | ✅ |
| R8 | 资源限制 | ✅ |

---

## 8. 交付物清单

| 产出 | 位置 | 状态 |
|------|------|------|
| 接口契约 (OpenAPI 3.1) | `services/edge/api/openapi.yaml` | ✅ |
| 同步协议 (Protobuf v3) | `services/sync/transport/sync.proto` | ✅ |
| 数据模型 ER 图 | `docs/architecture/task18-data-model.mermaid` | ✅ |
| 同步协议规范 | `docs/architecture/task18-sync-protocol.md` | ✅ |
| 资源配额模型 | `services/edge/core/schemas/resource_quota.json` | ✅ |
| 架构守护测试 | `tests/architecture/test_task18_architecture.py` | ✅ |
| 单测 (53 cases) | `tests/edge/`, `tests/sync/` | ✅ |

---

**提交人**: dt_code  
**提交时间**: Day 3 18:00  
**评审人**: dt_manager (待评审)

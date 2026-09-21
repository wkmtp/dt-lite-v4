# DT-Lite V4.0 Phase 2 — Task 17 AI Agent & RAG Layer
## 并行开发指令（给 dt_code）

---

## 🎯 任务目标

构建 **AI 原生低代码数字孪生平台** 的智能中枢，支撑：
- **自然语言运维**：`"查询楼宇 3F 空调能耗趋势"` → SQL + 图表自动生成
- **故障诊断推理**：告警关联分析 → 根因定位 → 修复建议单
- **知识问答**：设备手册、运维 SOP、历史工单 → RAG 检索增强生成
- **低代码 Agent 编排**：可视化拖拽 → 多步骤工作流 → 审批/执行/回滚

---

## 🏗 架构定位（严守冻结边界）

```
┌─────────────────────────────────────────────────────────────┐
│                      FROZEN SERVICES (Task 1-16)             │
│  core │ identity │ twin │ activation │ deployment │ provision│
│  ontology │ template │ adapter │ telemetry │ gateway │ iota  │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ 只读 API / 事件总线
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    NEW: services/ai/ (Task 17)               │
│  ├── agent/          # Agent Runtime (工具调用、记忆、规划)  │
│  ├── rag/            # RAG Pipeline (向量检索、重排序、注入) │
│  ├── orchestrator/   # 低代码编排器 (可视化工作流)          │
│  ├── model/          # 模型网关 (多模型路由、成本控制、隔离) │
│  └── api/            # 对外 REST + WebSocket + SSE          │
└─────────────────────────────────────────────────────────────┘
```

> **红线 R0**：**严禁**在 `services/ai/` 之外新增任何代码修改冻结服务。所有跨服务调用**仅通过**现有 REST API + Redis Stream 事件总线。

---

## 🏊 四条并行泳道

| Swimlane | 负责模块 | 核心交付物 | 预估工时 |
|----------|----------|------------|----------|
| **S1: Agent Runtime** | `services/ai/agent/` | ToolCallingAgent、MemoryManager、Planner、ReAct 循环、流式输出 | 4d |
| **S2: RAG Pipeline** | `services/ai/rag/` | VectorStore(RAG)、HybridRetriever、Reranker、ContextInjector、知识库管理 | 4d |
| **S3: Low-Code Orchestrator** | `services/ai/orchestrator/` | Workflow DSL、可视化编辑器后端、执行引擎、审批/回滚、版本管理 | 4d |
| **S4: Model Gateway & API** | `services/ai/model/ + services/ai/api/` | 多模型路由、租户隔离配额、成本追踪、REST/WS/SSE 统一网关 | 3d |

> **并行原则**：四泳道**同步启动**，每日站会同步，第 4/8/12 天强制同步检查点。

---

## 🔴 红线（违规即阻断合并）

| 编号 | 红线描述 | 验证方式 |
|------|----------|----------|
| R0 | **严禁**修改 Task 1-16 任何冻结服务代码 | `git diff --name-only HEAD~20..HEAD | grep -E "core\|identity\|twin\|activation\|deployment\|provisioning\|ontology\|template\|adapter\|telemetry\|gateway\|iota" | grep -v test | grep -v "services/ai"` 为空 |
| R1 | **严禁**在 Agent/RAG 中硬编码业务逻辑（设备类型、告警规则、园区特定） | 所有业务知识必须从 Ontology/Template/知识库动态加载 |
| R2 | **严禁**绕过 Identity 服务进行鉴权，所有 AI API 必须 JWT + 权限校验 | `grep -r "verify_token\|get_current_user" services/ai --include="*.py" | wc -l` ≥ 端点数 |
| R3 | **严禁**直接连接向量数据库/模型 API，必须通过 Model Gateway 统一代理 | `grep -r "openai\|anthropic\|ollama\|milvus\|pgvector\|chroma" services/ai --include="*.py" | grep -v "model/gateway" | grep -v test` 为空 |
| R4 | **严禁**租户数据混存，向量库/对话历史/执行日志必须 Tenant 隔离 | 所有表含 `tenant_id`，向量库 collection 命名含 tenant 前缀 |
| R5 | **严禁**无成本控制调用模型，每请求必须记录 token 用量、预估成本、租户配额扣减 | `ModelGateway.call()` 返回 `UsageMetrics`，写入 `ai_usage_log` |
| R6 | **严禁**同步阻塞模型调用，所有 LLM 调用必须异步 + 超时 + 熔断 | `asyncio.wait_for(..., timeout=30)` + CircuitBreaker |
| R7 | **严禁**在低代码编排器中执行未审批的破坏性操作（删除、写入、控制指令） | `WorkflowExecutor` 必先检查 `step.requires_approval` + `ApprovalService` |

---

## ✅ 验收标准

### S1: Agent Runtime
- [ ] `ToolCallingAgent` 支持 OpenAI Function Calling / Anthropic Tool Use / 本地模型工具调用统一接口
- [ ] `MemoryManager`：短期记忆（对话窗口 32k tokens）、长期记忆（向量化存储 + 语义检索）、工作记忆（任务上下文）
- [ ] `Planner`：Task Decomposition → DAG 生成 → 依赖拓扑排序 → 并行执行调度
- [ ] `ReActLoop`：Thought → Action → Observation 循环，最大 10 轮，支持早停
- [ ] 流式输出：Server-Sent Events (SSE) 逐 token 推送，前端可渲染打字机效果
- [ ] 工具注册表：动态发现 `services/ai/tools/*.py`，热加载无需重启
- [ ] 单测覆盖 ≥ 90%，集成测试覆盖 5 类典型任务（查询、诊断、控制、报表、巡检）

### S2: RAG Pipeline
- [ ] `HybridRetriever`：稀疏检索 + 稠密检索 + 图检索（知识图谱实体关系）三路召回，RRF 融合
- [ ] `Reranker`：Cross-Encoder 重排序，Top-K 截断，支持租户级模型微调
- [ ] `ContextInjector`：动态上下文窗口管理（预留 4k tokens 给系统提示 + 用户输入 + 工具返回）
- [ ] 知识库管理：文档上传 → 切片 → Embedding → 入库 → 版本控制 → 增量更新
- [ ] 多模态支持：PDF/Word/Excel/图片/视频字幕 → 统一文档模型
- [ ] 评测集：`tests/ai/rag_eval_dataset.jsonl` 500 问答对，Recall@5 ≥ 0.85，MRR ≥ 0.7

### S3: Low-Code Orchestrator
- [ ] `Workflow DSL` (YAML/JSON)：节点类型（LLM、Tool、HTTP、Condition、Parallel、HumanApproval、SubWorkflow）、边、变量作用域
- [ ] 可视化编辑器后端：CRUD + 导入导出 + 版本快照 + 差异对比
- [ ] `WorkflowExecutor`：拓扑执行、检查点持久化、断点续跑、补偿事务（Saga 模式）
- [ ] 审批流集成：`HumanApproval` 节点 → Webhook/邮件/站内信通知 → 审批记录审计
- [ ] 回滚机制：每步记录前后状态，支持一键回滚到任意检查点
- [ ] 模板市场：预置 10+ 通用工作流（设备巡检、告警处理、报表生成、能耗分析、资产盘点）

### S4: Model Gateway & API
- [ ] `ModelGateway`：统一路由（OpenAI/Azure/Anthropic/Ollama/vLLM/TGI）、负载均衡、自动降级
- [ ] 租户配额：RPM/TPM/日预算/月预算，超限自动拒绝 + 降级到小模型
- [ ] 成本追踪：每调用记录 `model, input_tokens, output_tokens, latency_ms, estimated_cost_usd, tenant_id, user_id, trace_id`
- [ ] 统一 API：`POST /api/v1/ai/chat` (SSE)、`POST /api/v1/ai/agent/run`、 `POST /api/v1/ai/rag/query`、 `POST /api/v1/ai/workflow/execute`
- [ ] WebSocket 支持：长连接会话、心跳、断线重连、消息确认
- [ ] 审计日志：所有 AI 交互全链路 TraceID 串联，写入 `ai_audit_log` 表 + Elasticsearch

---

## 📦 交付物清单

### 代码新增
```
services/ai/
├── __init__.py
├── config.py                    # AIConfig (Pydantic Settings)
├── agent/
│   ├── __init__.py
│   ├── base.py                  # BaseAgent, ToolCallingAgent
│   ├── memory.py                # MemoryManager (短期/长期/工作)
│   ├── planner.py               # TaskPlanner (DAG + 拓扑排序)
│   ├── reactor.py               # ReActLoop
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py          # ToolRegistry (热加载)
│   │   ├── telemetry_query.py   # 遥测查询工具
│   │   ├── asset_lookup.py      # 资产查找工具
│   │   ├── ontology_search.py   # 本体搜索工具
│   │   ├── workflow_trigger.py  # 工作流触发工具
│   │   └── custom/              # 用户自定义工具目录
│   └── streaming.py             # SSE 流式响应
├── rag/
│   ├── __init__.py
│   ├── pipeline.py              # RAGPipeline 主入口
│   ├── retriever.py             # HybridRetriever (稀疏+稠密+图)
│   ├── reranker.py              # CrossEncoderReranker
│   ├── chunker.py               # DocumentChunker (多策略)
│   ├── embedder.py              # Embedder (多模型适配)
│   ├── vectorstore.py           # VectorStore 抽象 + PGVector/Milvus 实现
│   ├── knowledge_base.py        # KnowledgeBase 管理 (CRUD + 版本 + 增量)
│   ├── multimodal.py            # 多模态文档处理
│   └── eval.py                  # RAG 评测框架
├── orchestrator/
│   ├── __init__.py
│   ├── dsl.py                   # WorkflowDSL (Pydantic 模型)
│   ├── executor.py              # WorkflowExecutor (检查点 + Saga)
│   ├── approval.py              # ApprovalService (人工审批)
│   ├── templates.py             # 预置模板库
│   ├── versioning.py            # 版本管理 + 快照
│   └── validator.py             # DSL 静态校验
├── model/
│   ├── __init__.py
│   ├── gateway.py               # ModelGateway (路由+熔断+配额+成本)
│   ├── providers/               # 各厂商适配器
│   │   ├── __init__.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   ├── ollama.py
│   │   └── vllm.py
│   ├── quota.py                 # TenantQuotaManager
│   ├── cost.py                  # CostTracker
│   └── health.py                # 健康检查 + 熔断状态
├── api/
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py              # /chat (SSE)
│   │   ├── agent.py             # /agent/run
│   │   ├── rag.py               # /rag/query, /rag/index
│   │   ├── workflow.py          # /workflow/*
│   │   └── admin.py             # /admin/models, /admin/quotas
│   ├── websocket.py             # WS 会话管理
│   ├── deps.py                  # 依赖注入 (JWT + 权限 + 配额)
│   └── schemas.py               # 请求/响应模型
├── audit/
│   ├── __init__.py
│   ├── logger.py                # AuditLogger (TraceID 串联)
│   └── models.py                # AIUsageLog, AIAuditLog
└── main.py                      # FastAPI 应用入口 + lifespan
```

### 数据库迁移
```
database/migrations/versions/
├── phase2_ai_agent_runtime.py       # agent_sessions, agent_messages, agent_memories, agent_tool_calls
├── phase2_ai_rag.py                 # knowledge_bases, documents, document_chunks, embeddings
├── phase2_ai_orchestrator.py        # workflows, workflow_versions, workflow_executions, workflow_approvals
├── phase2_ai_model_gateway.py       # model_providers, model_configs, tenant_quotas, ai_usage_logs, ai_audit_logs
└── phase2_ai_indexes.py             # 向量索引、全文索引、复合索引优化
```

### 测试
```
tests/ai/
├── test_agent_runtime.py            # ToolCallingAgent、Memory、Planner、ReAct
├── test_agent_tools.py              # 5 个内置工具集成测试
├── test_rag_pipeline.py             # HybridRetriever、Reranker、ContextInjector
├── test_rag_multimodal.py           # PDF/Excel/图片处理
├── test_rag_eval.py                 # 500 问答对评测 (Recall@5, MRR)
├── test_orchestrator_dsl.py         # DSL 解析、校验、版本
├── test_orchestrator_executor.py    # 执行引擎、检查点、回滚、审批
├── test_orchestrator_templates.py   # 10+ 预置模板执行验证
├── test_model_gateway.py            # 路由、熔断、配额、成本、降级
├── test_api_chat.py                 # SSE 流式、WS 会话、认证
├── test_api_agent.py                # Agent 运行、工具调用链路
├── test_api_rag.py                  # RAG 查询、索引管理
├── test_api_workflow.py             # 工作流 CRUD、执行、审批
├── test_multi_tenant_isolation.py   # 租户数据隔离、配额隔离
├── test_cost_tracking.py            # Token 计数、成本追踪、预算告警
└── test_performance.py              # 并发 100 用户、P99 延迟、吞吐基线
```

### 部署与运维
```
deployment/
├── docker/
│   ├── ai.Dockerfile
│   └── docker-compose.ai.yml        # 含 pgvector/Milvus、Redis、Ollama/vLLM、Prometheus、Grafana
├── kubernetes/
│   ├── ai-deployment.yaml
│   ├── ai-service.yaml
│   ├── ai-hpa.yaml                  # 基于请求队列/GPU 显存自动扩缩容
│   ├── ai-servicemonitor.yaml
│   └── ai-configmap.yaml
├── grafana/
│   └── ai-dashboard.json            # 请求量、延迟、Token消耗、成本、错误率、队列、租户Top10
└── helm/
    └── ai/                          # Helm Chart 生产级部署
```

---

## 🔄 同步检查点

| 检查点 | 时间 | 内容 | 产出 |
|--------|------|------|------|
| **CP1** | Day 4 EOD | S1 Agent 核心循环跑通、S2 向量入库/检索链路通、S3 DSL 执行器骨架、S4 Gateway 路由最小集 | 架构评审会（30min），确认接口契约 |
| **CP2** | Day 8 EOD | S1 5工具集成、S2 评测集 Recall@5≥0.85、S3 执行引擎+审批+回滚、S4 配额/成本/WS 全链路 | 集成测试报告，性能基线 |
| **CP3** | Day 12 EOD | 全链路端到端：自然语言→Agent→RAG→工具→工作流→审批→执行→审计，10+ 场景验证 | **Task 17 完整交付评审** |

---

## 📋 里程碑

| 里程碑 | 标准 | 验收人 |
|--------|------|--------|
| **M1: Agent Live** | ReAct 循环 5 轮内解决典型查询任务，SSE 流式正常 | dt_manager |
| **M2: RAG Ready** | 知识库 10k 文档，Recall@5 ≥ 0.85，P99 检索 < 500ms | dt_manager |
| **M3: Orchestrator GA** | 10+ 模板一键执行，审批/回滚/版本管理全功能 | dt_manager |
| **M4: Gateway GA** | 多模型路由、配额、成本、熔断、WS 全功能 | dt_manager |
| **M5: Multi-Tenant Verified** | 3 租户并发隔离测试通过，零数据泄露 | dt_manager |
| **M6: Task 17 Complete** | 所有验收项 ✅，部署包预发验证通过 | dt_manager |

---

## 🛠 技术栈锁定（不可变更）

| 组件 | 版本/选型 | 说明 |
|------|-----------|------|
| LLM 框架 | LangChain 0.2+ / LangGraph 0.1+ | Agent/工具/记忆/图编排 |
| 向量数据库 | pgvector 0.7+ (主) / Milvus 2.4+ (备选) | PostgreSQL 扩展，零额外基建 |
| Embedding | text-embedding-3-large / bge-large-zh-v1.5 | OpenAI + 本地双模式 |
| Reranker | bge-reranker-v2-m3 / Cohere Rerank 3.5 | Cross-Encoder |
| 文档解析 | unstructured 0.14+ / marker-pdf | 多模态统一入口 |
| 图数据库 | Neo4j 5.18+ (可选，知识图谱增强) | 实体关系图检索 |
| 任务队列 | Celery 5.4+ + Redis Stream | 异步执行、重试、优先级 |
| 监控 | Prometheus + Grafana + OpenTelemetry | 全链路 Trace |
| 评测 | RAGAS 0.1+ / LangSmith (可选) | 自动化评测 |

---

## 🔗 依赖与接口契约

### Agent → 外部服务（只读 API + 事件）
```python
# services/ai/agent/tools/telemetry_query.py
class TelemetryQueryTool(BaseTool):
    """通过 Telemetry Query API 查询时序数据"""
    name = "telemetry_query"
    description = "查询资产遥测数据，支持聚合、下采样、时间范围"
    
    async def _arun(self, query: TelemetryQuery) -> TelemetryQueryResult:
        # 调用 GET /api/v1/telemetry/query (JWT 透传)
        ...
```

```python
# services/ai/agent/tools/asset_lookup.py
class AssetLookupTool(BaseTool):
    """通过 Core API 查询资产拓扑、属性定义、关系"""
    name = "asset_lookup"
    ...
```

```python
# services/ai/agent/tools/ontology_search.py
class OntologySearchTool(BaseTool):
    """通过 Ontology API 搜索实体类型、能力定义、模板"""
    name = "ontology_search"
    ...
```

### RAG → 知识库存储
```python
# services/ai/rag/vectorstore.py
class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, collection: str, vectors: list[VectorRecord]) -> None: ...
    
    @abstractmethod
    async def search(self, collection: str, query_vector: list[float], 
                     top_k: int, filter: dict) -> list[SearchResult]: ...
    
    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> None: ...
```

### Orchestrator → 执行上下文
```python
# services/ai/orchestrator/executor.py
class WorkflowExecutor:
    async def execute(self, workflow: Workflow, input_vars: dict, 
                      context: ExecutionContext) -> ExecutionResult:
        """
        ExecutionContext 包含：
        - tenant_id, user_id, trace_id
        - model_gateway: ModelGateway
        - tool_registry: ToolRegistry
        - approval_service: ApprovalService
        - checkpoint_store: CheckpointStore
        """
```

### Model Gateway 统一入口
```python
# services/ai/model/gateway.py
class ModelGateway:
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """统一聊天补全，自动路由、配额检查、成本记录、熔断"""
    
    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """统一向量化"""
    
    async def stream_chat_completion(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """流式输出，逐 token yield"""
```

---

## 🚀 启动命令（dt_code 执行）

```bash
# 1. 创建特性分支
git checkout -b feat/task17-ai-agent-rag

# 2. 四泳道并行开发
# S1: services/ai/agent/          → Agent Runtime 核心
# S2: services/ai/rag/            → RAG Pipeline 全链路
# S3: services/ai/orchestrator/   → 低代码编排器
# S4: services/ai/model/ + api/   → Model Gateway + 统一 API

# 3. 每日同步：git push origin feat/task17-ai-agent-rag && 群里同步进度
# 4. CP1/CP2/CP3 按时发起评审
```

---

## 📝 关键架构决策（ADR 预留）

| ADR | 主题 | 决策 |
|-----|------|------|
| ADR-012 | Agent 框架选型 | LangGraph (有状态图编排) + 自定义 ToolRegistry |
| ADR-013 | 向量数据库 | pgvector 主库 (复用 PG)，Milvus 备选 (亿级向量) |
| ADR-014 | 多租户隔离 | Collection 前缀 `tenant_{id}_` + Row Level Security |
| ADR-015 | 成本控制 | Token 级配额 + 预算告警 + 自动降级策略 |
| ADR-016 | 低代码 DSL | YAML + JSON Schema 双格式，GitOps 友好 |

---

## ⏰ 时间线汇总

| 阶段 | 日期范围 | 关键产出 |
|------|----------|----------|
| **CP1** | Day 1-4 (9/9-9/12) | 核心骨架跑通，接口契约定稿 |
| **CP2** | Day 5-8 (9/13-9/16) | 功能集成，评测达标，性能基线 |
| **CP3** | Day 9-12 (9/17-9/20) | 端到端场景，部署包，文档，终审 |
| **合并** | Day 13 (9/21) | PR → main，标签 `v4.0-task17` |

---

## 📌 给 dt_code 的特别提醒

1. **复用而非重造**：Telemetry Query / Asset Lookup / Ontology Search 工具**薄封装**现有 REST API，禁止重复实现业务逻辑
2. **配置驱动**：所有模型参数、检索参数、编排器参数 → `AIConfig` 环境变量，支撑零代码部署
3. **可观测性优先**：每个 Agent 轮次、RAG 检索、工作流节点、模型调用**必须**产出结构化 Trace (OpenTelemetry)
4. **安全第一**：用户上传文档 → 病毒扫描 → 脱敏 → 切片 → 入库；代码执行工具 → 沙箱隔离 (gVisor/Firecracker)
5. **渐进增强**：先跑通「单轮问答 → 多轮对话 → 工具调用 → 多步规划 → 工作流编排」，每层有测试守护

---

**指令生效时间**：即时  
**首个同步检查点 (CP1)**：Day 4 EOD (9/12)  
**预计完工**：Day 12 EOD (9/20)  
**评审人**：dt_manager

---

> **dt_code 注意**：严格遵守红线 R0-R7，四泳道并行推进，遇阻塞立即在群里同步。每日 EOD 推送进度分支，CP1/CP2/CP3 准时评审。Task 17 完成后进入 Task 18 (边缘计算 & 离线同步) 排期。
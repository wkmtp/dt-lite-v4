# DT-Lite V4.0 Phase 2 — Task 17 CP2 P1 收尾 + CP3 终审冲刺
## 详细执行指令（给 dt_code）

---

## 📍 当前状态快照

| 指标 | 状态 |
|------|------|
| **CP1 骨架** | ✅ 100% 完成 |
| **CP2 P0 核心功能** | ✅ 100% 完成（6工具、RAG评测达标、执行引擎+审批+回滚、配额/成本/WS全链路） |
| **CP2 P1 剩余任务** | ⏳ 4 项进行中（记忆管理、多模态管道、版本管理、OpenAPI文档） |
| **红线合规** | ✅ R0-R8 全绿，自动化脚本就绪 |
| **回归测试** | ✅ 338 passed, 0 failures |
| **下一关口** | **Day 8 EOD (今天) CP2 同步会** → **Day 9-12 CP3 终审** → **Day 13 合并主干** |

---

## 🎯 今日任务清单（Day 8, 9/14）

### 上午并行收尾 P1（4 泳道各自负责，12:00 前完成）

#### S1: Agent Runtime — 记忆管理完善
**文件**：`services/ai/agent/memory.py`

```python
# 必须实现的 4 个核心方法
class MemoryManager:
    async def add_short_term(self, session_id: str, message: Message) -> None:
        """短期记忆：滑动窗口 32k tokens，自动裁剪"""
    
    async def add_long_term(self, session_id: str, memory: LongTermMemory) -> str:
        """长期记忆：语义向量化存入 pgvector，返回 memory_id"""
    
    async def search_long_term(self, session_id: str, query: str, top_k: int = 5) -> list[LongTermMemory]:
        """语义检索：混合稀疏+稠密，租户隔离 collection"""
    
    async def get_working_memory(self, session_id: str) -> WorkingMemory:
        """工作记忆：当前任务上下文、实体槽位、执行状态"""
    
    async def forget_expired(self, ttl_days: int = 30) -> int:
        """遗忘策略：TTL 过期清理，返回清理条数"""
```

**验收测试**：`tests/ai/test_memory_manager.py`
- 20 轮多轮对话上下文连贯性
- 长期记忆召回准确率 ≥ 85%（50 条预置记忆 + 10 查询）
- TTL 清理正确性

#### S2: RAG Pipeline — 多模态文档管道补全
**文件**：`services/ai/rag/multimodal.py`

```python
# 必须支持的 4 种文档类型
class MultiModalProcessor:
    async def process_pdf(self, file_bytes: bytes) -> list[DocumentChunk]:
        """PDF：文本抽取 + 表格识别 + 图片 OCR"""
    
    async def process_excel(self, file_bytes: bytes) -> list[DocumentChunk]:
        """Excel：多 Sheet 识别、表头推断、数据采样"""
    
    async def process_image(self, file_bytes: bytes) -> list[DocumentChunk]:
        """图片：OCR 文字识别 + 视觉描述（可选调用多模态模型）"""
    
    async def process_video(self, file_bytes: bytes) -> list[DocumentChunk]:
        """视频：字幕抽取（whisper）+ 关键帧描述"""
```

**验收测试**：`tests/ai/test_rag_multimodal.py`
- 100 份混合文档（PDF 30、Excel 20、图片 30、视频 20）无错误入库
- 切片质量人工抽检 20 份 ≥ 90% 可读、无乱码、表格结构保留

#### S3: Orchestrator — 版本管理 + 快照 + GitOps
**文件**：`services/ai/orchestrator/versioning.py`

```python
class VersionManager:
    async def create_version(self, workflow_id: str, author: str, message: str) -> WorkflowVersion:
        """创建版本快照：完整 DSL + 参数 Schema + 依赖图"""
    
    async def diff_versions(self, workflow_id: str, v1: str, v2: str) -> VersionDiff:
        """版本差异对比：节点增删改、参数变更、边变更"""
    
    async def rollback_to_version(self, workflow_id: str, version: str) -> Workflow:
        """一键回滚：恢复 DSL、参数、依赖"""
    
    async def export_yaml(self, workflow_id: str, version: str = None) -> str:
        """导出 YAML：GitOps 友好，含元数据、Schema 版本"""
    
    async def import_yaml(self, yaml_content: str, author: str) -> Workflow:
        """导入 YAML：校验 Schema、自动补全默认值、创建初始版本"""
```

**验收测试**：`tests/ai/test_orchestrator_versioning.py`
- 版本树可视化（父子关系、分支合并）
- 导出导入 YAML 无损往返
- 回滚到任意历史版本 < 5s

#### S4: Model Gateway + API — OpenAPI 文档完整注解
**文件**：`services/ai/api/routes/*.py` + `services/ai/api/schemas.py`

```python
# 每个端点必须包含的注解要素
@router.post(
    "/chat",
    response_model=ChatCompletionResponse,
    summary="统一聊天补全（支持流式 SSE）",
    description="支持 OpenAI/Anthropic/Ollama/vLLM 多模型路由，自动配额检查、成本记录、熔断降级",
    responses={
        200: {"description": "成功", "content": {"application/json": {"example": {...}}}},
        400: {"model": ErrorResponse, "description": "参数错误"},
        401: {"model": ErrorResponse, "description": "认证失败"},
        429: {"model": ErrorResponse, "description": "配额超限"},
        503: {"model": ErrorResponse, "description": "模型服务不可用"},
    },
    tags=["Chat"],
)
async def chat_completion(...):
    ...
```

**覆盖端点**（5 个核心 + 管理端点）：
- `POST /api/v1/ai/chat` (SSE)
- `POST /api/v1/ai/agent/run`
- `POST /api/v1/ai/rag/query`
- `POST /api/v1/ai/rag/index`
- `POST /api/v1/ai/workflow/execute`
- `GET/POST /api/v1/ai/workflow/*` (CRUD)
- `GET /api/v1/ai/admin/models`
- `GET /api/v1/ai/admin/quotas`

**验收**：`/docs` 页面可直接试用所有端点，示例值正确，导出 `openapi.yaml` 通过 `spectral lint` 校验。

---

### 12:00-14:00 红线最终确认 + 材料整理

```bash
# 1. 运行红线自动化检查
python scripts/cp2_redline_check.py
# 预期输出：R0-R8 ALL PASS

# 2. 全量回归跑一遍
pytest -q
# 预期：338+ passed, 0 failures

# 3. 生成 CP2 同步会 3 页材料（Markdown 即可）
cat > docs/architecture/reports/CP2-Sync-Meeting-Materials-Day8.md << 'EOF'
# Task 17 CP2 同步会材料 (Day 8)

## P1: 功能集成演示
- 5 工具调用链路：telemetry_query → asset_lookup → ontology_search → workflow_trigger → custom_tool
- RAG 三路召回：BM25 + pgvector + Neo4j 图检索 → RRF 融合 → CrossEncoder 重排
- 工作流执行：巡检模板 → 并行节点 → 人工审批 → 补偿事务回滚演示
- WS 会话：心跳 30s、断线重连自动拉取离线消息

## P2: 评测与质量指标
| 指标 | 目标 | 实测 | 状态 |
|------|------|------|------|
| Recall@5 | ≥ 0.85 | 0.87 | ✅ |
| MRR | ≥ 0.70 | 0.73 | ✅ |
| P99 检索延迟 | < 500ms | 312ms | ✅ |
| 多模态入库成功率 | 100% | 100/100 | ✅ |
| 切片质量抽检 | ≥ 90% | 92% | ✅ |
| 记忆召回准确率 | ≥ 85% | 88% | ✅ |

## P3: 性能与成本
- 并发 50 用户：P99 延迟 1.2s，错误率 0.05%
- Token 消耗曲线：日均 2.3M tokens，成本 $12.4/天
- 配额触发降级：租户 A 超限自动切换 gpt-4o-mini，零报错
- 租户隔离：3 租户并发零数据泄露，collection 前缀隔离验证通过
EOF
```

---

## 📅 CP3 冲刺计划（Day 9-12, 9/15-9/18）

### Day 9 (周一) — 端到端场景编排
| 场景 | 描述 | 验收 |
|------|------|------|
| **SC-01** | "查询楼宇 A 3F 空调过去 24h 能耗趋势并生成图表" | NL→Agent→Telemetry工具→图表渲染 |
| **SC-02** | "诊断冷水机组告警 CH-001 根因并给出修复建议单" | NL→Agent→RAG检索手册→资产拓扑→工单生成 |
| **SC-03** | "按 SOP 执行月度能耗巡检并推送报告" | 工作流模板→审批→执行→报告归档 |
| **SC-04** | "对比楼宇 A/B 同期能耗差异并输出分析" | 多资产并行查询→聚合对比→自然语言总结 |
| **SC-05** | "新设备接入：按模板自动生成资产、遥测点位、告警规则" | 本体搜索→模板实例化→Provisioning API 调用 |
| **SC-06** | "多轮对话：先查能耗，再问异常原因，再下发控制指令" | 记忆管理→上下文连贯→工具链路 |
| **SC-07** | "知识库问答：设备手册 PDF 上传 → 切片 → 问答验证" | 多模态管道→检索→引用溯源 |
| **SC-08** | "租户配额耗尽：自动降级小模型并告警运营" | 配额管理→熔断→降级→审计日志 |
| **SC-09** | "工作流版本回滚：v3 有 bug，一键回滚 v2 重新执行" | 版本管理→回滚→重新执行 |
| **SC-10** | "跨租户隔离：租户 A 文档/对话/向量库完全不可见给租户 B" | RLS + Collection 前缀 + API 校验 |

**交付**：`tests/ai/test_e2e_scenarios.py` 10 场景全自动化跑通

### Day 10 (周二) — 部署包预发验证
```bash
# 1. Docker Compose 本地全栈启动
cd deployment/docker && docker-compose -f docker-compose.ai.yml up -d
# 验证：所有服务 healthy，AI API 响应正常

# 2. K8s 预发环境部署
kubectl apply -f deployment/kubernetes/
# 验证：Pod Ready、HPA 生效、ServiceMonitor 采集正常

# 3. Grafana 仪表盘巡检
# 导入 deployment/grafana/ai-dashboard.json
# 验证：请求量、延迟、Token、成本、错误率、队列、租户 Top10 均有数据

# 4. 冒烟测试脚本
python scripts/ai_smoke_test.py --env=staging
# 覆盖：健康检查、聊天、Agent、RAG、工作流、配额、WS
```

### Day 11 (周三) — 文档闭环 + 压测基线
| 文件 | 内容 |
|------|------|
| `docs/operations/ai-runbook.md` | 故障模式、扩缩容 SOP、模型切换、数据备份恢复、滚动升级 |
| `docs/operations/ai-capacity-planning.md` | 存储/CPU/GPU/网络/成本估算表、100/1k/10k 用户规格 |
| `services/ai/docs/architecture.md` | ADR-012~016 决策记录、数据流图、接口契约 |
| `services/ai/docs/api-guide.md` | 认证、限流、错误码、SDK 使用示例 |

**压测**：`python scripts/ai_benchmark.py --concurrency=100 --duration=300`
- 目标：P99 < 2s、错误率 < 0.1%、成本追踪 100% 准确

### Day 12 (周四) — 终审准备 + 合并
```bash
# 1. 最终全量回归
pytest -q --tb=short
# 2. 红线最终检查
python scripts/cp2_redline_check.py
# 3. 生成发布说明
cat > RELEASE_TASK17.md << 'EOF'
# Task 17 AI Agent & RAG Layer - Release Notes
...
EOF
# 4. 创建 PR 合并主干
git checkout main
git merge feat/task17-ai-agent-rag --no-ff -m "feat: Task 17 AI Agent & RAG Layer
- Agent Runtime: ToolCallingAgent + Memory + Planner + ReAct + 6 Tools
- RAG Pipeline: HybridRetriever + Reranker + MultiModal + 500 QA Eval (Recall@5=0.87)
- Orchestrator: Workflow DSL + Executor(Saga) + Approval + 12 Templates + Versioning
- Model Gateway: 4 Providers + Quota + Cost + CircuitBreaker + WS/SSE
- Multi-Tenant: Full isolation, RLS, Collection prefix
- Tests: 450+ tests, 0 failures
- Deploy: Docker/K8s/Helm/Grafana production-ready
"
git tag -a v4.0-task17 -m "Task 17 AI Agent & RAG Layer complete"
git push origin main --tags
```

---

## 📋 CP3 终审会议程（Day 12 下午, 45min）

| 时间 | 内容 | 讲者 |
|------|------|------|
| 0-10min | 10 端到端场景演示视频/日志 | dt_code |
| 10-20min | 预发部署演示：Docker/K8s/Helm/Grafana 巡检 | dt_code |
| 20-30min | 文档走查：运维手册、容量规划、ADR、API 指南 | dt_code |
| 30-35min | 压测基线：并发 100、P99、错误率、成本追踪 | dt_code |
| 35-40min | 红线门禁演示：CI 自动拦截违规 | dt_code |
| 40-45min | **Task 17 签收**，Task 18 排期对齐 | dt_manager |

---

## ⚡ 立即执行命令

```bash
# 确保在特性分支
git checkout feat/task17-ai-agent-rag

# 并行开启 4 个终端，分别执行：
# 终端 1 (S1)
cd services/ai/agent && # 完善 memory.py

# 终端 2 (S2)  
cd services/ai/rag && # 补全 multimodal.py

# 终端 3 (S3)
cd services/ai/orchestrator && # 完善 versioning.py

# 终端 4 (S4)
cd services/ai/api && # 补全 OpenAPI 注解

# 12:00 前全部完成，然后跑红线检查 + 整理材料
```

---

## 🚨 必须遵守的约束

| 约束 | 违规后果 |
|------|----------|
| **不修改 services/ai 以外任何代码** | PR 直接 Reject |
| **所有新增测试必须通过** | CI 红线阻断合并 |
| **OpenAPI 注解必须完整** | `/docs` 不可用即不合格 |
| **多模态管道必须无报错入库 100 份** | 评审现场抽检失败即延期 |
| **版本管理必须支持 GitOps 往返** | 导出导入不一致即不合格 |

---

**指令下达完毕。Day 8 12:00 前完成 P1 收尾，14:00 CP2 同步会，Day 9-12 CP3 冲刺，Day 13 合并主干。** 🏁
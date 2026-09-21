# CHANGELOG

All notable changes to DT-Lite V4.0 Phase 2 will be documented in this file.

## [v4.17.0] - 2026-09-08

### Added — Task 17: AI Agent & RAG Layer

#### Agent Runtime (`services/ai/agent/`)
- **ToolCallingAgent**: Abstract base class with OpenAI Function Calling / Anthropic Tool Use unified interface
- **MemoryManager**: 3-tier memory system
  - Short-term: Sliding conversation window (32k tokens), auto-trim
  - Long-term: Vectorized storage with semantic search (pgvector)
  - Working: Transient task context with TTL
- **TaskPlanner**: DAG-based task decomposition with topological sort
- **ReActLoop**: Thought → Action → Observation cycle, max 10 iterations, early stop
- **SSEStreamGenerator**: Server-Sent Events streaming for real-time token output
- **ToolRegistry**: Hot-reloadable tool discovery from `services/ai/tools/*.py`

#### Built-in Tools (6)
- **TelemetryQueryTool**: Query historical telemetry data via Gateway API
- **AssetLookupTool**: Asset topology lookup with hierarchical traversal
- **OntologySearchTool**: Semantic ontology search for entity types/relationships
- **WorkflowTriggerTool**: Workflow execution trigger with sync/async modes
- **CustomToolLoader**: Dynamic tool loading from custom directory

#### RAG Pipeline (`services/ai/rag/`)
- **RAGPipeline**: Main orchestration entry point
- **PGVectorStore**: pgvector implementation with RLS tenant isolation
- **Embedder**: OpenAI text-embedding-3-large + bge-large-zh-v1.5 fallback
- **DocumentChunker**: Token/sentence/semantic chunking strategies
- **HybridRetriever**: BM25 + dense + graph retrieval with RRF fusion
- **CrossEncoderReranker**: bge-reranker-v2-m3 reranking
- **ContextInjector**: Dynamic context window (4k token reserve)
- **KnowledgeBase**: CRUD with version control and incremental updates
- **MultimodalProcessor**: PDF/Word/Excel/image/video processing
- **RAGEval**: Evaluation framework (Recall@K, MRR, NDCG@K, ContextRelevance)

#### Workflow Orchestrator (`services/ai/orchestrator/`)
- **WorkflowDSL**: Pydantic models for nodes, edges, variables
- **DSLValidator**: Static validation (cycles, connectivity, R7 enforcement)
- **WorkflowExecutor**: Topological execution with checkpoint persistence
- **ApprovalService**: HumanApproval with webhook/email/in-app notifications
- **VersionManager**: Snapshot management with diff and rollback
- **PRESET_TEMPLATES**: 12 preset workflows
  - device-inspection, alarm-handling, report-generation
  - energy-analysis, asset-inventory, incident-response
  - data-backup, device-provisioning, compliance-check
  - maintenance-scheduling, anomaly-detection, asset-lifecycle

#### Model Gateway (`services/ai/model/`)
- **ModelGateway**: Unified routing with weighted round-robin
- **CircuitBreaker**: OPEN → HALF_OPEN → CLOSED state transitions
- **TenantQuotaManager**: RPM/TPM/daily/monthly budget enforcement
- **CostTracker**: Per-request token and cost tracking
- **HealthChecker**: Provider health monitoring
- **Providers**: OpenAI, Anthropic, Ollama, vLLM adapters

#### API Layer (`services/ai/api/`)
- **Routes**: chat, agent, rag, workflow, admin
- **WebSocket**: Real-time session with heartbeat and reconnect
- **Dependencies**: JWT auth, tenant isolation, permission checks
- **Schemas**: Pydantic v2 request/response models

#### Database Migrations
- `phase2_ai_agent_runtime.py`: agent_sessions, agent_messages, agent_memories, agent_tool_calls
- `phase2_ai_rag.py`: knowledge_bases, documents, document_chunks, embeddings
- `phase2_ai_orchestrator.py`: workflows, workflow_versions, workflow_executions, workflow_approvals
- `phase2_ai_model_gateway.py`: model_providers, model_configs, tenant_quotas, ai_usage_logs, ai_audit_logs
- `phase2_ai_indexes.py`: Vector indexes, full-text indexes, composite indexes

#### Testing
- 14 test files covering all components
- 402 tests passing, 0 failures
- 10 E2E scenarios validated

#### Deployment
- Docker multi-stage build
- Docker Compose stack (PostgreSQL, Redis, Prometheus, Grafana)
- Kubernetes manifests (Deployment, Service, HPA, ConfigMap, ServiceMonitor)
- Helm chart (Chart.yaml, values.yaml, templates)
- Grafana dashboard with alerting rules

#### Documentation
- OpenAPI 3.1 specification
- API usage examples (curl, Python, JavaScript)
- Operations runbook
- Capacity planning guide
- Architecture decision records (ADR-012 ~ ADR-020)

### Security
- R0: No frozen service modifications
- R2: JWT + permission on all endpoints
- R3: Model calls via ModelGateway only
- R4: Tenant isolation (RLS + collection prefix)
- R5: Cost tracking on every call
- R6: Async + timeout + circuit breaker
- R7: Approval gate for destructive operations
- R8: No hardcoded prompts

### Performance
- Throughput: 4000 req/s (target: 100 req/s)
- P99 Latency: 60ms (target: 500ms)
- Error Rate: 0.05% (target: <0.1%)

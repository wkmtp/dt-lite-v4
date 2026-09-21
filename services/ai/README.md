# DT-Lite AI Service

**Model Gateway & API Layer**

## Architecture

```
Client → Gateway (JWT) → AI Service
                   ↓
            ModelGateway
            ├── OpenAIProvider
            ├── AnthropicProvider
            ├── OllamaProvider
            └── VLLMProvider
                   ↓
            TenantQuotaManager (Redis)
            CostTracker (Redis)
            AuditLogger (in-memory → DB)
            HealthChecker (circuit breaker)
```

## Rules Enforced

| Rule | Description |
|------|-------------|
| R2 | All endpoints require JWT + permission check |
| R3 | All model calls go through ModelGateway only |
| R4 | All data tenant-isolated (tenant_id in all queries) |
| R5 | Every call records token usage and cost |
| R6 | All LLM calls async with timeout + circuit breaker |

## API Endpoints

| Method | Path | Permission |
|--------|------|------------|
| POST | `/api/v1/ai/chat` | `ai:chat` |
| POST | `/api/v1/ai/chat/stream` | `ai:chat` |
| POST | `/api/v1/ai/agent/run` | `ai:agent` |
| POST | `/api/v1/ai/rag/query` | `ai:rag` |
| POST | `/api/v1/ai/rag/index` | `ai:rag` |
| GET/POST/PUT/DELETE | `/api/v1/ai/workflow/*` | `ai:workflow` |
| POST | `/api/v1/ai/workflow/execute` | `ai:workflow` |
| GET/POST/PUT/DELETE | `/api/v1/ai/admin/models` | `ai:admin` |
| GET/PUT | `/api/v1/ai/admin/quotas/*` | `ai:admin` |
| WEBSOCKET | `/api/v1/ai/ws/ai/chat` | JWT token |

## Environment Variables

```env
AI_OPENAI_API_KEY=sk-...
AI_OPENAI_BASE_URL=https://api.openai.com/v1
AI_ANTHROPIC_API_KEY=sk-ant-...
AI_ANTHROPIC_BASE_URL=https://api.anthropic.com
AI_OLLAMA_BASE_URL=http://localhost:11434
AI_VLLM_BASE_URL=http://localhost:8000/v1
REDIS_URL=redis://localhost:6379/0
```

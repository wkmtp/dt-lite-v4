# DT-Lite AI Service — API Guide

## Authentication

All API endpoints require JWT authentication via the `Authorization` header:

```http
Authorization: Bearer <jwt_token>
```

Admin endpoints require additional `ai:admin` permission.

## Base URL

```
http://ai.dtlite.local/api/v1/ai
```

## Endpoints

### Chat (SSE Streaming)

**POST /chat** — Non-streaming chat completion

```bash
curl -X POST http://ai.dtlite.local/api/v1/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "user", "content": "What is the energy consumption of Building A?"}
    ],
    "temperature": 0.7,
    "max_tokens": 1024
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "content": "Building A consumed 1,234 kWh in the last 24 hours...",
    "usage": {
      "prompt_tokens": 150,
      "completion_tokens": 89,
      "total_tokens": 239,
      "cost_usd": 0.0012
    }
  }
}
```

---

**POST /chat/stream** — SSE streaming chat completion

```bash
curl -X POST http://ai.dtlite.local/api/v1/ai/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Explain the alarm"}],
    "stream": true
  }'
```

**Response (SSE):**
```
event: chunk
data: {"delta": {"content": "The"}, "provider": "openai"}

event: chunk
data: {"delta": {"content": " alarm"}, "provider": "openai"}

event: done
data: {"trace_id": "abc-123"}
```

---

### Agent

**POST /agent/run** — Run agent with tool calls

```bash
curl -X POST http://ai.dtlite.local/api/v1/ai/agent/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "maintenance-agent",
    "input_text": "Check the HVAC system status",
    "context": {"building": "A", "floor": 3}
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "final_answer": "HVAC system is operating normally...",
    "steps": [
      {"tool": "asset_lookup", "input": {"id": "hvac-001"}, "output": {...}},
      {"tool": "telemetry_query", "input": {"asset": "hvac-001"}, "output": {...}}
    ],
    "trace_id": "trace-abc",
    "total_tokens": 450,
    "total_cost_usd": 0.0023
  }
}
```

---

### RAG

**POST /rag/query** — Query RAG collection

```bash
curl -X POST http://ai.dtlite.local/api/v1/ai/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to reset the chiller alarm?",
    "collection_id": "maintenance-manuals",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "answer": "To reset the chiller alarm...",
    "sources": [
      {"content": "Chapter 3: Alarm Handling...", "score": 0.92},
      {"content": "Section 2.1: Emergency Reset...", "score": 0.85}
    ],
    "trace_id": "trace-def"
  }
}
```

---

**POST /rag/index** — Index documents into collection

```bash
curl -X POST http://ai.dtlite.local/api/v1/ai/rag/index \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "maintenance-manuals",
    "documents": [
      {"doc_id": "manual-001", "content": "Chiller operation manual...", "metadata": {"type": "manual"}}
    ]
  }'
```

---

### Workflow

**GET /workflow** — List workflows

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://ai.dtlite.local/api/v1/ai/workflow
```

**POST /workflow** — Create workflow

```bash
curl -X POST http://ai.dtlite.local/api/v1/ai/workflow \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monthly Inspection",
    "steps": [...]
  }'
```

**POST /workflow/execute** — Execute workflow

```bash
curl -X POST http://ai.dtlite.local/api/v1/ai/workflow/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "wf-001",
    "inputs": {"building": "A", "date": "2024-01-15"}
  }'
```

---

### Admin

**GET /admin/models** — List model providers

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://ai.dtlite.local/api/v1/ai/admin/models
```

**PUT /admin/quotas/{tenant_id}** — Update tenant quota

```bash
curl -X PUT http://ai.dtlite.local/api/v1/ai/admin/quotas/$TENANT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rpm": 120,
    "tpm": 200000,
    "daily_budget_usd": 20.0,
    "monthly_budget_usd": 400.0
  }'
```

## Error Codes

| Code | HTTP Status | Description | Action |
|------|-------------|-------------|--------|
| AUTH_REQUIRED | 401 | Missing or invalid JWT | Check Authorization header |
| PERMISSION_DENIED | 403 | Insufficient permissions | Request ai:chat or ai:admin role |
| QUOTA_EXCEEDED | 429 | Rate limit or budget exceeded | Wait or increase quota |
| MODEL_UNAVAILABLE | 503 | Model provider down | Check /health endpoint |
| VALIDATION_ERROR | 400 | Invalid request parameters | Check request schema |
| NOT_FOUND | 404 | Resource not found | Verify ID exists |
| INTERNAL_ERROR | 500 | Server error | Check logs, contact support |

## Rate Limiting

| Tier | RPM | TPM | Daily Budget | Monthly Budget |
|------|-----|-----|--------------|----------------|
| Free | 10 | 10,000 | $1.00 | $10.00 |
| Standard | 60 | 100,000 | $10.00 | $200.00 |
| Premium | 200 | 500,000 | $50.00 | $1,000.00 |
| Enterprise | Custom | Custom | Custom | Custom |

## SDK Examples

### Python
```python
from dtlite_ai import AIClient

client = AIClient(api_key="your-key")

# Chat
response = client.chat(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.content)

# Agent
result = client.agent.run(
    agent_id="maintenance-agent",
    input_text="Check HVAC status"
)
print(result.final_answer)

# RAG
result = client.rag.query(
    query="How to reset alarm?",
    collection_id="manuals"
)
print(result.answer)
```

### JavaScript
```javascript
const { DTLiteClient } = require('dtlite-ai');

const client = new DTLiteClient({ apiKey: 'your-key' });

// Chat
const response = await client.chat({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello' }]
});
console.log(response.content);

// Agent
const result = await client.agent.run({
  agentId: 'maintenance-agent',
  inputText: 'Check HVAC status'
});
console.log(result.finalAnswer);
```

### cURL
```bash
# Chat
curl -X POST http://ai.dtlite.local/api/v1/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]}'

# Agent
curl -X POST http://ai.dtlite.local/api/v1/ai/agent/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "maintenance-agent", "input_text": "Check status"}'
```
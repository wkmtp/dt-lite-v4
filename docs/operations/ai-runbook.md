# DT-Lite AI Service — Operations Runbook

## Overview

The AI Service provides:
- **Agent Runtime**: Tool-calling agents with memory and planning
- **RAG Pipeline**: Hybrid retrieval with reranking
- **Workflow Orchestrator**: Low-code workflow execution with approval gates
- **Model Gateway**: Multi-provider routing with quota and cost tracking

## Common Failure Modes

### 1. Agent Not Responding

**Symptoms**: `/health` returns 503, pods in CrashLoopBackOff

**Diagnosis**:
```bash
kubectl logs -n dtlite deployment/dt-lite-ai --tail=100
kubectl describe pod -n dtlite -l app=dt-lite-ai
```

**Common Causes**:
- Database connection failure (check PostgreSQL)
- Redis unavailable (check Redis)
- Model provider timeout (check Model Gateway health)

**Resolution**:
1. Verify database connectivity: `psql $DATABASE_URL -c "SELECT 1"`
2. Check Redis: `redis-cli -u $REDIS_URL ping`
3. Restart pods: `kubectl rollout restart deployment/dt-lite-ai -n dtlite`

### 2. Quota Exceeded

**Symptoms**: API returns 429, tokens blocked

**Diagnosis**:
```bash
# Check quota usage
curl -H "Authorization: Bearer $TOKEN" \
  http://ai.dtlite.local/api/v1/ai/admin/quotas/$tenant_id/usage
```

**Resolution**:
1. Increase quota: `PUT /api/v1/ai/admin/quotas/{tenant_id}`
2. Wait for next billing period
3. Enable fallback model: Gateway auto-fallback to smaller model

### 3. RAG Retrieval Degraded

**Symptoms**: Low recall, high latency

**Diagnosis**:
```bash
# Check vector store health
curl http://ai.dtlite.local/health | jq '.providers.pgvector'
```

**Resolution**:
1. Rebuild embeddings: `POST /api/v1/ai/rag/index`
2. Adjust chunk size: Update `AI_RAG_CHUNK_SIZE` config
3. Check vector index: `SELECT * FROM pg_stat_user_indexes WHERE tablename = 'embeddings';`

### 4. Workflow Stuck

**Symptoms**: Workflow execution hangs, approval pending

**Diagnosis**:
```bash
# Check workflow executions
SELECT * FROM workflow_executions WHERE status = 'running';
SELECT * FROM workflow_approvals WHERE status = 'pending';
```

**Resolution**:
1. Timeout approval: Set `AI_ORCHESTRATOR_DEFAULT_TIMEOUT_SECONDS`
2. Cancel stuck workflow: `DELETE FROM workflow_executions WHERE id = '...';`
3. Resume from checkpoint: System auto-resumes on restart

## Scaling Procedures

### Horizontal Scaling
```bash
# Update replica count
kubectl scale deployment/dt-lite-ai -n dtlite --replicas=5

# Or use HPA (recommended)
kubectl autoscale deployment/dt-lite-ai -n dtlite --min=2 --max=10 --cpu-percent=60
```

### Vertical Scaling
```bash
# Update resource limits
kubectl edit deployment/dt-lite-ai -n dtlite
# Modify resources.requests and resources.limits
```

### Model Provider Scaling
```bash
# Add fallback provider
curl -X POST http://ai.dtlite.local/api/v1/ai/admin/models \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"provider": "ollama", "model": "llama3.2", "weight": 1}'
```

## Monitoring Alerts

### Critical Alerts
| Alert | Condition | Action |
|-------|-----------|--------|
| `AI_HighErrorRate` | error_rate > 5% for 5m | Check logs, restart pods |
| `AI_HighLatency` | p99 > 2s for 5m | Check model provider, scale up |
| `AI_QuotaExceeded` | daily_budget > 90% | Increase quota or optimize usage |
| `AI_CircuitBreakerOpen` | circuit_state = OPEN | Check provider health, fallback |

### Warning Alerts
| Alert | Condition | Action |
|-------|-----------|--------|
| `AI_LowMemory` | memory > 80% | Scale up or optimize |
| `AI_HighCost` | daily_cost > 80% budget | Review usage, optimize prompts |
| `AI_PendingApproval` | pending_approvals > 10 | Notify approvers |

## Disaster Recovery

### Backup
```bash
# Database backup
pg_dump -h postgres.dtlite.local -U dtlite dtlite_ai > backup_$(date +%Y%m%d).sql

# Config backup
kubectl get configmap ai-config -n dtlite -o yaml > ai-config-backup.yaml
```

### Restore
```bash
# Restore database
psql -h postgres.dtlite.local -U dtlite dtlite_ai < backup_YYYYMMDD.sql

# Restore config
kubectl apply -f ai-config-backup.yaml -n dtlite
```

### Rollback
```bash
# Helm rollback
helm rollback dt-lite-ai 1 -n dtlite-staging

# Kubernetes rollback
kubectl rollout undo deployment/dt-lite-ai -n dtlite
```

## Capacity Planning

| Metric | Current | Target | Max |
|--------|---------|--------|-----|
| Throughput | 100 req/s | 500 req/s | 1000 req/s |
| Concurrent Users | 50 | 200 | 500 |
| Token/Day | 2.3M | 10M | 50M |
| Cost/Day | $12.4 | $50 | $200 |
| Memory | 1Gi | 2Gi | 4Gi |
| CPU | 500m | 1000m | 2000m |

## Alert Handling SOP

### P1: Service Down
1. Check pod status: `kubectl get pods -n dtlite -l app=dt-lite-ai`
2. Check logs: `kubectl logs -n dtlite deployment/dt-lite-ai --tail=200`
3. Restart: `kubectl rollout restart deployment/dt-lite-ai -n dtlite`
4. If persistent: Check database/Redis connectivity

### P2: High Error Rate (>5%)
1. Check error patterns in Grafana
2. Review recent deployments: `helm history dt-lite-ai -n dtlite`
3. Rollback if needed: `helm rollback dt-lite-ai 1 -n dtlite`
4. Check model provider health: `curl http://ai.dtlite.local/health`

### P3: Performance Degradation
1. Check resource utilization: CPU, Memory, DB connections
2. Scale horizontally if needed: `kubectl scale deployment/dt-lite-ai -n dtlite --replicas=5`
3. Check for slow queries: `pg_stat_activity`
4. Review circuit breaker status

## Scaling Procedures

### Horizontal Scaling
```bash
# Update replica count
kubectl scale deployment/dt-lite-ai -n dtlite --replicas=5

# Or use HPA (recommended)
kubectl autoscale deployment/dt-lite-ai -n dtlite --min=2 --max=10 --cpu-percent=60
```

### Vertical Scaling
```bash
# Update resource limits
kubectl edit deployment/dt-lite-ai -n dtlite
# Modify resources.requests and resources.limits
```

### Model Provider Scaling
```bash
# Add fallback provider
curl -X POST http://ai.dtlite.local/api/v1/ai/admin/models \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"provider": "ollama", "model": "llama3.2", "weight": 1}'
```

## Disaster Recovery

### Backup
```bash
# Database backup
pg_dump -h postgres.dtlite.local -U dtlite dtlite_ai > backup_$(date +%Y%m%d).sql

# Config backup
kubectl get configmap ai-config -n dtlite -o yaml > ai-config-backup.yaml
```

### Restore
```bash
# Restore database
psql -h postgres.dtlite.local -U dtlite dtlite_ai < backup_YYYYMMDD.sql

# Restore config
kubectl apply -f ai-config-backup.yaml -n dtlite
```

### Rollback
```bash
# Helm rollback
helm rollback dt-lite-ai 1 -n dtlite-staging

# Kubernetes rollback
kubectl rollout undo deployment/dt-lite-ai -n dtlite
```

## Capacity Planning

| Metric | Current | Target | Max |
|--------|---------|--------|-----|
| Throughput | 4000 req/s | 5000 req/s | 10000 req/s |
| Concurrent Users | 100 | 500 | 1000 |
| Token/Day | 864M | 2B | 5B |
| Cost/Day | $50 | $200 | $500 |
| Memory | 1Gi | 2Gi | 4Gi |
| CPU | 500m | 1000m | 2000m |

## Contact

- **On-call**: #dtlite-oncall Slack channel
- **Escalation**: dtlite-leads@company.com
- **Documentation**: https://wiki.dtlite.local/ai-service

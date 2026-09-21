# DT-Lite AI Service — Capacity Planning

## Overview

This document provides capacity planning guidelines for the DT-Lite AI Service,
covering storage, compute, network, and cost estimates for different deployment scales.

## Throughput Sizing

### Small Scale (100 concurrent users)
- **Requests/sec**: 50
- **Tokens/sec**: 10,000
- **Daily tokens**: 864M (24h)
- **Daily cost**: ~$50
- **Replicas**: 2
- **CPU per replica**: 500m
- **Memory per replica**: 1Gi

### Medium Scale (1,000 concurrent users)
- **Requests/sec**: 500
- **Tokens/sec**: 100,000
- **Daily tokens**: 8.64B (24h)
- **Daily cost**: ~$500
- **Replicas**: 5
- **CPU per replica**: 1000m
- **Memory per replica**: 2Gi

### Large Scale (10,000 concurrent users)
- **Requests/sec**: 5,000
- **Tokens/sec**: 1,000,000
- **Daily tokens**: 86.4B (24h)
- **Daily cost**: ~$5,000
- **Replicas**: 10
- **CPU per replica**: 2000m
- **Memory per replica**: 4Gi

## Storage Requirements

### Database (PostgreSQL + pgvector)
| Scale | Initial | Monthly Growth | Total (1 yr) |
|-------|---------|----------------|--------------|
| Small | 10 GiB | 5 GiB | 70 GiB |
| Medium | 50 GiB | 25 GiB | 350 GiB |
| Large | 200 GiB | 100 GiB | 1.4 TiB |

### Vector Store (pgvector)
| Scale | Vectors | Dimensions | Storage |
|-------|---------|------------|---------|
| Small | 1M | 1536 | 6 GiB |
| Medium | 10M | 1536 | 60 GiB |
| Large | 100M | 1536 | 600 GiB |

### Cache (Redis)
| Scale | Max Memory | Eviction Policy |
|-------|------------|-----------------|
| Small | 1 GiB | allkeys-lru |
| Medium | 4 GiB | allkeys-lru |
| Large | 16 GiB | allkeys-lru |

## Network Requirements

### Inbound
| Scale | Bandwidth | P99 Latency |
|-------|-----------|-------------|
| Small | 100 Mbps | < 200ms |
| Medium | 1 Gbps | < 500ms |
| Large | 10 Gbps | < 1s |

### Outbound (to LLM providers)
| Scale | Bandwidth | Concurrent Connections |
|-------|-----------|----------------------|
| Small | 50 Mbps | 100 |
| Medium | 500 Mbps | 1,000 |
| Large | 5 Gbps | 10,000 |

## Cost Estimates (AWS)

### Small Scale (Monthly)
| Component | Cost |
|-----------|------|
| EC2 (2x t3.medium) | $150 |
| RDS (db.r5.large) | $300 |
| ElastiCache (cache.r6g.large) | $100 |
| Data Transfer | $50 |
| **Total Infrastructure** | **$600** |
| LLM API Costs | $50 |
| **Total** | **$650** |

### Medium Scale (Monthly)
| Component | Cost |
|-----------|------|
| EC2 (5x t3.large) | $600 |
| RDS (db.r5.xlarge) | $600 |
| ElastiCache (cache.r6g.xlarge) | $200 |
| Data Transfer | $200 |
| **Total Infrastructure** | **$1,600** |
| LLM API Costs | $500 |
| **Total** | **$2,100** |

### Large Scale (Monthly)
| Component | Cost |
|-----------|------|
| EC2 (10x c5.2xlarge) | $2,400 |
| RDS (db.r5.2xlarge) | $1,200 |
| ElastiCache (cache.r6g.2xlarge) | $400 |
| Data Transfer | $800 |
| **Total Infrastructure** | **$4,800** |
| LLM API Costs | $5,000 |
| **Total** | **$9,800** |

## Scaling Triggers

### Horizontal Scaling
| Metric | Trigger Scale Up | Trigger Scale Down |
|--------|------------------|-------------------|
| CPU Utilization | > 70% for 5m | < 30% for 10m |
| Memory Utilization | > 80% for 5m | < 40% for 10m |
| Request Queue Depth | > 100 | < 10 |
| P99 Latency | > 1s | < 200ms |

### Vertical Scaling
| Metric | Action |
|--------|--------|
| CPU > 90% for 15m | Upgrade instance type |
| Memory > 90% for 15m | Upgrade instance type |
| Disk > 80% | Expand volume |

## Optimization Recommendations

### Cost Optimization
1. Use fallback models (gpt-4o → gpt-4o-mini → gpt-3.5-turbo)
2. Implement request caching for repeated queries
3. Use batch processing for non-real-time tasks
4. Set strict token budgets per tenant

### Performance Optimization
1. Enable connection pooling (PgBouncer)
2. Use vector index optimization (IVFFlat)
3. Implement response streaming for long completions
4. Cache frequent RAG retrievals

### Reliability Optimization
1. Multi-AZ deployment
2. Auto-failover to backup providers
3. Circuit breaker for provider failures
4. Rate limiting per tenant

## Monitoring Dashboard

Key metrics to track:
- Requests/sec by provider
- Token usage by tenant
- Cost accumulation by tenant
- Error rate by endpoint
- P99 latency by endpoint
- Quota utilization by tenant
- Circuit breaker states

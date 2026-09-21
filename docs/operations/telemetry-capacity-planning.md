# Telemetry Pipeline Capacity Planning

## 1. Throughput Sizing

| Target Throughput | Pods | CPU (total) | Memory (total) | PostgreSQL | Network |
|-------------------|------|-------------|----------------|------------|---------|
| 10k pts/s | 1 | 1 CPU | 2 GB | 1 vCPU, 4GB | 100 Mbps |
| 100k pts/s | 2 | 2 CPU | 4 GB | 2 vCPU, 8GB | 500 Mbps |
| 500k pts/s | 10 | 10 CPU | 20 GB | 4 vCPU, 16GB | 2.5 Gbps |
| 1M pts/s | 20 | 20 CPU | 40 GB | 8 vCPU, 32GB | 5 Gbps |

**Assumptions:**
- Average point size: 200 bytes (JSON)
- Batch size: 10k points
- Flush interval: 10ms

---

## 2. Storage Sizing

### Raw Data (telemetry_points)

| Retention | 100k pts/s | 500k pts/s | 1M pts/s |
|-----------|------------|------------|----------|
| 7 days | 117 GB | 585 GB | 1.17 TB |
| 30 days | 500 GB | 2.5 TB | 5 TB |
| 90 days | 1.5 TB | 7.5 TB | 15 TB |

### Aggregated Data

| Level | Retention | Compression Ratio | 100k pts/s |
|-------|-----------|-------------------|------------|
| 1s | 7 days | 60x | 2 GB |
| 1m | 90 days | 1440x | 35 GB |
| 1h | 365 days | 8640x | 60 GB |

**Total Storage (100k pts/s, 30-day raw):** ~600 GB (raw) + 100 GB (agg) = 700 GB

---

## 3. Database Sizing

### PostgreSQL + TimescaleDB

| Metric | 100k pts/s | 500k pts/s |
|--------|------------|------------|
| WAL generation | 20 MB/s | 100 MB/s |
| Checkpoint frequency | Every 30s | Every 10s |
| Connection pool | 50 | 200 |
| Buffer cache | 4 GB | 16 GB |
| Disk IOPS | 10k | 50k |

**Recommended:** AWS RDS PostgreSQL `db.r6g.2xlarge` or equivalent

---

## 4. Network Bandwidth

| Protocol | Points/s | Avg Size | Bandwidth |
|----------|----------|----------|-----------|
| BACnet | 40k | 150 B | 6 Mbps |
| Modbus | 35k | 120 B | 4.2 Mbps |
| MQTT | 15k | 200 B | 2.4 Mbps |
| OPC-UA | 10k | 180 B | 1.44 Mbps |
| **Total** | **100k** | **162 B** | **~14 Mbps** |

**With 10x headroom:** 140 Mbps sustained per pod

---

## 5. Scaling Factors

### When to Scale Up (vertical)
- P99 latency > 200ms at current capacity
- Memory usage > 80%
- CPU usage > 70% sustained

### When to Scale Out (horizontal)
- Throughput > 80% of current pod capacity
- Single partition hotspot detected
- Error rate increasing with load

### Auto-Scaling Configuration (HPA)
```yaml
minReplicas: 2
maxReplicas: 10
targetCPUUtilization: 70%
targetMemoryUtilization: 80%
scaleUpStabilization: 60s
scaleDownStabilization: 300s
```

---

## 6. Cost Estimate (AWS us-east-1)

| Component | 100k pts/s | 500k pts/s |
|-----------|------------|------------|
| ECS/Fargate (2-10 pods) | $350/mo | $1,500/mo |
| RDS PostgreSQL | $400/mo | $1,200/mo |
| ElastiCache Redis | $100/mo | $200/mo |
| CloudWatch + ALB | $50/mo | $150/mo |
| **Total** | **~$900/mo** | **~$3,050/mo** |

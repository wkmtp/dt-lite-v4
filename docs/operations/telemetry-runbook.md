# Telemetry Pipeline Operations Runbook

## 1. Service Overview

The Telemetry Pipeline service handles high-throughput ingestion, quality scoring,
aggregation, and querying of time-series data from protocol adapters.

**Key Components:**
- **S1 Ingestion**: BatchWriter + PartitionRouter (100k+ pts/s)
- **S2 Aggregation**: ContinuousAggregator (1s/1m/1h/1d rollups)
- **S3 Quality**: QualityEngine (5-dimension scoring)
- **S4 Query**: TelemetryQuery DSL with push-down aggregation

**Dependencies:**
- PostgreSQL + TimescaleDB (time-series storage)
- Redis (backpressure state, circuit breaker)
- Gateway (JWT auth)

---

## 2. Common Failure Modes

### 2.1 BatchWriter Backpressure Triggered

**Symptoms:** 429 responses, queue depth increasing
**Root Cause:** Consumer lag (DB write slow or partition hotspot)
**Recovery:**
1. Check `telemetry_batch_queue_depth` metric
2. Verify PostgreSQL write latency (check `pg_stat_statements`)
3. Scale horizontally: increase partition count
4. Temporarily increase `BATCH_FLUSH_MS` to reduce pressure

### 2.2 Circuit Breaker Open on Adapter

**Symptoms:** Adapter health = false, connection retries exhausted
**Root Cause:** Protocol endpoint unreachable or responding with errors
**Recovery:**
1. Check adapter logs: `grep "CircuitBreaker" /var/log/dtlite/*.log`
2. Verify endpoint connectivity: `telnet <host> <port>`
3. Wait for HALF_OPEN transition (configurable, default 30s)
4. If persistent: disable adapter in registry, investigate

### 2.3 Quality Score Degradation

**Symptoms:** High BAD quality ratio (>5%)
**Root Cause:** Sensor faults, network jitter, or data corruption
**Recovery:**
1. Check `telemetry_quality_total` by quality dimension
2. Review quality rules: `GET /api/v1/telemetry/config`
3. Adjust thresholds if false positives
4. Investigate source adapter for hardware issues

### 2.4 Data Loss During Flush

**Symptoms:** `telemetry_points_ingested_total` < expected
**Root Cause:** BatchWriteResult failed=0 not set correctly, or partition unavailable
**Recovery:**
1. Check `telemetry_ingestion_errors_total` metric
2. Review BatchWriter logs for retry failures
3. Verify PostgreSQL write path (disk I/O, connection pool)
4. Enable dead-letter queue for retry

---

## 3. Scaling Procedures

### Horizontal Scaling (Pods)
```bash
# Current replicas
kubectl get hpa telemetry -n dtlite

# Manual scale (if HPA not sufficient)
kubectl scale deployment telemetry -n dtlite --replicas=5

# Verify health
kubectl get pods -n dtlite -l app=telemetry
```

### Database Scaling
```bash
# Check TimescaleDB hypertable size
psql -d dtlite_telemetry -c "SELECT hypertable_size('telemetry_points');"

# Add more partitions if hotspot detected
# (handled automatically by PartitionRouter consistent hashing)
```

### Backpressure Tuning
```bash
# Update ConfigMap
kubectl edit configmap telemetry-config -n dtlite

# Fields:
# BATCH_MAX_SIZE: 10000 (default)
# BATCH_FLUSH_MS: 10 (default)
# MAX_PENDING_BATCHES: 10 (default)
```

---

## 4. Monitoring Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Low Throughput | < 1000 pts/s for 5m | WARNING | Check adapter health |
| High P99 Latency | > 500ms for 5m | CRITICAL | Check DB write latency |
| High Error Rate | > 1% for 5m | CRITICAL | Check partition health |
| Queue Depth High | > 50 pending batches | WARNING | Scale consumers |
| BAD Quality High | > 5% ratio | WARNING | Review quality rules |
| Disk Usage High | > 80% | CRITICAL | Extend retention or add storage |
| Adapter DOWN | health=0 | CRITICAL | Check protocol endpoint |

---

## 5. Disaster Recovery

### 5.1 Full Restore from Backup
```bash
# Restore TimescaleDB
pg_restore -d dtlite_telemetry /backups/dtlite_telemetry_$(date -I).dump

# Restore Redis (if used for caching)
redis-cli -h redis RESTORE ...

# Verify data integrity
psql -d dtlite_telemetry -c "SELECT count(*) FROM telemetry_points WHERE timestamp > NOW() - INTERVAL '1h';"
```

### 5.2 Graceful Shutdown
```bash
# Signal graceful shutdown (flushes pending batches)
kubectl delete pod telemetry-xxx -n dtlite --force --grace-period=30

# Verify batch flush completed
# Check metrics: telemetry_batch_flush_total should increment
```

---

## 6. Capacity Planning

See `docs/operations/telemetry-capacity-planning.md` for detailed capacity tables.

**Quick Reference:**
- 100k pts/s sustained → 2 pods (4 CPU, 8GB RAM)
- 1M pts/s sustained → 10 pods + read replica
- 30-day raw retention → 500GB SSD per hypertable

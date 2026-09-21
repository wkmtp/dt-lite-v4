# Edge Node Capacity Planning Guide

**Version:** 4.18.0

---

## 1. Throughput Sizing

### Formula
```
Required Throughput (pts/s) = devices × readings_per_device × sampling_rate
```

### Examples
| Scenario | Devices | Rate | Throughput | Storage/Day |
|----------|---------|------|-----------|-------------|
| Small factory | 10 | 1Hz | 10 pts/s | 864 KB |
| Medium plant | 100 | 10Hz | 1k pts/s | 864 MB |
| Large campus | 1000 | 10Hz | 10k pts/s | 8.6 GB |
| Enterprise | 10000 | 1Hz | 10k pts/s | 864 GB |

---

## 2. Storage Sizing

### SQLite Performance
- Write: ~10k-100k INSERT/s (single row)
- Batch write: ~100k-500k INSERT/s (executemany)
- Recommended batch size: 100-1000 rows

### Retention Policy
- Default: 7 days (configurable)
- Compression: zstandard/lz4 for archived data
- Garbage collection: 7-day max retention (see `task18-crdt-gc.md`)

### Disk Requirements
```
Disk = (throughput × 3600 × 24 × retention_days × avg_point_size) / compression_ratio
```

Example: 1k pts/s, 7 days, 200 bytes/point, 2x compression
```
= 1000 × 86400 × 200 × 7 / 2
= 6.048 GB
```

---

## 3. Memory Sizing

### Components
| Component | Base | Per-Device | Notes |
|-----------|------|------------|-------|
| SQLite cache | 50 MB | - | WAL mode |
| CRDT state | 10 MB | 1 KB | LWW + ORSet |
| Sync buffer | 5 MB | 100 B | Pending uploads |
| Inference models | 50 MB | 20 MB | ONNX models |
| Adapter buffers | 10 MB | 500 B | Offline buffering |

### Total Memory Formula
```
Memory (MB) = base + devices × per_device + models × model_count
```

Example: 100 devices, 2 models
```
= 125 + 100 × 0.1 + 2 × 20
= 165 MB
```

---

## 4. Network Sizing

### Upload Bandwidth
```
Upload bandwidth (bps) = throughput × avg_point_size × 8
```
Example: 1k pts/s, 200 bytes/point
```
= 1000 × 200 × 8 = 1.6 Mbps
```

### Download Bandwidth
- Commands: ~1 KB/device/hour
- Config updates: ~10 KB/node/event

---

## 5. AWS Cost Estimates

### t3.medium (2 vCPU, 4GB RAM)
- Compute: ~$30/month
- EBS 100GB: ~$8/month
- Total: ~$38/month per edge node

### t3.large (2 vCPU, 8GB RAM)
- Compute: ~$60/month
- EBS 200GB: ~$16/month
- Total: ~$76/month per edge node

### Cost per 1000 nodes (t3.medium)
- Compute: $30,000/month
- Storage: $8,000/month
- Total: ~$38,000/month

---

## 6. Scaling Triggers

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU usage | > 60% | > 80% | Scale horizontally |
| Memory usage | > 70% | > 90% | Increase RAM / GC |
| Disk usage | > 75% | > 90% | Expand storage / GC |
| Network latency | > 100ms | > 500ms | Check network / CDN |
| Sync queue depth | > 1000 | > 5000 | Increase sync frequency |

---

## 7. Optimization Recommendations

1. **Batch writes:** Use `executemany` for 100+ points
2. **Index wisely:** Only index `tenant_id` and `timestamp`
3. **Compress archives:** Use zstandard for cold data
4. **GC regularly:** Run CRDT GC every sync cycle
5. **Monitor WAL:** SQLite WAL size should stay < 100MB

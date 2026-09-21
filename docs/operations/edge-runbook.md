# Edge Node Operations Runbook

**Version:** 4.18.0  
**Service:** DT-Lite Edge Runtime  
**Owner:** DT-Lite Platform Team

---

## 1. Service Overview

The Edge Node provides offline-first telemetry collection, local inference, and bidirectional sync with the cloud platform. It runs on resource-constrained edge devices.

### Architecture
- **Core:** EdgeNode lifecycle management (provision, heartbeat, health)
- **Storage:** SQLite-based local persistence (metadata + telemetry)
- **Sync:** HLC + CRDT-based bidirectional sync with cloud
- **Compute:** ONNX Runtime inference engine
- **Adapter:** Protocol-agnostic edge adapters (Modbus, BACnet, MQTT, OPC-UA)
- **OTA:** Secure firmware updates with Ed25519 signature verification

### Key Ports
- HTTP API: `8080`
- Metrics: `9090`

---

## 2. Failure Modes & Mitigation

### 2.1 Process Crash
**Symptoms:** Edge node unresponsive, heartbeat timeout
**Mitigation:**
1. systemd auto-restart: `systemctl restart dtlite-edge`
2. Data is safe in SQLite WAL (write-ahead logging)
3. Re-provision if node_id lost

### 2.2 Disk Full
**Symptoms:** Write errors, `sqlite3.OperationalError: database or disk is full`
**Mitigation:**
1. Clear old telemetry: `DELETE FROM telemetry_points WHERE timestamp < ?`
2. Adjust retention policy via API
3. Scale disk capacity

### 2.3 Network Partition
**Symptoms:** Sync engine disconnected, pending uploads growing
**Mitigation:**
1. Local writes continue normally (SQLite)
2. Pending queue auto-flush on reconnect
3. HLC ensures causal ordering

### 2.4 OTA Update Failure
**Symptoms:** New version crashes on startup
**Mitigation:**
1. A/B partition rollback automatic
2. Previous version restored from partition B
3. Health check gate prevents bad rollout

### 2.5 CRDT State Explosion
**Symptoms:** Memory usage > 50MB
**Mitigation:**
1. Trigger manual GC: `POST /api/v1/edge/gc`
2. Review CRDT GC strategy (`docs/architecture/task18-crdt-gc.md`)
3. Reduce sync window if needed

---

## 3. Scaling Procedures

### Horizontal Scaling
- Edge nodes are stateless (local SQLite is per-node)
- Scale by adding more edge nodes
- Cloud-side sync handles merge

### Vertical Scaling
- Increase SQLite cache size
- Adjust `buffer_size` in adapter config
- Monitor `resource_quota` API

---

## 4. Monitoring Alerts

### P1 (Critical)
- Node heartbeat timeout > 5 min
- Disk usage > 90%
- OTA update failure

### P2 (Warning)
- Pending sync queue > 1000
- CRDT memory > 30MB
- Error rate > 1%

### P3 (Info)
- New node provisioned
- OTA canary stage change
- GC cycle completed

---

## 5. Disaster Recovery

### Backup
```bash
# Backup SQLite database
cp /var/lib/dtlite-edge/node.db /backup/dtlite-edge-$(date +%Y%m%d).db
# Backup configuration
cp /etc/dtlite-edge/config.yaml /backup/
```

### Restore
```bash
# Restore database
systemctl stop dtlite-edge
cp /backup/dtlite-edge-YYYYMMDD.db /var/lib/dtlite-edge/node.db
systemctl start dtlite-edge
# Verify data integrity
curl -s http://localhost:8080/health | jq .
```

### Rollback
```bash
# Rollback to previous version
systemctl restart dtlite-edge@prev
```

---

## 6. Capacity Planning

| Scenario | Throughput | Storage (30d) | Memory |
|----------|-----------|---------------|--------|
| 10 devices | 100 pts/s | 1 GB | 256 MB |
| 100 devices | 1k pts/s | 10 GB | 512 MB |
| 1000 devices | 10k pts/s | 100 GB | 1 GB |

See `docs/operations/edge-capacity-planning.md` for detailed sizing.

---

## 7. Contact

- **On-call:** DT-Lite Platform Team
- **Escalation:** dt-lite-oncall@company.com
- **Documentation:** `docs/operations/`

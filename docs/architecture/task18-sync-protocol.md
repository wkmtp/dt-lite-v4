# DT-Lite Edge — Sync Protocol Specification

**Version**: 1.0  
**Status**: CP1 Freeze  
**Date**: 2026-09-08

---

## 1. Overview

The Sync Protocol enables bidirectional data synchronization between Edge Nodes and Cloud Center using **WebSocket + Protobuf** as the transport layer.

### Design Principles

- **Causal Consistency**: Hybrid Logical Clock (HLC) for total ordering
- **Conflict Freedom**: CRDT-based data structures (LWW-Register, OR-Set, RGA)
- **Backpressure**: Token bucket rate limiting + priority queue
- **Resilience**: Exponential backoff retry + checkpoint persistence

---

## 2. Connection Lifecycle

```
┌──────────┐                              ┌──────────┐
│ Edge     │                              │ Cloud    │
│ Node     │                              │ Center   │
└────┬─────┘                              └────┬─────┘
     │                                         │
     │  1. WebSocket Upgrade                   │
     │  GET /api/v1/sync/ws?token=xxx          │
     │────────────────────────────────────────>│
     │                                         │
     │  2. 101 Switching Protocols             │
     │<────────────────────────────────────────│
     │                                         │
     │  3. Hello (NodeID, HLC, Capabilities)   │
     │────────────────────────────────────────>│
     │                                         │
     │  4. HelloAck (Accepted, ConfigVersion)  │
     │<────────────────────────────────────────│
     │                                         │
     │         ──── Sync Session ────          │
     │                                         │
     │  5. Heartbeat (every 30s)               │
     │<────────────────────────────────────────│
     │                                         │
     │  N. Close (Graceful / Error)            │
     │────────────────────────────────────────>│
```

---

## 3. Message Flow

### 3.1 Telemetry Upload (Edge → Cloud)

```
Edge                                    Cloud
 │                                         │
 │  TelemetryBatch {                      │
 │    points: [...],                      │
 │    tenant_id: "t1",                    │
 │    sync_hlc: HLC(1000, 5, "edge-1")    │
 │  }                                     │
 │────────────────────────────────────────>│
 │                                         │
 │  Ack { seq: 100, accepted: 50 }         │
 │<────────────────────────────────────────│
 │                                         │
 │  (If rejected: queue for retry)         │
```

### 3.2 Command Download (Cloud → Edge)

```
Edge                                    Cloud
 │                                         │
 │  ConfigSync {                           │
 │    node_id: "edge-1",                  │
 │    config_version: "2.0",              │
 │    sync_hlc: HLC(999, 3, "cloud")      │
 │  }                                     │
 │────────────────────────────────────────>│
 │                                         │
 │  ConfigDelta {                          │
 │    deltas: [{key: "rule_x",            │
 │              value: {...}}],            │
 │    sync_hlc: HLC(1001, 1, "cloud")     │
 │  }                                     │
 │<────────────────────────────────────────│
 │                                         │
 │  CommandBatch {                         │
 │    commands: [...],                    │
 │    sync_hlc: HLC(1002, 2, "cloud")     │
 │  }                                     │
 │<────────────────────────────────────────│
```

### 3.3 Conflict Resolution

```
Edge                                    Cloud
 │                                         │
 │  ConflictReport {                       │
 │    conflict_id: "c1",                  │
 │    key: "asset.temp",                  │
 │    edge_value: 25.5,                   │
 │    edge_hlc: HLC(998, 10, "edge-1"),   │
 │    strategy: "lww"                     │
 │  }                                     │
 │────────────────────────────────────────>│
 │                                         │
 │  ConflictResolve {                      │
 │    conflict_id: "c1",                  │
 │    resolved_value: 25.5,               │
 │    resolved_by: "edge"                 │
 │  }                                     │
 │<────────────────────────────────────────│
```

---

## 4. HLC (Hybrid Logical Clock)

### 4.1 Structure

```protobuf
message HLCTimestamp {
  int64 physical_ts = 1;      // Nanoseconds since epoch
  int32 logical_counter = 2;  // Monotonically increasing
  string node_id = 3;         // Originating node identifier
}
```

### 4.2 Operations

| Operation | Description |
|-----------|-------------|
| `now(node_id)` | Create new HLC from current physical time |
| `increment()` | Increment logical counter |
| `merge(other)` | Take max of physical + max of logical + 1 |
| `is_after(other)` | Check causal ordering |

### 4.3 Usage in Sync

- Each message carries its source HLC
- Recipient merges incoming HLC with local clock
- Conflict detection: compare HLC of cloud vs edge values

---

## 5. CRDT Data Structures

### 5.1 LWW-Register (Last-Writer-Wins)

For scalar values (config, single property):
```python
if edge_hlc.is_after(cloud_hlc):
    return edge_value
return cloud_value
```

### 5.2 OR-Set (Observed-Remove Set)

For collections (adapter list, subscribed topics):
- Add with unique tag
- Remove observed tags
- Merge: union of all elements with non-empty tags

### 5.3 RGA (Replicated Growable Array)

For ordered lists (rule execution history):
- Total ordering via HLC
- Insert with predecessor reference
- Delete by marking tombstones

---

## 6. Backpressure & Rate Limiting

### 6.1 Token Bucket

```
Rate: 1000 tokens/sec
Capacity: 2000 tokens
Each message costs: N tokens (based on size)
```

### 6.2 Priority Queue

| Priority | Message Type |
|----------|--------------|
| P0 (Critical) | Commands, OTA updates |
| P1 (High) | Config sync, Heartbeat ack |
| P2 (Medium) | Telemetry batches |
| P3 (Low) | Logs, diagnostics |

### 6.3 Exponential Backoff

```
Retry attempts: 5
Initial delay: 100ms
Max delay: 30s
Jitter: ±20%
```

---

## 7. Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | ERR_NONE | Success |
| 1 | ERR_INVALID_TOKEN | Authentication failed |
| 2 | ERR_PROVISION_FAILED | Node provisioning error |
| 3 | ERR_SYNC_CONFLICT | Unresolvable conflict |
| 4 | ERR_OTA_VERIFY_FAILED | Signature/checksum mismatch |
| 5 | ERR_QUOTA_EXCEEDED | Resource quota exceeded |
| 6 | ERR_INVALID_MESSAGE | Protocol violation |
| 99 | ERR_INTERNAL | Unexpected error |

---

## 8. Checkpoint & Resume

### 8.1 Checkpoint Storage

```
Location: /var/lib/dtlite-edge/sync/checkpoints/
Format: JSON
Content: {
  "node_id": "edge-1",
  "cloud_hlc": {...},
  "pending_uploads": [...],
  "last_sync_at": "2026-09-08T10:00:00Z"
}
```

### 8.2 Resume Procedure

1. On reconnect, send last known HLC
2. Cloud computes delta since that HLC
3. Edge applies deltas in causal order
4. Checkpoint updated after each batch

---

## 9. Security

| Layer | Mechanism |
|-------|-----------|
| Transport | TLS 1.3 (required for production) |
| Authentication | JWT bearer token (provisioning) |
| Integrity | Ed25519 signatures on OTA packages |
| Confidentiality | WebSocket frame encryption |

---

*Specification frozen at CP1 — 2026-09-08*

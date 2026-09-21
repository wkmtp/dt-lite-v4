# CRDT Garbage Collection Strategy

**Version:** 1.0  
**Date:** 2026-09-08  
**Status:** Approved  

---

## 1. Overview

CRDT state on edge nodes accumulates over time. Without garbage collection (GC), memory and storage grow unbounded. This document defines a three-layer GC strategy: **window GC**, **state compression**, and **7-day maximum retention**.

## 2. GC Layers

### 2.1 Layer 1 — Window GC (HLC-based)

- **Principle:** Only keep CRDT state for events within the causal window `[HLC_min, HLC_now]`.
- **Implementation:**
  - Each CRDT (LWWRegister, ORSet) tracks its minimum HLC (`hlc_min`).
  - On every sync cycle, the edge node computes `HLC_min = min(all_received_hlcs)`.
  - Any state element whose tag/HLC is before `HLC_min` is safe to discard (the cloud has a newer version).
- **Trigger:** Every sync heartbeat (default 30s).

### 2.2 Layer 2 — State Compression

- **LWWRegister:** Keep only the latest `(value, timestamp)` pair. Old values are discarded after merge.
- **ORSet:**
  - Elements with all tags GC'd (i.e., no live tag remains) are removed.
  - Use a **tombstone queue**: when an element is removed, its tag is recorded as a tombstone. Tombstones older than `max_retention` are purged.
- **RGA (Replicated-Growable-Array):** Not yet implemented; planned for Task 19.

### 2.3 Layer 3 — Maximum Retention (7 days)

- **Hard limit:** No CRDT state is kept longer than 7 days from creation.
- **Implementation:**
  - Each CRDT entry stores `created_at: HLC`.
  - GC runs every hour: remove all entries where `now() - created_at > 7 days`.
- **Rationale:** Edge nodes are expected to sync at least once per day. After 7 days, the cloud is guaranteed to have the authoritative state.

## 3. GC Algorithm Pseudocode

```
def run_gc(crdt_state: dict[str, CRDT], now: HLCTimestamp):
    # Layer 1: Window GC
    hlc_min = compute_hlc_min(crdt_state)
    for key, crdt in crdt_state.items():
        crdt.gc_before(hlc_min)

    # Layer 2: State Compression
    for key, crdt in crdt_state.items():
        crdt.compress()

    # Layer 3: Max retention
    cutoff = now - timedelta(days=7)
    for key, crdt in list(crdt_state.items()):
        if crdt.created_at < cutoff:
            del crdt_state[key]
```

## 4. Monitoring

- **GC metrics:**
  - `edge_crdt_gc_entries_purged` — count of entries purged per GC cycle
  - `edge_crdt_memory_bytes` — current CRDT state memory usage
  - `edge_crdt_retention_days` — actual max retention in days (should be ≤ 7)
- **Alert threshold:** If `edge_crdt_memory_bytes > 50MB`, trigger warning.

## 5. Compatibility with Sync Protocol

- GC is **local-only**: the edge node decides what to purge without notifying the cloud.
- The cloud maintains its own CRDT state and performs independent GC.
- After GC, the edge node sends a **sync handshake** with its current HLC to the cloud. The cloud uses this to determine what delta to send back.

## 6. Future Work

- [ ] Implement RGA CRDT with GC support
- [ ] Add GC as a Celery background task (for cloud-side)
- [ ] Integrate with retention policy from Task 16 (Telemetry)

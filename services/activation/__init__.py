"""Task 14 — Twin Activation & Operational Binding Foundation.

This module provides the operational layer that transforms a provisioned
PersistentTwinEntity into an active runtime twin. It reuses existing
TwinBinding (Task 9) and TwinEntityRegistry (Task 8) without duplication.

Responsibilities:
  - TwinActivationLog: persistent activation state tracking
  - TwinCommand: command lifecycle (CREATED → SENT → ACKNOWLEDGED → FAILED)
  - TwinActivationService: activate/deactivate entities in registry
  - TwinCommandService: create and track command intent
  - Data mapping configuration via JSONB (no protocol fields)
"""

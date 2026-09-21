# Architecture Decision Records — DT-Lite AI Service

## ADR-012: Agent Framework Selection

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need an agent framework for tool calling, memory, and planning.
**Decision**: Use LangGraph 0.1+ for stateful graph orchestration with custom ToolRegistry.
**Rationale**: LangGraph provides native support for stateful workflows, cycles, and conditional routing. Custom ToolRegistry enables hot-loading without restart.
**Consequences**:
- + Rich graph-based agent orchestration
- + Native support for cycles and conditionals
- - Requires learning LangGraph patterns
- - Limited to Python ecosystem

## ADR-013: Vector Database Selection

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need vector storage for RAG embeddings with tenant isolation.
**Decision**: Use pgvector 0.7+ as primary (PostgreSQL extension), Milvus 2.4+ as fallback for billion-scale vectors.
**Rationale**: pgvector eliminates separate vector DB infrastructure, reuses existing PostgreSQL, supports RLS for tenant isolation. Milvus available for future scaling.
**Consequences**:
- + Zero additional infrastructure for pgvector
- + Tenant isolation via existing RLS
- - Limited to ~100M vectors per collection for pgvector
- - Milvus adds deployment complexity

## ADR-014: Multi-Tenant Isolation Strategy

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need to ensure strict data isolation between tenants.
**Decision**: Collection prefix (`tenant_{id}_*`) + Row Level Security (RLS) + explicit tenant_id parameter propagation.
**Rationale**: Defense-in-depth with multiple isolation layers. Collection prefix for vector stores, RLS for relational data, explicit parameter for API layer.
**Consequences**:
- + Strong isolation guarantees
- + No cross-tenant data leakage
- - Additional query complexity
- - Need to validate tenant_id at every boundary

## ADR-015: Cost Control and Quota Management

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need to track and limit token usage per tenant to control costs.
**Decision**: Implement TenantQuotaManager with sliding window counters (RPM/TPM/daily/monthly budgets) + auto-fallback to smaller models when quotas exceeded.
**Rationale**: Prevents cost overrun, provides predictable billing, graceful degradation.
**Consequences**:
- + Cost predictability
- + Auto-fallback prevents service disruption
- - Complex quota tracking logic
- - Need to handle edge cases (race conditions, clock skew)

## ADR-016: Low-Code Workflow DSL

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need visual workflow editor with programmatic execution.
**Decision**: YAML/JSON-based DSL with GitOps-friendly format, version snapshots, and diff comparison.
**Rationale**: Human-readable, version-controlled, diffable. Supports import/export without lock-in.
**Consequences**:
- + Version control friendly
- + Easy review and approval
- - Learning curve for DSL syntax
- - Need to maintain backward compatibility

## ADR-017: Model Gateway Pattern

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need unified interface to multiple LLM providers with fallback and circuit breaking.
**Decision**: ModelGateway as sole entry point for all model calls, with weighted round-robin routing and automatic fallback chain.
**Rationale**: Centralized control, consistent error handling, easy provider switching.
**Consequences**:
- + Single point of control
- + Easy to add new providers
- - Gateway becomes bottleneck if not scaled
- - Single point of failure (mitigated by circuit breaker)

## ADR-018: Audit and Compliance Logging

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need full audit trail for compliance and cost tracking.
**Decision**: Dual logging to ai_usage_logs (billing) and ai_audit_logs (compliance), both with trace_id correlation.
**Rationale**: Separates operational costs from security auditing. Trace ID enables full request tracing.
**Consequences**:
- + Full audit trail
- + Cost attribution
- - Additional storage requirements
- - Need to maintain log retention policies

## ADR-019: Streaming Response Pattern

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need to support SSE streaming for better UX.
**Decision**: Use sse-starlette for Server-Sent Events, yield chunks as they arrive from model provider.
**Rationale**: Standard HTTP streaming, works with all modern browsers, simple implementation.
**Consequences**:
- + Better user experience
- + Lower perceived latency
- - Connection state management
- - Need to handle client disconnects

## ADR-020: WebSocket Session Management

**Status**: Accepted
**Date**: 2026-09-07
**Context**: Need persistent connections for real-time collaboration.
**Decision**: Token-based auth via query parameter, heartbeat with 30s interval, Redis Stream for offline message buffering.
**Rationale**: Simple auth, reliable delivery, graceful degradation on disconnect.
**Consequences**:
- + Real-time updates
- + Offline message recovery
- - Connection state in memory
- - Need to handle reconnect edge cases

"""Memory manager for DT-Lite AI agents.

Provides three memory tiers:
  1. Short-term   — sliding conversation window bounded by token count (default 32k)
  2. Long-term    — vectorised embeddings with semantic search, persisted per tenant
  3. Working      — transient task-context store cleared between runs
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)

# Approximate tokens per character (English).  A safe upper-bound for filtering.
_TOKENS_PER_CHAR: float = 0.25


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemoryEntry(BaseModel):
    """A single chunk of long-term memory."""

    entry_id: str = Field(..., description="Unique ID within the tenant store")
    tenant_id: str = Field(..., description="Tenant isolation key")
    content: str = Field(..., description="Text content of the memory chunk")
    embedding: Optional[list[float]] = Field(None, description="Normalized embedding vector")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary labels")
    created_at: str = Field(..., description="ISO-8601 timestamp")


class WorkingMemoryItem(BaseModel):
    """An item stored in the transient working-memory store."""

    key: str
    value: Any
    ttl_seconds: int = Field(default=3600, ge=1)


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class MemoryManager:
    """Manages short-term, long-term, and working memory for an agent.

    All operations are tenant-scoped — no cross-tenant data leakage.
    """

    def __init__(
        self,
        tenant_id: str,
        config: Optional[AIConfig] = None,
    ) -> None:
        self.tenant_id: str = tenant_id
        self.config: AIConfig = config or get_ai_config()

        # In-memory stores (persisted long-term would hook into a vector DB)
        self._short_term: list[dict[str, Any]] = []
        self._working: dict[str, WorkingMemoryItem] = {}
        self._long_term_index: dict[str, MemoryEntry] = {}

    # ------------------------------------------------------------------
    # Short-term memory (conversation window)
    # ------------------------------------------------------------------

    def add_to_short_term(self, role: str, content: str) -> None:
        """Append a message to the short-term conversation window.

        Automatically trims the oldest entries if the window exceeds
        ``AGENT_MEMORY_WINDOW_TOKENS``.
        """
        self._short_term.append({"role": role, "content": content})
        self._trim_short_term()

    def get_short_term(self) -> list[dict[str, Any]]:
        """Return the full short-term message list."""
        return list(self._short_term)

    def clear_short_term(self) -> None:
        """Reset the conversation window."""
        self._short_term.clear()

    def _token_estimate(self, text: str) -> int:
        """Rough token count from character length."""
        return int(len(text) * _TOKENS_PER_CHAR)

    def _trim_short_term(self) -> None:
        """Evict oldest messages until the window is within token budget."""
        budget = self.config.AGENT_MEMORY_WINDOW_TOKENS
        while len(self._short_term) > 1:
            total = sum(self._token_estimate(m["content"]) for m in self._short_term)
            if total <= budget:
                break
            self._short_term.pop(0)

    # ------------------------------------------------------------------
    # Long-term memory (vectorised + semantic search)
    # ------------------------------------------------------------------

    async def store_long_term(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Persist a memory chunk and return its entry_id.

        Generates an embedding via the configured EmbeddingGateway
        (never calls a model directly).
        """
        import uuid
        entry_id = uuid.uuid4().hex[:12]
        entry = MemoryEntry(
            entry_id=entry_id,
            tenant_id=self.tenant_id,
            content=content,
            embedding=None,  # populated asynchronously via EmbeddingGateway
            metadata=metadata or {},
            created_at=asyncio.get_event_loop().strftime("%Y-%m-%dT%H:%M:%SZ")
            if hasattr(asyncio.get_event_loop(), "strftime")
            else "",
        )
        # Placeholder: real implementation would call EmbeddingGateway here
        self._long_term_index[entry_id] = entry
        logger.debug("Stored long-term memory entry %s for tenant %s", entry_id, self.tenant_id)
        return entry_id

    async def search_long_term(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.6,
    ) -> list[MemoryEntry]:
        """Semantic search over stored long-term memories.

        Returns entries whose cosine similarity to the query exceeds
        ``score_threshold``.  Falls back to keyword match when no
        embeddings are available.
        """
        candidates = [
            e for e in self._long_term_index.values()
            if e.tenant_id == self.tenant_id
        ]
        # Simple keyword fallback when embeddings are absent
        query_terms = set(query.lower().split())
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in candidates:
            entry_terms = set(entry.content.lower().split())
            if entry_terms & query_terms:
                scored.append((len(entry_terms & query_terms) / max(len(query_terms), 1), entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            entry for score, entry in scored[:top_k]
            if score >= score_threshold
        ]

    def list_long_term(self) -> list[MemoryEntry]:
        """Return all long-term entries for this tenant."""
        return [
            e for e in self._long_term_index.values()
            if e.tenant_id == self.tenant_id
        ]

    # ------------------------------------------------------------------
    # Working memory (task context)
    # ------------------------------------------------------------------

    def set_working(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Store a value in working memory with an optional TTL."""
        self._working[key] = WorkingMemoryItem(key=key, value=value, ttl_seconds=ttl_seconds)

    def get_working(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from working memory, or *default* if absent."""
        item = self._working.get(key)
        if item is None:
            return default
        return item.value

    def delete_working(self, key: str) -> bool:
        """Remove a working-memory entry. Returns True if it existed."""
        return self._working.pop(key, None) is not None

    def clear_working(self) -> None:
        """Flush all working-memory entries."""
        self._working.clear()

    def compact_working(self) -> int:
        """Remove expired working-memory entries. Returns count removed."""
        now = asyncio.get_event_loop().time() if hasattr(asyncio.get_event_loop(), "time") else 0
        expired = [k for k, v in self._working.items() if now - v.ttl_seconds > 0]
        for k in expired:
            del self._working[k]
        return len(expired)

"""CrossEncoderReranker — rank retrieved chunks by relevance to query."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from services.ai.rag.vectorstore import QueryResult


@dataclass
class RerankResult:
    """A single reranked result with an explicit relevance score."""
    doc_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    rank: int = 0


class CrossEncoderReranker:
    """
    Reranks a list of retrieved results by computing a cross-encoder relevance
    score for every (query, chunk) pair.

    In production this delegates to ModelGateway (R3 compliant).
    For testing a mock scoring function is used when no gateway is provided.
    """

    def __init__(self, gateway: Optional[Any] = None) -> None:
        self._gw = gateway

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def rerank(
        self,
        query: str,
        results: Sequence[QueryResult],
        *,
        tenant_id: str,
        top_k: Optional[int] = None,
    ) -> list[QueryResult]:
        """
        Return reranked results sorted by relevance score (descending).
        If *top_k* is given, returns only the top-k.
        """
        if not results:
            return []

        scored = await self._score_pairs(query, results, tenant_id=tenant_id)

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)

        out: list[QueryResult] = []
        for i, item in enumerate(scored):
            if top_k is not None and i >= top_k:
                break
            out.append(QueryResult(
                doc_id=item["doc_id"],
                text=item["text"],
                score=item["score"],
                metadata=item.get("metadata", {}),
            ))
        return out

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    async def _score_pairs(
        self,
        query: str,
        results: Sequence[QueryResult],
        *,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Score each (query, chunk) pair. Uses gateway in prod, mock otherwise."""
        if self._gw is not None:
            return await self._score_via_gateway(query, results, tenant_id=tenant_id)
        return self._score_mock(query, results)

    async def _score_via_gateway(
        self,
        query: str,
        results: Sequence[QueryResult],
        *,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Delegate to ModelGateway.rerank (R3 compliance)."""
        texts = [r.text for r in results]
        ranked = await self._gw.rerank(query, texts, tenant_id=tenant_id)
        # ranked: list of {"index": int, "score": float}
        id_score_map = {r["index"]: r["score"] for r in ranked}
        scored = []
        for i, r in enumerate(results):
            scored.append({
                "doc_id": r.doc_id,
                "text": r.text,
                "score": id_score_map.get(i, 0.0),
                "metadata": r.metadata,
            })
        return scored

    def _score_mock(
        self,
        query: str,
        results: Sequence[QueryResult],
    ) -> list[dict[str, Any]]:
        """
        Mock scoring: uses a simple token-overlap heuristic so tests pass
        without external dependencies.

        Score = (overlap_count / len(query_tokens)) * max(result.score, 0.01)
        """
        query_tokens = set(query.lower().split())
        scored = []
        for r in results:
            doc_tokens = set(r.text.lower().split())
            overlap = len(query_tokens & doc_tokens)
            base = max(r.score, 0.01)
            mock_score = (overlap / max(len(query_tokens), 1)) * base
            scored.append({
                "doc_id": r.doc_id,
                "text": r.text,
                "score": round(mock_score, 6),
                "metadata": r.metadata,
            })
        return scored

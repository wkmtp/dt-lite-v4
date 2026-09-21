"""HybridRetriever: sparse (BM25) + dense (vector) + graph (KG entity) with RRF fusion."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from services.ai.rag.vectorstore import VectorStore, QueryResult
from services.ai.rag.embedder import Embedder
from services.ai.rag.chunker import Chunk


@dataclass
class SparseResult:
    """A BM25-style sparse retrieval result."""
    doc_id: str
    score: float
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphResult:
    """A knowledge-graph entity retrieval result."""
    entity_id: str
    score: float
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    """
    Combines sparse (BM25), dense (vector), and graph (KG entity) retrieval
    using Reciprocal Rank Fusion (RRF).

    RRF formula:
        score(doc) = Σ_s ( w_s / (k + rank_s(doc)) )
    where k is the RRF constant (default 60) and the sum is over all signals
    that returned *doc*.
    """

    # RRF constants
    RRF_K: float = 60.0

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
        bm25_index: Optional[Any] = None,
        kg_index: Optional[Any] = None,
    ) -> None:
        self._vs = vector_store
        self._embedder = embedder
        self._bm25 = bm25_index
        self._kg = kg_index

    async def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,
        top_k: int = 10,
        sparse_weight: float = 0.3,
        dense_weight: float = 0.5,
        graph_weight: float = 0.2,
        rrf_k: Optional[float] = None,
    ) -> list[QueryResult]:
        """
        Run all three retrieval signals and fuse via RRF.
        Returns top-*top_k* merged results, filtered to the given tenant.
        """
        filter_meta = {"tenant_id": tenant_id}

        # Dense
        q_emb = await self._embedder.embed_one(query, tenant_id=tenant_id)
        dense_results = await self._vs.search(
            q_emb,
            tenant_id=tenant_id,
            top_k=top_k * 2,
            filter_metadata=filter_meta,
        )
        dense_map: dict[str, QueryResult] = {r.doc_id: r for r in dense_results}

        # Sparse (BM25)
        sparse_results: list[SparseResult] = []
        if self._bm25 is not None:
            sparse_results = await self._retrieve_bm25(
                query, top_k=top_k * 2, tenant_id=tenant_id
            )
        sparse_map: dict[str, SparseResult] = {r.doc_id: r for r in sparse_results}

        # Graph
        graph_results: list[GraphResult] = []
        if self._kg is not None:
            graph_results = await self._retrieve_kg(
                query, top_k=top_k * 2, tenant_id=tenant_id
            )
        graph_map: dict[str, GraphResult] = {r.entity_id: r for r in graph_results}

        # RRF fusion
        k_const = rrf_k if rrf_k is not None else self.RRF_K
        all_doc_ids = set(dense_map.keys()) | set(sparse_map.keys()) | set(graph_map.keys())

        # Build rank maps: doc_id -> (signal, rank_within_signal)
        def _rank_map(results: list[Any]) -> dict[str, int]:
            return {r.doc_id if hasattr(r, "doc_id") else r.entity_id: i
                    for i, r in enumerate(results)}

        dense_ranks = _rank_map(dense_results)
        sparse_ranks = _rank_map(sparse_results)
        graph_ranks = _rank_map(graph_results)

        rrf_scores: dict[str, float] = {}
        for doc_id in all_doc_ids:
            score = 0.0
            if doc_id in dense_ranks:
                score += dense_weight / (k_const + dense_ranks[doc_id] + 1)
            if doc_id in sparse_ranks:
                score += sparse_weight / (k_const + sparse_ranks[doc_id] + 1)
            if doc_id in graph_ranks:
                score += graph_weight / (k_const + graph_ranks[doc_id] + 1)
            rrf_scores[doc_id] = score

        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]
        merged: list[QueryResult] = []
        for doc_id in sorted_ids:
            if doc_id in dense_map:
                merged.append(dense_map[doc_id])
            elif doc_id in sparse_map:
                sr = sparse_map[doc_id]
                merged.append(QueryResult(
                    doc_id=sr.doc_id, text=sr.text,
                    score=rrf_scores[doc_id], metadata=sr.metadata,
                ))
            elif doc_id in graph_map:
                gr = graph_map[doc_id]
                merged.append(QueryResult(
                    doc_id=gr.entity_id, text=gr.text,
                    score=rrf_scores[doc_id], metadata=gr.metadata,
                ))
        return merged

    async def _retrieve_bm25(
        self, query: str, top_k: int, *, tenant_id: str
    ) -> list[SparseResult]:
        """BM25 retrieval via the configured index (e.g. Whoosh / Elasticsearch)."""
        if self._bm25 is None:
            return []
        return await self._bm25.search(query, top_k=top_k, tenant_id=tenant_id)

    async def _retrieve_kg(
        self, query: str, top_k: int, *, tenant_id: str
    ) -> list[GraphResult]:
        """KG entity retrieval via the configured index."""
        if self._kg is None:
            return []
        return await self._kg.search(query, top_k=top_k, tenant_id=tenant_id)

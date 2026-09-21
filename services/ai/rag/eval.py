"""RAG evaluation framework: Recall@K, MRR, ContextRelevance, NDCG@K, BenchmarkRunner."""
from __future__ import annotations

import asyncio
import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional, Sequence

from services.ai.rag.vectorstore import QueryResult


@dataclass
class RAGEvalResult:
    """Results of a single RAG evaluation run."""
    recall_at_k: float
    mrr: float
    context_relevance: float
    ndcg_at_k: float
    p99_latency_ms: float = 0.0
    per_query: list[dict[str, Any]] = field(default_factory=list)


class RAGEval:
    """
    Evaluation framework for RAG pipelines.
    Metrics:
    - Recall@K: fraction of relevant documents retrieved
    - MRR: mean reciprocal rank of first relevant document
    - ContextRelevance: proportion of retrieved context that is relevant
    - NDCG@K: normalized discounted cumulative gain
    """

    def __init__(self, k: int = 5) -> None:
        self._k = k

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    @staticmethod
    def recall_at_k(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
        """Fraction of ground-truth relevant docs found in top-K."""
        if not relevant:
            return 0.0
        retrieved_set = set(retrieved[:len(retrieved)])
        relevant_set = set(relevant)
        hits = len(retrieved_set & relevant_set)
        return hits / len(relevant_set)

    @staticmethod
    def mean_reciprocal_rank(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
        """Mean reciprocal rank: 1/rank of first relevant doc, 0 if none."""
        relevant_set = set(relevant)
        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant_set:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def context_relevance(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
        """Fraction of retrieved docs that are relevant."""
        if not retrieved:
            return 0.0
        relevant_set = set(relevant)
        hits = sum(1 for doc_id in retrieved if doc_id in relevant_set)
        return hits / len(retrieved)

    @staticmethod
    def ndcg_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: Optional[int] = None) -> float:
        """Normalized discounted cumulative gain at K."""
        effective_k = k or len(retrieved)
        effective_k = min(effective_k, len(retrieved))
        relevant_set = set(relevant)

        dcg = 0.0
        for i in range(effective_k):
            if retrieved[i] in relevant_set:
                dcg += 1.0 / math.log2(i + 2)

        # Ideal DCG: all relevant docs at the top
        ideal_hits = min(len(relevant_set), effective_k)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))

        return dcg / idcg if idcg > 0 else 0.0

    # ------------------------------------------------------------------
    # Evaluate a single query
    # ------------------------------------------------------------------

    def evaluate_query(
        self,
        query: str,
        relevant_docs: Sequence[str],
        retrieved_docs: Sequence[QueryResult],
    ) -> dict[str, Any]:
        """Evaluate a single query, returning per-query metrics."""
        ret_ids = [r.doc_id for r in retrieved_docs[: self._k]]
        recall = self.recall_at_k(ret_ids, relevant_docs)
        mrr = self.mean_reciprocal_rank(ret_ids, relevant_docs)
        relevance = self.context_relevance(ret_ids, relevant_docs)
        ndcg = self.ndcg_at_k(ret_ids, relevant_docs, self._k)
        return {
            "query": query,
            "recall": recall,
            "mrr": mrr,
            "context_relevance": relevance,
            "ndcg": ndcg,
        }

    # ------------------------------------------------------------------
    # Evaluate full batch
    # ------------------------------------------------------------------

    def evaluate(
        self,
        queries: Sequence[str],
        relevant_docs: Sequence[Sequence[str]],
        retrieved_docs: Sequence[Sequence[QueryResult]],
        latencies_ms: Optional[Sequence[float]] = None,
    ) -> RAGEvalResult:
        """
        Evaluate RAG performance over a full batch.

        Args:
            queries: List of query strings.
            relevant_docs: List of lists of ground-truth relevant doc ids.
            retrieved_docs: List of lists of QueryResult objects (ordered).
            latencies_ms: Optional list of per-query latencies in ms.
        """
        n = len(queries)
        if n != len(relevant_docs) or n != len(retrieved_docs):
            raise ValueError("All three sequences must have the same length")

        recalls: list[float] = []
        mrrs: list[float] = []
        relevances: list[float] = []
        ndcgs: list[float] = []
        per_query: list[dict[str, Any]] = []

        for q, rel, ret in zip(queries, relevant_docs, retrieved_docs):
            result = self.evaluate_query(q, rel, ret)
            per_query.append(result)
            recalls.append(result["recall"])
            mrrs.append(result["mrr"])
            relevances.append(result["context_relevance"])
            ndcgs.append(result["ndcg"])

        p99 = 0.0
        if latencies_ms:
            sorted_latencies = sorted(latencies_ms)
            idx = int(math.ceil(0.99 * len(sorted_latencies))) - 1
            p99 = sorted_latencies[max(idx, 0)]

        return RAGEvalResult(
            recall_at_k=sum(recalls) / n if n else 0.0,
            mrr=sum(mrrs) / n if n else 0.0,
            context_relevance=sum(relevances) / n if n else 0.0,
            ndcg_at_k=sum(ndcgs) / n if n else 0.0,
            p99_latency_ms=p99,
            per_query=per_query,
        )

    # ------------------------------------------------------------------
    # JSONL dataset loading
    # ------------------------------------------------------------------

    @staticmethod
    def load_jsonl(path: str | Path) -> list[dict[str, str]]:
        """Load a JSONL eval dataset file, one JSON object per line."""
        p = Path(path)
        records: list[dict[str, str]] = []
        with p.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON on line {line_no} of {p}"
                    ) from exc
        return records


class BenchmarkRunner:
    """
    Runs RAG evaluation against a real or mock retriever.
    Supports async invocation and JSONL dataset I/O.
    """

    def __init__(
        self,
        retriever_fn: Callable[[str, dict[str, Any]], Any],
        *,
        k: int = 5,
        timeout_s: float = 5.0,
    ) -> None:
        """
        Args:
            retriever_fn: Async callable signature
                ``async (query: str, context: dict) -> list[QueryResult]``
            k: Top-K for metrics.
            timeout_s: Per-query timeout.
        """
        self._retriever_fn = retriever_fn
        self._k = k
        self._timeout_s = timeout_s

    async def _run_one(
        self,
        query: str,
        ctx: dict[str, Any],
    ) -> tuple[list[QueryResult], float]:
        """Run one query, return (results, latency_ms)."""
        t0 = time.monotonic()
        try:
            results = await asyncio.wait_for(
                self._retriever_fn(query, ctx),
                timeout=self._timeout_s,
            )
        except asyncio.TimeoutError:
            results = []
        latency_ms = (time.monotonic() - t0) * 1000
        return results, latency_ms

    async def run(
        self,
        dataset: Sequence[dict[str, str]],
        *,
        tenant_id: str = "default",
        top_k: int = 5,
    ) -> RAGEvalResult:
        """
        Run the full benchmark over *dataset*.

        Each dataset entry must have keys:
            question, answer, context, kb_id
        The ``answer`` field is used as the ground-truth relevant doc id.
        The ``context`` field is returned as the retrieved chunk text.
        """
        queries: list[str] = []
        relevant: list[list[str]] = []
        retrieved: list[list[QueryResult]] = []
        latencies: list[float] = []

        ctx = {"tenant_id": tenant_id, "top_k": top_k}

        for entry in dataset:
            q = entry["question"]
            answer = entry["answer"]
            queries.append(q)
            relevant.append([answer])
            results, lat = await self._run_one(q, ctx)
            latencies.append(lat)
            retrieved.append(results)

        eval_ = RAGEval(k=top_k)
        return eval_.evaluate(queries, relevant, retrieved, latencies_ms=latencies)

    def run_sync(
        self,
        dataset: Sequence[dict[str, str]],
        *,
        tenant_id: str = "default",
        top_k: int = 5,
    ) -> RAGEvalResult:
        """Synchronous wrapper around :meth:`run`."""
        return asyncio.get_event_loop().run_until_complete(
            self.run(dataset, tenant_id=tenant_id, top_k=top_k)
        )

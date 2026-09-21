"""Vector Store ABC + Postgres/pgvector implementation + Milvus fallback."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from pydantic import BaseModel, Field


@dataclass
class VectorDocument:
    """A single chunk stored in a vector index."""
    doc_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    """A single match returned by the retriever."""
    doc_id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorStore(ABC):
    """Abstract base for vector stores used by the RAG pipeline."""

    @abstractmethod
    async def upsert(self, docs: Sequence[VectorDocument], *, tenant_id: str) -> list[str]:
        """Upsert documents and return their stored ids."""

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        *,
        tenant_id: str,
        top_k: int = 10,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[QueryResult]:
        """Return top-k nearest neighbours."""

    @abstractmethod
    async def delete(self, doc_ids: Sequence[str], *, tenant_id: str) -> int:
        """Delete documents by id. Return number deleted."""

    @abstractmethod
    async def exists(self, doc_id: str, *, tenant_id: str) -> bool:
        """Check whether a document is stored."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources."""


# ---------------------------------------------------------------------------
# PGVector implementation
# ---------------------------------------------------------------------------

class PGVectorStore(VectorStore):
    """Postgres/pgvector vector store. Collection names are always tenant-prefixed."""

    def __init__(
        self,
        dsn: str,
        embedding_dim: int = 3072,
        max_connections: int = 10,
    ) -> None:
        self._dsn = dsn
        self._embedding_dim = embedding_dim
        self._max_connections = max_connections
        self._pool: Any = None

    def _collection(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}_rag_docs"

    async def _ensure_pool(self) -> Any:
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._dsn, max_size=self._max_connections)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._collection('')} (
                        id TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        embedding vector({self._embedding_dim}),
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    CREATE INDEX IF NOT EXISTS idx_{self._collection('')}_embedding
                        ON {self._collection('')} USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100);
                    """
                )
        return self._pool

    async def upsert(self, docs: Sequence[VectorDocument], *, tenant_id: str) -> list[str]:
        pool = await self._ensure_pool()
        table = self._collection(tenant_id)
        ids: list[str] = []
        async with pool.acquire() as conn:
            for doc in docs:
                existing = await conn.fetchval(
                    f"SELECT id FROM {table} WHERE id = $1", doc.doc_id
                )
                if existing:
                    await conn.execute(
                        f"UPDATE {table} SET text=$1, embedding=$2, metadata=$3 WHERE id=$4",
                        doc.text, doc.embedding, doc.metadata, doc.doc_id,
                    )
                else:
                    await conn.execute(
                        f"INSERT INTO {table} (id, text, embedding, metadata) VALUES ($1,$2,$3,$4)",
                        doc.doc_id, doc.text, doc.embedding, doc.metadata,
                    )
                ids.append(doc.doc_id)
        return ids

    async def search(
        self,
        query_embedding: list[float],
        *,
        tenant_id: str,
        top_k: int = 10,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[QueryResult]:
        pool = await self._ensure_pool()
        table = self._collection(tenant_id)
        where = "1=1"
        params: list[Any] = [query_embedding, top_k]
        if filter_metadata:
            placeholders = [f"metadata->>'{k}' = ${{i+3}}" for i, k in enumerate(sorted(filter_metadata.keys()))]
            where += " AND " + " AND ".join(placeholders)
            params += list(filter_metadata.values())
        rows = await pool.fetch(
            f"SELECT id, text, embedding, metadata FROM {table} WHERE {where} ORDER BY embedding <=> $1 LIMIT $2",
            *params,
        )
        return [
            QueryResult(doc_id=r["id"], text=r["text"], score=float(r["embedding"]), metadata=r["metadata"])
            for r in rows
        ]

    async def delete(self, doc_ids: Sequence[str], *, tenant_id: str) -> int:
        pool = await self._ensure_pool()
        table = self._collection(tenant_id)
        result = await pool.execute(f"DELETE FROM {table} WHERE id = ANY($1)", list(doc_ids))
        return int(result.split()[-1])

    async def exists(self, doc_id: str, *, tenant_id: str) -> bool:
        pool = await self._ensure_pool()
        table = self._collection(tenant_id)
        row = await pool.fetchval(f"SELECT 1 FROM {table} WHERE id=$1", doc_id)
        return row is not None

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None


# ---------------------------------------------------------------------------
# Milvus fallback
# ---------------------------------------------------------------------------

class MilvusStore(VectorStore):
    """Milvus vector store fallback. Collection names are always tenant-prefixed."""

    def __init__(
        self,
        uri: str = "http://localhost:19530",
        token: str = "",
        embedding_dim: int = 3072,
    ) -> None:
        self._uri = uri
        self._token = token
        self._embedding_dim = embedding_dim
        self._collection: Any = None

    def _collection_name(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}_rag"

    async def _ensure_collection(self, tenant_id: str) -> None:
        from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
        name = self._collection_name(tenant_id)
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self._embedding_dim),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
        ]
        schema = CollectionSchema(fields, "RAG document store")
        self._collection = Collection(name, schema, connection_uri=self._uri, token=self._token)
        index_params = {"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        self._collection.create_index("embedding", index_params)
        self._collection.load()

    async def upsert(self, docs: Sequence[VectorDocument], *, tenant_id: str) -> list[str]:
        if self._collection is None:
            await self._ensure_collection(tenant_id)
        ids = [d.doc_id for d in docs]
        texts = [d.text for d in docs]
        embs = [d.embedding for d in docs]
        metas = [str(m) for m in [d.metadata for d in docs]]
        self._collection.upsert([ids, texts, embs, metas])
        return ids

    async def search(
        self,
        query_embedding: list[float],
        *,
        tenant_id: str,
        top_k: int = 10,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[QueryResult]:
        if self._collection is None:
            await self._ensure_collection(tenant_id)
        expr = " AND ".join(f"metadata LIKE '%{k}%{v}%'" for k, v in (filter_metadata or {}).items()) if filter_metadata else None
        results = self._collection.search(
            [query_embedding], "embedding",
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=top_k,
            expr=expr,
        )
        hits = results[0]
        return [
            QueryResult(
                doc_id=h.id,
                text=h.entity.get("text"),
                score=float(h.distance),
                metadata={},
            )
            for h in hits
        ]

    async def delete(self, doc_ids: Sequence[str], *, tenant_id: str) -> int:
        if self._collection is None:
            await self._ensure_collection(tenant_id)
        expr = f"id in [{', '.join(repr(i) for i in doc_ids)}]"
        self._collection.delete(expr)
        return len(doc_ids)

    async def exists(self, doc_id: str, *, tenant_id: str) -> bool:
        if self._collection is None:
            await self._ensure_collection(tenant_id)
        results = self._collection.query(expr=f"id=='{doc_id}'", output_fields=["id"])
        return len(results) > 0

    async def close(self) -> None:
        if self._collection:
            self._collection.release()
            self._collection = None

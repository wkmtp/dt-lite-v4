"""KnowledgeBase CRUD: document upload → chunk → embed → index with version control and incremental update."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from pydantic import BaseModel, Field

from services.ai.rag.chunker import DocumentChunker, Chunk, ChunkStrategy
from services.ai.rag.embedder import Embedder
from services.ai.rag.vectorstore import VectorStore, VectorDocument


@dataclass
class DocumentMeta:
    """Metadata about an ingested document."""
    doc_id: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    version: int
    chunk_count: int
    status: str  # "pending", "indexed", "failed"


class KnowledgeBase:
    """
    Manages a tenant's knowledge base:
    - Upload and parse documents (via MultimodalProcessor)
    - Chunk documents
    - Embed chunks
    - Index into VectorStore
    - Track versions and support incremental updates
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
        chunker: Optional[DocumentChunker] = None,
    ) -> None:
        self._vs = vector_store
        self._embedder = embedder
        self._chunker = chunker or DocumentChunker()
        # In-memory version registry (replace with DB in production)
        self._versions: dict[str, list[DocumentMeta]] = {}

    async def upload(
        self,
        doc_id: str,
        content: bytes,
        filename: str,
        content_type: str,
        *,
        tenant_id: str,
        strategy: ChunkStrategy = ChunkStrategy.TOKEN,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> DocumentMeta:
        """
        Parse content, chunk, embed, and index. Returns the DocumentMeta.
        """
        # Determine strategy config
        from services.ai.rag.chunker import ChunkConfig
        config = ChunkConfig(strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunker = DocumentChunker(config)

        # Parse content into text (simple; use MultimodalProcessor for complex formats)
        text = self._parse_content(content, content_type)
        if not text:
            raise ValueError(f"Could not extract text from {filename}")

        # Chunk
        chunks = chunker.chunk(text, doc_id=doc_id)

        # Embed
        texts = [c.text for c in chunks]
        embeddings = await self._embedder.embed(texts, tenant_id=tenant_id)

        # Upsert into vector store
        docs = [
            VectorDocument(
                doc_id=f"{doc_id}_chunk_{c.chunk_index}",
                text=c.text,
                embedding=emb,
                metadata={"source_doc_id": doc_id, "chunk_index": c.chunk_index, "filename": filename},
            )
            for c, emb in zip(chunks, embeddings)
        ]
        await self._vs.upsert(docs, tenant_id=tenant_id)

        # Update version registry
        now = datetime.now(timezone.utc)
        meta = DocumentMeta(
            doc_id=doc_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            uploaded_at=now,
            version=self._next_version(tenant_id, doc_id),
            chunk_count=len(chunks),
            status="indexed",
        )
        self._versions.setdefault(tenant_id, []).append(meta)
        return meta

    async def get_versions(
        self,
        tenant_id: str,
        doc_id: Optional[str] = None,
    ) -> list[DocumentMeta]:
        """Return version history for a document (or all documents in the tenant)."""
        versions = self._versions.get(tenant_id, [])
        if doc_id:
            return [v for v in versions if v.doc_id == doc_id]
        return versions

    async def delete_document(
        self,
        doc_id: str,
        *,
        tenant_id: str,
    ) -> int:
        """Delete all chunks for a document and return count deleted."""
        # Find all chunk ids for this doc
        # In production, query the vector store for doc_id prefix matches
        all_versions = self._versions.get(tenant_id, [])
        chunks_to_delete = []
        for v in all_versions:
            if v.doc_id == doc_id and v.status == "indexed":
                for i in range(v.chunk_count):
                    chunks_to_delete.append(f"{doc_id}_chunk_{i}")
        if chunks_to_delete:
            await self._vs.delete(chunks_to_delete, tenant_id=tenant_id)
        return len(chunks_to_delete)

    async def incremental_update(
        self,
        doc_id: str,
        new_content: bytes,
        new_filename: str,
        content_type: str,
        *,
        tenant_id: str,
    ) -> DocumentMeta:
        """
        Incremental update: delete old chunks, re-ingest with new content.
        Returns the new DocumentMeta.
        """
        # Delete previous version
        await self.delete_document(doc_id, tenant_id=tenant_id)
        # Re-upload
        return await self.upload(
            doc_id, new_content, new_filename, content_type,
            tenant_id=tenant_id,
        )

    def _next_version(self, tenant_id: str, doc_id: str) -> int:
        versions = [v for v in self._versions.get(tenant_id, []) if v.doc_id == doc_id]
        return max((v.version for v in versions), default=0) + 1

    def _parse_content(self, content: bytes, content_type: str) -> str:
        """
        Simple content parser. In production, delegate to MultimodalProcessor.
        """
        if content_type.startswith("text/") or content_type in ("application/json", "application/xml"):
            return content.decode("utf-8", errors="replace")
        if content_type == "application/pdf":
            # TODO: integrate with pymupdf or similar
            return "[PDF content extraction pending]"
        if content_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "application/msword"):
            return "[Word content extraction pending]"
        return content.decode("utf-8", errors="replace")

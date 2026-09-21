"""RAG Pipeline - Main entry point for retrieval-augmented generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from services.ai.model.gateway import ModelGateway
from services.ai.rag.chunker import DocumentChunker
from services.ai.rag.embedder import Embedder
from services.ai.rag.vectorstore import VectorStore, PGVectorStore
from services.ai.rag.retriever import HybridRetriever
from services.ai.rag.reranker import CrossEncoderReranker
from services.ai.rag.context_injector import ContextInjector
from services.ai.rag.knowledge_base import KnowledgeBase
from services.ai.rag.multimodal import MultimodalProcessor


@dataclass
class RAGPipeline:
    """
    Main entry point for the RAG pipeline. Orchestrates chunking, embedding,
    retrieval, reranking, and context injection.
    """
    gateway: ModelGateway
    vector_store: Optional[VectorStore] = None
    embedder: Optional[Embedder] = None
    chunker: Optional[DocumentChunker] = None
    retriever: Optional[HybridRetriever] = None
    reranker: Optional[CrossEncoderReranker] = None
    context_injector: Optional[ContextInjector] = None
    knowledge_base: Optional[KnowledgeBase] = None
    multimodal_processor: Optional[MultimodalProcessor] = None

    def __post_init__(self) -> None:
        if self.embedder is None:
            self.embedder = Embedder(self.gateway)
        if self.chunker is None:
            self.chunker = DocumentChunker()
        if self.context_injector is None:
            self.context_injector = ContextInjector()
        if self.reranker is None:
            self.reranker = CrossEncoderReranker(self.gateway)
        if self.multimodal_processor is None:
            self.multimodal_processor = MultimodalProcessor()
        if self.knowledge_base is None and self.vector_store is not None:
            self.knowledge_base = KnowledgeBase(self.vector_store, self.embedder, self.chunker)
        if self.retriever is None and self.vector_store is not None:
            self.retriever = HybridRetriever(self.vector_store, self.embedder)

    async def ingest(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        *,
        tenant_id: str,
        doc_id: Optional[str] = None,
    ) -> Any:
        """
        Ingest a document: parse → chunk → embed → index.
        Returns the DocumentMeta from KnowledgeBase.
        """
        if self.knowledge_base is None:
            raise RuntimeError("KnowledgeBase not initialized; provide a VectorStore")
        if doc_id is None:
            import uuid
            doc_id = str(uuid.uuid4())
        return await self.knowledge_base.upload(
            doc_id, content, filename, content_type,
            tenant_id=tenant_id,
        )

    async def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,
        top_k: int = 10,
    ) -> list[Any]:
        """
        Retrieve relevant documents for a query.
        Returns a list of QueryResult objects.
        """
        if self.retriever is None:
            raise RuntimeError("Retriever not initialized; provide a VectorStore")
        return await self.retriever.retrieve(query, tenant_id=tenant_id, top_k=top_k)

    async def retrieve_and_rerank(
        self,
        query: str,
        *,
        tenant_id: str,
        top_k: int = 10,
        rerank_top_k: Optional[int] = None,
    ) -> list[Any]:
        """
        Retrieve and rerank results using cross-encoder.
        """
        results = await self.retrieve(query, tenant_id=tenant_id, top_k=top_k * 2)
        if self.reranker is None:
            return results
        return await self.reranker.rerank(query, results, tenant_id=tenant_id, top_k=rerank_top_k or top_k)

    async def build_context(
        self,
        query: str,
        *,
        tenant_id: str,
        system_prompt: str = "",
        top_k: int = 10,
    ) -> str:
        """
        Build the final context string for the LLM prompt.
        """
        results = await self.retrieve_and_rerank(query, tenant_id=tenant_id, top_k=top_k)
        from services.ai.rag.context_injector import ContextItem
        items = [
            ContextItem(text=r.text, score=r.score, metadata=r.metadata)
            for r in results
        ]
        return self.context_injector.build_context(items, query=query, system_prompt=system_prompt)

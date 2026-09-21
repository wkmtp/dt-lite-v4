"""Task 17 CP1 — RAG Pipeline skeleton smoke test."""
import pytest
from uuid import uuid4

from services.ai.rag.vectorstore import PGVectorStore
from services.ai.rag.embedder import Embedder
from services.ai.rag.chunker import DocumentChunker
from services.ai.rag.retriever import HybridRetriever
from services.ai.rag.reranker import CrossEncoderReranker
from services.ai.rag.context_injector import ContextInjector
from services.ai.rag.knowledge_base import KnowledgeBase


class TestRAGSkeleton:
    def test_chunker_init(self):
        chunker = DocumentChunker(chunk_size=256, overlap=32)
        assert chunker.chunk_size == 256

    def test_embedder_init(self):
        embedder = Embedder()
        assert embedder.model is not None

    def test_context_injector_init(self):
        ci = ContextInjector(max_context_tokens=8000)
        assert ci.max_context_tokens == 8000

    def test_knowledge_base_init(self):
        kb = KnowledgeBase(
            kb_id=uuid4(),
            tenant_id=uuid4(),
            name="test-kb",
        )
        assert kb.tenant_id is not None


class TestHybridRetriever:
    def test_retriever_init(self):
        r = HybridRetriever(top_k=5, rrf_k=60)
        assert r.top_k == 5


class TestCrossEncoderReranker:
    def test_reranker_init(self):
        r = CrossEncoderReranker(top_k=3)
        assert r.top_k == 3

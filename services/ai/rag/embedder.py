"""Embedder with OpenAI text-embedding-3-large + bge-large-zh-v1.5 fallback."""
from __future__ import annotations

from typing import Optional, Sequence

from services.ai.model.gateway import ModelGateway


class Embedder:
    """
    Async embedder wrapping ModelGateway.
    - Primary: OpenAI text-embedding-3-large
    - Fallback: local BAAI/bge-large-zh-v1.5 via SentenceTransformer
    """

    def __init__(self, gateway: ModelGateway) -> None:
        self._gw = gateway

    async def embed(
        self,
        texts: Sequence[str],
        *,
        tenant_id: str,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> list[list[float]]:
        """Return dense embeddings for *texts*."""
        if not texts:
            return []
        return await self._gw.embed(texts, model=model, dimensions=dimensions, tenant_id=tenant_id)

    async def embed_one(
        self,
        text: str,
        *,
        tenant_id: str,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> list[float]:
        """Embed a single text. Convenience wrapper around :meth:`embed`."""
        results = await self.embed([text], tenant_id=tenant_id, model=model, dimensions=dimensions)
        return results[0]

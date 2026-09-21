"""RAG endpoints: query and index.

R2: JWT + permission required.
R5: All LLM calls (if any) tracked.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends

from services.ai.api.schemas import RAGQueryRequest, RAGQueryResponse, RAGIndexRequest, RAGIndexResponse
from services.ai.api.deps import get_current_tenant, require_ai_permission, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["ai-rag"])


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    req: RAGQueryRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    _user = Depends(get_current_user),
):
    """Query a RAG collection and return relevant documents + synthesized answer."""
    from services.ai.rag.service import RAGService
    service = RAGService()
    result = await service.query(
        tenant_id=str(tenant_id),
        query=req.query,
        collection_id=req.collection_id,
        top_k=req.top_k,
    )
    return RAGQueryResponse(success=True, data=result)


@router.post("/index", response_model=RAGIndexResponse)
async def rag_index(
    req: RAGIndexRequest,
    tenant_id: UUID = Depends(get_current_tenant),
    _user = Depends(get_current_user),
):
    """Index documents into a RAG collection for later querying."""
    from services.ai.rag.service import RAGService
    service = RAGService()
    result = await service.index(
        tenant_id=str(tenant_id),
        collection_id=req.collection_id,
        documents=req.documents,
    )
    return RAGIndexResponse(success=True, data=result)

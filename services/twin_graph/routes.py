"""Twin Graph API Routes — FastAPI endpoints for relationship management."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.dependencies import get_current_tenant, require_permission
from services.database import AsyncSessionLocal
from services.twin_graph.exceptions import (
    InvalidRelationshipError,
    TwinEntityNotFoundError,
    TwinRelationshipNotFoundError,
)
from services.twin_graph.schemas import PathResponse, RelationshipCreateRequest, RelationshipResponse
from services.twin_graph.services import TwinGraphService

router = APIRouter(prefix="/api/v1/twin-graph", tags=["Twin Graph"])


def _get_graph_service(db: AsyncSession) -> TwinGraphService:
    return TwinGraphService(session=db)


# ==================== Relationship CRUD ====================

@router.post(
    "/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("twin_graph:create"))],
)
async def create_relationship(
    body: RelationshipCreateRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Create a semantic relationship between two twin entities.

    Security:
    - tenant_id from JWT context (not from body)
    - Both entities must exist in the same tenant
    """
    async with AsyncSessionLocal() as db:
        service = _get_graph_service(db)
        try:
            rel = await service.create_relation(
                source_id=body.source_id,
                target_id=body.target_id,
                relationship_type=body.relationship_type,
                tenant_id=tenant_id,
                metadata=body.metadata,
            )
        except InvalidRelationshipError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": e.code, "message": e.message})
        except TwinEntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})

    return RelationshipResponse.model_validate(rel)


@router.delete(
    "/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("twin_graph:delete"))],
)
async def delete_relationship(
    relationship_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Delete (soft-remove) a relationship."""
    async with AsyncSessionLocal() as db:
        service = _get_graph_service(db)
        try:
            ok = await service.remove_relation(relationship_id, tenant_id)
        except TwinRelationshipNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


# ==================== Neighbor Query ====================

@router.get(
    "/{twin_id}/neighbors",
    response_model=list[dict],
    dependencies=[Depends(require_permission("twin_graph:read"))],
)
async def get_neighbors(
    twin_id: UUID,
    relationship_type: Optional[str] = Query(None),
    direction: str = Query("both", pattern="^(outgoing|incoming|both)$"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Get all neighbor twin entities connected to the given entity.

    Supports filtering by relationship_type and traversal direction.
    """
    async with AsyncSessionLocal() as db:
        service = _get_graph_service(db)
        try:
            neighbors = await service.get_neighbors(
                twin_id, tenant_id,
                relationship_type=relationship_type,
                direction=direction,
            )
        except TwinEntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})
        return neighbors


# ==================== Path Query ====================

@router.get(
    "/path",
    response_model=PathResponse,
    dependencies=[Depends(require_permission("twin_graph:read"))],
)
async def find_path(
    source: UUID = Query(..., description="Source twin entity ID"),
    target: UUID = Query(..., description="Target twin entity ID"),
    max_depth: int = Query(5, ge=1, le=20, description="Maximum BFS depth"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """Find a path between two twin entities via graph traversal."""
    async with AsyncSessionLocal() as db:
        service = _get_graph_service(db)
        try:
            path = await service.find_path(source, target, tenant_id, max_depth=max_depth)
        except TwinEntityNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": e.code, "message": e.message})

        if path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PATH_NOT_FOUND", "message": f"No path from {source} to {target}"},
            )

    return PathResponse(
        source_id=source,
        target_id=target,
        path=path,
        depth=len(path) - 1,
    )

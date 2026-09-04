"""
DT-Lite Core Service - 核心模型
负责：Entity, Asset, Property, Relationship
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(
    title="DT-Lite Core Service",
    description="Core Digital Twin Model Service",
    version="4.0.0"
)

class Entity(BaseModel):
    id: Optional[int] = None
    name: str
    entity_type: str  # asset, location, person, etc.
    properties: Dict[str, Any] = {}
    parent_id: Optional[int] = None

class Asset(BaseModel):
    id: Optional[int] = None
    name: str
    asset_type: str
    location_id: Optional[int] = None
    properties: Dict[str, Any] = {}
    relationships: List[Dict[str, Any]] = []

@app.get("/")
async def root():
    return {"service": "DT-Lite Core", "version": "4.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/v1/entities")
async def list_entities(entity_type: Optional[str] = None):
    return {"success": True, "data": []}

@app.post("/api/v1/entities")
async def create_entity(entity: Entity):
    return {"success": True, "data": entity.model_dump()}

@app.get("/api/v1/assets")
async def list_assets():
    return {"success": True, "data": []}

@app.post("/api/v1/assets")
async def create_asset(asset: Asset):
    return {"success": True, "data": asset.model_dump()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

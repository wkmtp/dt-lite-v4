"""
DT-Lite Identity Service - 身份体系
负责：Tenant, User, Role, Permission
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(
    title="DT-Lite Identity Service",
    description="Identity & Access Management Service",
    version="4.0.0"
)

class Tenant(BaseModel):
    id: Optional[int] = None
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool = True

class User(BaseModel):
    id: Optional[int] = None
    tenant_id: int
    username: str
    email: str
    role: str  # admin, user, viewer
    is_active: bool = True

class Role(BaseModel):
    id: Optional[int] = None
    name: str
    permissions: List[str]

@app.get("/")
async def root():
    return {"service": "DT-Lite Identity", "version": "4.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/v1/tenants")
async def list_tenants():
    return {"success": True, "data": []}

@app.post("/api/v1/tenants")
async def create_tenant(tenant: Tenant):
    return {"success": True, "data": tenant.model_dump()}

@app.get("/api/v1/users")
async def list_users(tenant_id: int):
    return {"success": True, "data": []}

@app.post("/api/v1/users")
async def create_user(user: User):
    return {"success": True, "data": user.model_dump()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

from sqlalchemy import Column, String, DateTime, UUID
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from services.core.models.base import Base


class Role(Base):
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(128), nullable=False)
    code = Column(String(64), nullable=False)
    metadata = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

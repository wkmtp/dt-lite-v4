from sqlalchemy import Column, String, Text, DateTime, UUID
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from services.core.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(128), nullable=False)
    code = Column(String(64), unique=True, nullable=False)
    status = Column(String(32), nullable=False, default="active")
    metadata = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"

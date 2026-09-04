from sqlalchemy import Column, String, DateTime, UUID, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from services.core.models.base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    username = Column(String(128), nullable=False)
    email = Column(String(255))
    password_hash = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    metadata = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"

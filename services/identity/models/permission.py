from sqlalchemy import Column, String, Text, UUID
from sqlalchemy.dialects.postgresql import JSONB
from services.core.models.base import Base


class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    code = Column(String(128), unique=True, nullable=False)
    description = Column(Text)
    metadata = Column(JSONB, nullable=False, default={})

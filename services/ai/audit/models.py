"""SQLAlchemy models for AI audit and usage tracking.

These models persist audit data to PostgreSQL for long-term billing and analytics.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from services.database import engine


class Base(DeclarativeBase):
    pass


class AIUsageLog(Base):
    """Per-request usage record for billing and analytics."""

    __tablename__ = "ai_usage_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(Uuid, nullable=False, index=True)
    user_id = Column(Uuid, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    endpoint = Column(String(200), nullable=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    success = Column(Integer, nullable=False, default=1)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_ai_usage_tenant_ts", "tenant_id", "created_at"),
        Index("ix_ai_usage_trace", "trace_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "trace_id": self.trace_id,
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id),
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "success": bool(self.success),
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AIAuditLog(Base):
    """High-level audit trail for compliance and incident investigation."""

    __tablename__ = "ai_audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(Uuid, nullable=False, index=True)
    user_id = Column(Uuid, nullable=False, index=True)
    action = Column(String(100), nullable=False)  # chat, rag_query, agent_run, workflow_exec
    resource_type = Column(String(100), nullable=True)  # model, rag_doc, workflow
    resource_id = Column(String(200), nullable=True)
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="success")  # success | failure | rejected
    rejection_reason = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_ai_audit_tenant_ts", "tenant_id", "created_at"),
        Index("ix_ai_audit_trace", "trace_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "trace_id": self.trace_id,
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id),
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Export Base for migration discovery
__all__ = ["Base", "AIUsageLog", "AIAuditLog"]

"""AI API package."""

from services.ai.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    AgentRunRequest,
    AgentRunResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGIndexRequest,
    RAGIndexResponse,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    ModelConfig,
    QuotaConfig,
)
from services.ai.api.deps import get_current_user, get_current_tenant, require_ai_permission
from services.ai.api.websocket import websocket_manager

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ChatStreamChunk",
    "AgentRunRequest",
    "AgentRunResponse",
    "RAGQueryRequest",
    "RAGQueryResponse",
    "RAGIndexRequest",
    "RAGIndexResponse",
    "WorkflowExecuteRequest",
    "WorkflowExecuteResponse",
    "ModelConfig",
    "QuotaConfig",
    "get_current_user",
    "get_current_tenant",
    "require_ai_permission",
    "websocket_manager",
]

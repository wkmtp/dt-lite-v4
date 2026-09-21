"""Pydantic v2 request/response schemas for the AI API layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


# ===================================================================== Chat
class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    content: str


class ChatRequest(BaseModel):
    model: str = Field(..., description="Model identifier, e.g. gpt-4o, llama3.2")
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, ge=1, le=8192)
    stream: bool = Field(False, description="Set true for SSE streaming response")
    trace_id: Optional[str] = Field(None, description="Caller-supplied trace ID for audit")


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None


class ChatStreamChunk(BaseModel):
    """SSE chunk shape for streaming chat."""
    provider: str
    model: Optional[str] = None
    delta: dict[str, Any] = Field(default_factory=dict)
    finish_reason: Optional[str] = None
    usage: Optional[dict[str, int]] = None


# ===================================================================== Agent
class AgentRunRequest(BaseModel):
    agent_id: str = Field(..., description="Agent template ID")
    input_text: str = Field(..., min_length=1)
    context: Optional[dict[str, Any]] = None
    trace_id: Optional[str] = None


class AgentStep(BaseModel):
    step_index: int
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: Optional[Any] = None
    llm_model: Optional[str] = None
    tokens_used: int = 0


class AgentRunResponse(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None


# ===================================================================== RAG
class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    collection_id: Optional[str] = None
    top_k: int = Field(5, ge=1, le=20)
    trace_id: Optional[str] = None


class RAGDocument(BaseModel):
    doc_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGQueryResponse(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None


class RAGIndexRequest(BaseModel):
    collection_id: str
    documents: list[RAGDocument] = Field(..., min_length=1)
    trace_id: Optional[str] = None


class RAGIndexResponse(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None


# ===================================================================== Workflow
class WorkflowExecuteRequest(BaseModel):
    workflow_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None


class WorkflowStep(BaseModel):
    step_id: str
    step_type: str  # llm | tool | condition | branch
    status: str  # pending | running | success | failed
    input: dict[str, Any] = Field(default_factory=dict)
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class WorkflowExecuteResponse(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None


# ===================================================================== Admin
class ModelConfig(BaseModel):
    provider: str
    model: str
    base_url: Optional[str] = None
    weight: int = 1
    enabled: bool = True
    rpm: int = 60
    tpm: int = 100_000


class QuotaConfig(BaseModel):
    tenant_id: str
    rpm: int = 60
    tpm: int = 100_000
    daily_budget_tokens: int = 1_000_000
    monthly_budget_tokens: int = 20_000_000
    daily_budget_usd: float = 10.0
    monthly_budget_usd: float = 200.0


class TenantQuotaResponse(BaseModel):
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[dict[str, Any]] = None

"""
Request/Response Schemas for Workflow CRUD and Execution.

Pydantic v2 schemas for API request/response validation.
"""

from __future__ import annotations

from typing import Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class WorkflowCreateRequest(BaseModel):
    """Request schema for creating a workflow."""
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=1000)
    template: Optional[str] = Field(default=None, description="Template name to use")
    tags: list[str] = Field(default_factory=list)
    is_public: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class WorkflowUpdateRequest(BaseModel):
    """Request schema for updating a workflow."""
    name: Optional[str] = Field(default=None, max_length=256)
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[list[str]] = Field(default=None)
    is_public: Optional[bool] = Field(default=None)
    nodes: Optional[list[dict[str, Any]]] = Field(default=None)
    edges: Optional[list[dict[str, Any]]] = Field(default=None)
    variables: Optional[list[dict[str, Any]]] = Field(default=None)


class WorkflowNode(BaseModel):
    """Node schema for workflow definition."""
    node_id: str = Field(..., min_length=1, max_length=128)
    node_type: str = Field(..., description="Node type enum value")
    label: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=1000)
    enabled: bool = Field(default=True)
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    """Edge schema for workflow definition."""
    edge_id: str = Field(..., min_length=1, max_length=128)
    source_node_id: str = Field(..., min_length=1, max_length=128)
    target_node_id: str = Field(..., min_length=1, max_length=128)
    label: str = Field(default="", max_length=256)
    condition: Optional[str] = Field(default=None)


class WorkflowVariable(BaseModel):
    """Variable schema for workflow definition."""
    name: str = Field(..., min_length=1, max_length=128)
    scope: str = Field(default="workflow")
    description: str = Field(default="", max_length=500)
    type_hint: Optional[str] = Field(default=None)
    default_value: Any = Field(default=None)


class WorkflowResponse(BaseModel):
    """Response schema for workflow CRUD operations."""
    workflow_id: str
    tenant_id: str
    name: str
    description: str
    version: str
    status: WorkflowStatus
    tags: list[str]
    is_public: bool
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    variables: list[WorkflowVariable]
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    snapshot_count: int = 0
    last_execution_status: Optional[str] = None
    last_execution_at: Optional[str] = None


class WorkflowListResponse(BaseModel):
    """Response schema for listing workflows."""
    workflows: list[WorkflowResponse]
    total: int
    page: int
    page_size: int


class WorkflowExecuteRequest(BaseModel):
    """Request schema for executing a workflow."""
    workflow_id: str = Field(..., min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)
    execution_id: Optional[str] = Field(default=None)
    resume_from_checkpoint: bool = Field(default=False)


class WorkflowExecuteResponse(BaseModel):
    """Response schema for workflow execution."""
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    results: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    started_at: str
    completed_at: Optional[str] = None
    checkpoint_available: bool = False
    checkpoint_id: Optional[str] = None


class WorkflowCheckpointRequest(BaseModel):
    """Request schema for checkpoint operations."""
    workflow_id: str
    execution_id: str


class WorkflowCheckpointResponse(BaseModel):
    """Response schema for checkpoint operations."""
    checkpoint_id: str
    workflow_id: str
    execution_id: str
    timestamp: str
    status: str
    completed_nodes: list[str]
    step_index: int
    variables: dict[str, Any]


class WorkflowSnapshotRequest(BaseModel):
    """Request schema for snapshot operations."""
    workflow_id: str
    version: Optional[str] = Field(default=None)
    description: str = Field(default="")
    author: str = Field(default="")


class WorkflowSnapshotResponse(BaseModel):
    """Response schema for snapshot operations."""
    snapshot_id: str
    workflow_id: str
    version: str
    timestamp: str
    description: str
    author: str
    is_current: bool
    checksum: str
    changes: dict[str, Any]
    diff: Optional[dict[str, Any]] = None


class WorkflowValidationResponse(BaseModel):
    """Response schema for workflow validation."""
    valid: bool
    issues: list[dict[str, Any]]
    error_count: int
    warning_count: int
    summary: str


class WorkflowTemplateResponse(BaseModel):
    """Response schema for workflow templates."""
    template_id: str
    name: str
    description: str
    category: str
    node_count: int
    edge_count: int


class WorkflowMetricsResponse(BaseModel):
    """Response schema for workflow execution metrics."""
    workflow_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_seconds: float
    last_execution_status: str
    last_execution_at: Optional[str] = None

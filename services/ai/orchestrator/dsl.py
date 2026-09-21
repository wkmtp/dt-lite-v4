"""
Workflow DSL (Domain Specific Language) definitions.

Defines Pydantic models for workflow nodes, edges, and variable scopes.
Supports node types: LLM, Tool, HTTP, Condition, Parallel, HumanApproval, SubWorkflow.
"""

from __future__ import annotations

from typing import Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    """Supported workflow node types."""
    LLM = "llm"
    TOOL = "tool"
    HTTP = "http"
    CONDITION = "condition"
    PARALLEL = "parallel"
    HUMAN_APPROVAL = "human_approval"
    SUB_WORKFLOW = "sub_workflow"
    START = "start"
    END = "end"


class VariableScope(str, Enum):
    """Variable scope levels in workflow execution."""
    WORKFLOW = "workflow"      # Global to entire workflow
    NODE = "node"              # Scoped to single node
    SUB_WORKFLOW = "sub_workflow"  # Scoped to sub-workflow
    SESSION = "session"        # Persists across runs


class BaseNodeConfig(BaseModel):
    """Base configuration for all workflow nodes."""
    node_id: str = Field(..., min_length=1, max_length=128)
    node_type: NodeType
    label: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=1000)
    enabled: bool = Field(default=True)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class LLMNodeConfig(BaseNodeConfig):
    """Configuration for LLM nodes."""
    node_type: NodeType = NodeType.LLM
    model: str = Field(default="gpt-4o", description="LLM model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    system_prompt: str = Field(default="", description="System prompt for LLM")
    user_prompt: str = Field(default="", description="User prompt template")
    response_format: str = Field(default="text", description="text|json|schema")
    output_variable: Optional[str] = Field(default=None, description="Variable to store output")
    retries: int = Field(default=0, ge=0, le=5)
    timeout_seconds: int = Field(default=60, ge=1, le=300)


class ToolNodeConfig(BaseNodeConfig):
    """Configuration for tool execution nodes."""
    node_type: NodeType = NodeType.TOOL
    tool_name: str = Field(..., min_length=1, description="Tool identifier")
    tool_params: dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to tool")
    input_variable: Optional[str] = Field(default=None, description="Input variable name")
    output_variable: Optional[str] = Field(default=None, description="Variable to store output")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retries: int = Field(default=0, ge=0, le=5)


class HTTPNodeConfig(BaseNodeConfig):
    """Configuration for HTTP request nodes."""
    node_type: NodeType = NodeType.HTTP
    method: str = Field(default="GET", description="HTTP method")
    url: str = Field(..., description="Request URL")
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = Field(default=None, description="Request body")
    response_variable: Optional[str] = Field(default=None, description="Variable to store response")
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retries: int = Field(default=0, ge=0, le=5)
    success_status_codes: list[int] = Field(default=[200, 201, 202, 204])


class ConditionNodeConfig(BaseNodeConfig):
    """Configuration for conditional branching nodes."""
    node_type: NodeType = NodeType.CONDITION
    expression: str = Field(..., description="Conditional expression (Python-like)")
    true_node_id: Optional[str] = Field(default=None, description="Node ID to execute if true")
    false_node_id: Optional[str] = Field(default=None, description="Node ID to execute if false")


class ParallelNodeConfig(BaseNodeConfig):
    """Configuration for parallel execution nodes."""
    node_type: NodeType = NodeType.PARALLEL
    parallel_nodes: list[str] = Field(default_factory=list, description="Node IDs to run in parallel")
    fan_out_node_id: Optional[str] = Field(default=None, description="Node to fan out to")
    fan_in_node_id: Optional[str] = Field(default=None, description="Node to fan in from")
    timeout_seconds: int = Field(default=60, ge=1, le=300)


class HumanApprovalNodeConfig(BaseNodeConfig):
    """Configuration for human approval nodes."""
    node_type: NodeType = NodeType.HUMAN_APPROVAL
    approvers: list[str] = Field(default_factory=list, description="User IDs or roles")
    approval_type: str = Field(default="any", description="any|all")
    timeout_hours: int = Field(default=24, ge=1, le=720)
    notification_channel: str = Field(default="in_app", description="webhook|email|in_app")
    webhook_url: Optional[str] = Field(default=None)
    approve_action: str = Field(default="continue", description="continue|abort")
    comment_required: bool = Field(default=False)
    output_variable: Optional[str] = Field(default=None, description="Variable to store decision")


class SubWorkflowNodeConfig(BaseNodeConfig):
    """Configuration for sub-workflow nodes."""
    node_type: NodeType = NodeType.SUB_WORKFLOW
    workflow_id: str = Field(..., min_length=1, description="ID of sub-workflow")
    input_mapping: dict[str, str] = Field(default_factory=dict, description="Input variable mapping")
    output_mapping: dict[str, str] = Field(default_factory=dict, description="Output variable mapping")
    timeout_seconds: int = Field(default=300, ge=1, le=3600)


class StartNodeConfig(BaseNodeConfig):
    """Configuration for start nodes."""
    node_type: NodeType = NodeType.START
    inputs: list[str] = Field(default_factory=list, description="Required input variables")
    defaults: dict[str, Any] = Field(default_factory=dict)


class EndNodeConfig(BaseNodeConfig):
    """Configuration for end nodes."""
    node_type: NodeType = NodeType.END
    outputs: list[str] = Field(default_factory=list, description="Output variable names")
    save_to_history: bool = Field(default=True)


class Variable(BaseModel):
    """Represents a variable in workflow scope."""
    name: str = Field(..., min_length=1, max_length=128)
    scope: VariableScope = Field(default=VariableScope.NODE)
    description: str = Field(default="", max_length=500)
    type_hint: Optional[str] = Field(default=None, description="Expected type hint")
    default_value: Any = Field(default=None)


class EdgeConfig(BaseModel):
    """Represents a directed edge between nodes."""
    edge_id: str = Field(..., min_length=1, max_length=128)
    source_node_id: str = Field(..., min_length=1, max_length=128)
    target_node_id: str = Field(..., min_length=1, max_length=128)
    label: str = Field(default="", max_length=256)
    condition: Optional[str] = Field(default=None, description="Condition expression for edge")

    @field_validator("source_node_id")
    @classmethod
    def validate_source_not_self(cls, v: str, info) -> str:
        if "target_node_id" in info.data and v == info.data["target_node_id"]:
            raise ValueError("Self-loop edges are not allowed")
        return v


class WorkflowDSL(BaseModel):
    """
    Main workflow DSL definition.

    Represents a complete workflow with nodes, edges, variables, and metadata.
    """
    workflow_id: str = Field(..., min_length=1, max_length=128, description="Unique workflow identifier")
    tenant_id: str = Field(..., min_length=1, description="Tenant isolation ID")
    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(default="", max_length=1000)
    version: str = Field(default="1.0.0", description="Semantic version")
    tags: list[str] = Field(default_factory=list)
    is_public: bool = Field(default=False)

    nodes: list[BaseNodeConfig] = Field(default_factory=list)
    edges: list[EdgeConfig] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default="", description="ISO 8601 timestamp")
    updated_at: str = Field(default="", description="ISO 8601 timestamp")

    @property
    def node_map(self) -> dict[str, BaseNodeConfig]:
        """Get node dictionary by node_id."""
        return {node.node_id: node for node in self.nodes}

    @property
    def edge_map(self) -> dict[str, EdgeConfig]:
        """Get edge dictionary by edge_id."""
        return {edge.edge_id: edge for edge in self.edges}

    @field_validator("nodes")
    @classmethod
    def validate_node_ids_unique(cls, v: list[BaseNodeConfig]) -> list[BaseNodeConfig]:
        node_ids = [node.node_id for node in v]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate node IDs found")
        return v

    @field_validator("edges")
    @classmethod
    def validate_edges_connect_valid_nodes(cls, v: list[EdgeConfig], info) -> list[EdgeConfig]:
        if "nodes" not in info.data:
            return v
        valid_node_ids = {node.node_id for node in info.data["nodes"]}
        for edge in v:
            if edge.source_node_id not in valid_node_ids:
                raise ValueError(f"Edge references non-existent source node: {edge.source_node_id}")
            if edge.target_node_id not in valid_node_ids:
                raise ValueError(f"Edge references non-existent target node: {edge.target_node_id}")
        return v

    @field_validator("variables")
    @classmethod
    def validate_variable_names_unique(cls, v: list[Variable]) -> list[Variable]:
        var_names = [var.name for var in v]
        if len(var_names) != len(set(var_names)):
            raise ValueError("Duplicate variable names found")
        return v

    def get_start_nodes(self) -> list[BaseNodeConfig]:
        """Get all start nodes in the workflow."""
        return [node for node in self.nodes if node.node_type == NodeType.START]

    def get_end_nodes(self) -> list[BaseNodeConfig]:
        """Get all end nodes in the workflow."""
        return [node for node in self.nodes if node.node_type == NodeType.END]

    def get_nodes_by_type(self, node_type: NodeType) -> list[BaseNodeConfig]:
        """Get all nodes of a specific type."""
        return [node for node in self.nodes if node.node_type == node_type]

    def has_destructive_operations(self) -> bool:
        """Check if workflow contains destructive operations."""
        destructive_types = {NodeType.TOOL, NodeType.HTTP}
        for node in self.nodes:
            if node.node_type in destructive_types:
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert workflow to dictionary representation."""
        return self.model_dump(exclude={"node_map", "edge_map"})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowDSL":
        """Create WorkflowDSL from dictionary."""
        return cls(**data)

"""
DSL Static Validation for Workflow Definitions.

Validates node types, edge connectivity, cycle detection, required fields,
and business rules such as approval gates for destructive operations.
"""

from __future__ import annotations

from typing import Optional
from collections import deque
from pydantic import BaseModel
from .dsl import (
    WorkflowDSL, NodeType, EdgeConfig, BaseNodeConfig,
    LLMNodeConfig, HTTPNodeConfig, ToolNodeConfig,
    ConditionNodeConfig, HumanApprovalNodeConfig,
)


class ValidationIssue(BaseModel):
    """Represents a single validation issue."""
    issue_type: str  # error, warning, info
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    field: Optional[str] = None


class DSLValidator:
    """Static validator for WorkflowDSL definitions."""

    REQUIRED_START_NODES = 1
    REQUIRED_END_NODES = 1
    MAX_NODE_COUNT = 100
    MAX_EDGE_COUNT = 500
    MAX_DEPTH = 50

    VALID_NODE_TYPES = NodeType.__members__.values()

    @staticmethod
    def validate(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """
        Run all static validations on a workflow.

        Returns list of ValidationIssue objects.
        """
        issues: list[ValidationIssue] = []

        issues.extend(DSLValidator._validate_node_types(workflow))
        issues.extend(DSLValidator._validate_edge_connectivity(workflow))
        issues.extend(DSLValidator._validate_cycles(workflow))
        issues.extend(DSLValidator._validate_required_fields(workflow))
        issues.extend(DSLValidator._validate_node_count(workflow))
        issues.extend(DSLValidator._validate_edge_count(workflow))
        issues.extend(DSLValidator._validate_graph_structure(workflow))
        issues.extend(DSLValidator._validate_approval_requirements(workflow))
        issues.extend(DSLValidator._validate_variable_references(workflow))

        return issues

    @staticmethod
    def _validate_node_types(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate all node types are recognized."""
        issues = []
        for node in workflow.nodes:
            if node.node_type not in DSLValidator.VALID_NODE_TYPES:
                issues.append(ValidationIssue(
                    issue_type="error",
                    message=f"Unknown node type: {node.node_type}",
                    node_id=node.node_id,
                    field="node_type"
                ))
        return issues

    @staticmethod
    def _validate_edge_connectivity(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate all edges connect to existing nodes."""
        issues = []
        node_ids = {node.node_id for node in workflow.nodes}

        for edge in workflow.edges:
            if edge.source_node_id not in node_ids:
                issues.append(ValidationIssue(
                    issue_type="error",
                    message=f"Edge references non-existent source node: {edge.source_node_id}",
                    edge_id=edge.edge_id,
                    field="source_node_id"
                ))
            if edge.target_node_id not in node_ids:
                issues.append(ValidationIssue(
                    issue_type="error",
                    message=f"Edge references non-existent target node: {edge.target_node_id}",
                    edge_id=edge.edge_id,
                    field="target_node_id"
                ))

        return issues

    @staticmethod
    def _validate_cycles(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Detect cycles in workflow graph using DFS."""
        issues = []
        if len(workflow.nodes) == 0:
            return issues

        graph: dict[str, list[str]] = {}
        for node in workflow.nodes:
            graph[node.node_id] = []
        for edge in workflow.edges:
            graph[edge.source_node_id].append(edge.target_node_id)

        # Detect cycles using DFS with coloring
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in graph}
        cycle_edges: list[tuple[str, str]] = []

        def dfs(node_id: str, path: list[str]) -> None:
            color[node_id] = GRAY
            for neighbor in graph.get(node_id, []):
                if color[neighbor] == GRAY:
                    cycle_edges.append((node_id, neighbor))
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path + [neighbor])
            color[node_id] = BLACK

        for node_id in graph:
            if color[node_id] == WHITE:
                dfs(node_id, [node_id])

        for src, dst in cycle_edges:
            issues.append(ValidationIssue(
                issue_type="error",
                message=f"Cycle detected: {src} -> {dst}",
                edge_id=None
            ))

        return issues

    @staticmethod
    def _validate_required_fields(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate required fields for each node type."""
        issues = []

        start_nodes = workflow.get_start_nodes()
        end_nodes = workflow.get_end_nodes()

        if len(start_nodes) == 0:
            issues.append(ValidationIssue(
                issue_type="error",
                message="Workflow must have at least one START node"
            ))
        if len(end_nodes) == 0:
            issues.append(ValidationIssue(
                issue_type="error",
                message="Workflow must have at least one END node"
            ))

        for node in workflow.nodes:
            if isinstance(node, LLMNodeConfig):
                if not node.user_prompt and not node.system_prompt:
                    issues.append(ValidationIssue(
                        issue_type="warning",
                        message="LLM node has no prompt defined",
                        node_id=node.node_id
                    ))
            elif isinstance(node, HTTPNodeConfig):
                if not node.url:
                    issues.append(ValidationIssue(
                        issue_type="error",
                        message="HTTP node missing URL",
                        node_id=node.node_id,
                        field="url"
                    ))
            elif isinstance(node, ToolNodeConfig):
                if not node.tool_name:
                    issues.append(ValidationIssue(
                        issue_type="error",
                        message="Tool node missing tool_name",
                        node_id=node.node_id,
                        field="tool_name"
                    ))
            elif isinstance(node, ConditionNodeConfig):
                if not node.expression:
                    issues.append(ValidationIssue(
                        issue_type="error",
                        message="Condition node missing expression",
                        node_id=node.node_id,
                        field="expression"
                    ))
            elif isinstance(node, HumanApprovalNodeConfig):
                if not node.approvers:
                    issues.append(ValidationIssue(
                        issue_type="warning",
                        message="HumanApproval node has no approvers defined",
                        node_id=node.node_id
                    ))

        return issues

    @staticmethod
    def _validate_node_count(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate node count limits."""
        issues = []
        if len(workflow.nodes) > DSLValidator.MAX_NODE_COUNT:
            issues.append(ValidationIssue(
                issue_type="error",
                message=f"Too many nodes: {len(workflow.nodes)} (max: {DSLValidator.MAX_NODE_COUNT})"
            ))
        return issues

    @staticmethod
    def _validate_edge_count(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate edge count limits."""
        issues = []
        if len(workflow.edges) > DSLValidator.MAX_EDGE_COUNT:
            issues.append(ValidationIssue(
                issue_type="error",
                message=f"Too many edges: {len(workflow.edges)} (max: {DSLValidator.MAX_EDGE_COUNT})"
            ))
        return issues

    @staticmethod
    def _validate_graph_structure(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate graph structure: reachability from start to end."""
        issues = []
        if len(workflow.nodes) == 0:
            return issues

        graph: dict[str, list[str]] = {node.node_id: [] for node in workflow.nodes}
        for edge in workflow.edges:
            graph[edge.source_node_id].append(edge.target_node_id)

        start_nodes = {node.node_id for node in workflow.get_start_nodes()}
        end_nodes = {node.node_id for node in workflow.get_end_nodes()}

        # Check reachability from each start node
        for start_id in start_nodes:
            visited = set()
            queue = deque([start_id])
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                for neighbor in graph.get(current, []):
                    queue.append(neighbor)

            unreachable_ends = end_nodes - visited
            if unreachable_ends:
                issues.append(ValidationIssue(
                    issue_type="warning",
                    message=f"End nodes unreachable from start {start_id}: {unreachable_ends}",
                    node_id=start_id
                ))

        # Check for unreachable nodes
        all_reachable = set()
        for start_id in start_nodes:
            queue = deque([start_id])
            while queue:
                current = queue.popleft()
                if current in all_reachable:
                    continue
                all_reachable.add(current)
                for neighbor in graph.get(current, []):
                    queue.append(neighbor)

        unreachable_nodes = {node.node_id for node in workflow.nodes} - all_reachable
        if unreachable_nodes:
            issues.append(ValidationIssue(
                issue_type="warning",
                message=f"Unreachable nodes: {unreachable_nodes}"
            ))

        return issues

    @staticmethod
    def _validate_approval_requirements(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate R7: destructive operations require approval gates."""
        issues = []

        if not workflow.has_destructive_operations():
            return issues

        # Check if there's a HumanApproval node before any destructive path
        destructive_node_ids = set()
        for node in workflow.nodes:
            if node.node_type in {NodeType.TOOL, NodeType.HTTP}:
                destructive_node_ids.add(node.node_id)

        if not destructive_node_ids:
            return issues

        # Find approval nodes
        approval_nodes = {node.node_id for node in workflow.nodes
                         if node.node_type == NodeType.HUMAN_APPROVAL}

        # Check if approval nodes can reach all destructive nodes
        graph: dict[str, list[str]] = {}
        for node in workflow.nodes:
            graph[node.node_id] = []
        for edge in workflow.edges:
            graph[edge.source_node_id].append(edge.target_node_id)

        for destr_node_id in destructive_node_ids:
            # BFS from approval nodes to check if any can reach destructive node
            can_reach = False
            for approval_id in approval_nodes:
                visited = set()
                queue = deque([approval_id])
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    visited.add(current)
                    if current == destr_node_id:
                        can_reach = True
                        break
                    for neighbor in graph.get(current, []):
                        queue.append(neighbor)
                if can_reach:
                    break

            if not can_reach and approval_nodes:
                issues.append(ValidationIssue(
                    issue_type="warning",
                    message=f"Destructive node {destr_node_id} may not be protected by approval",
                    node_id=destr_node_id
                ))
            elif not approval_nodes:
                issues.append(ValidationIssue(
                    issue_type="error",
                    message=f"Workflow has destructive operations but no HumanApproval node (R7 violation)",
                    node_id=destr_node_id
                ))

        return issues

    @staticmethod
    def _validate_variable_references(workflow: WorkflowDSL) -> list[ValidationIssue]:
        """Validate variable references in nodes."""
        issues = []
        defined_vars = {var.name for var in workflow.variables}

        for node in workflow.nodes:
            # Check input/output variable references
            if hasattr(node, "input_variable") and node.input_variable:
                if node.input_variable not in defined_vars and node.input_variable != "":
                    issues.append(ValidationIssue(
                        issue_type="warning",
                        message=f"Node {node.node_id} references undefined variable: {node.input_variable}",
                        node_id=node.node_id,
                        field="input_variable"
                    ))
            if hasattr(node, "output_variable") and node.output_variable:
                if node.output_variable not in defined_vars and node.output_variable != "":
                    issues.append(ValidationIssue(
                        issue_type="warning",
                        message=f"Node {node.node_id} references undefined variable: {node.output_variable}",
                        node_id=node.node_id,
                        field="output_variable"
                    ))

        return issues


def validate_workflow(workflow: WorkflowDSL) -> dict:
    """
    Validate a workflow and return results.

    Returns dict with:
        - valid: bool
        - issues: list of ValidationIssue
        - error_count: int
        - warning_count: int
    """
    issues = DSLValidator.validate(workflow)
    errors = [i for i in issues if i.issue_type == "error"]
    warnings = [i for i in issues if i.issue_type == "warning"]

    return {
        "valid": len(errors) == 0,
        "issues": issues,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "summary": f"{len(errors)} errors, {len(warnings)} warnings"
    }

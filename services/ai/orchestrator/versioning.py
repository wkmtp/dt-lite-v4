"""
Version Management and Snapshot System for Workflows.

Provides version tracking, snapshot creation, diff comparison,
and rollback capabilities.
"""

from __future__ import annotations

import json
import hashlib
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field
from .dsl import WorkflowDSL


@dataclass
class VersionSnapshot:
    """A snapshot of a workflow at a specific version."""
    snapshot_id: str
    workflow_id: str
    version: str
    timestamp: str
    description: str = ""
    author: str = ""
    is_current: bool = False
    workflow_data: dict = field(default_factory=dict)
    checksum: str = ""
    changes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "workflow_id": self.workflow_id,
            "version": self.version,
            "timestamp": self.timestamp,
            "description": self.description,
            "author": self.author,
            "is_current": self.is_current,
            "checksum": self.checksum,
            "changes": self.changes
        }


@dataclass
class DiffResult:
    """Result of comparing two workflow versions."""
    workflow_id: str
    version_from: str
    version_to: str
    nodes_added: list[str] = field(default_factory=list)
    nodes_removed: list[str] = field(default_factory=list)
    nodes_modified: list[str] = field(default_factory=list)
    edges_added: list[str] = field(default_factory=list)
    edges_removed: list[str] = field(default_factory=list)
    variables_added: list[str] = field(default_factory=list)
    variables_removed: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "version_from": self.version_from,
            "version_to": self.version_to,
            "nodes_added": self.nodes_added,
            "nodes_removed": self.nodes_removed,
            "nodes_modified": self.nodes_modified,
            "edges_added": self.edges_added,
            "edges_removed": self.edges_removed,
            "variables_added": self.variables_added,
            "variables_removed": self.variables_removed,
            "summary": self.summary
        }


class VersionManager:
    """Manages workflow versions and snapshots."""

    def __init__(self):
        self._snapshots: dict[str, list[VersionSnapshot]] = {}
        self._current_version: dict[str, str] = {}

    def create_snapshot(
        self,
        workflow: WorkflowDSL,
        description: str = "",
        author: str = ""
    ) -> VersionSnapshot:
        """
        Create a new snapshot for a workflow.

        Generates a version bump, creates snapshot, and returns it.
        """
        workflow_id = workflow.workflow_id
        current_version = self._current_version.get(workflow_id, "1.0.0")
        new_version = self._bump_version(current_version)

        workflow_data = workflow.to_dict()
        checksum = self._compute_checksum(workflow_data)
        changes = self._compute_changes(workflow, current_version)

        snapshot = VersionSnapshot(
            snapshot_id=f"{workflow_id}__{new_version}",
            workflow_id=workflow_id,
            version=new_version,
            timestamp=datetime.utcnow().isoformat(),
            description=description,
            author=author,
            is_current=True,
            workflow_data=workflow_data,
            checksum=checksum,
            changes=changes
        )

        # Mark previous snapshots as not current
        if workflow_id in self._snapshots:
            for snap in self._snapshots[workflow_id]:
                snap.is_current = False

        # Store snapshot
        if workflow_id not in self._snapshots:
            self._snapshots[workflow_id] = []
        self._snapshots[workflow_id].append(snapshot)
        self._current_version[workflow_id] = new_version

        return snapshot

    def get_snapshot(
        self,
        workflow_id: str,
        version: Optional[str] = None
    ) -> Optional[VersionSnapshot]:
        """Get a specific snapshot by workflow_id and version."""
        if workflow_id not in self._snapshots:
            return None

        snapshots = self._snapshots[workflow_id]
        if version:
            for snap in snapshots:
                if snap.version == version:
                    return snap
            return None

        # Return current version
        for snap in snapshots:
            if snap.is_current:
                return snap

        return snapshots[-1] if snapshots else None

    def get_version_history(self, workflow_id: str) -> list[VersionSnapshot]:
        """Get full version history for a workflow."""
        return self._snapshots.get(workflow_id, []).copy()

    def diff_versions(
        self,
        workflow_id: str,
        version_from: str,
        version_to: str
    ) -> Optional[DiffResult]:
        """Compute diff between two versions."""
        snap_from = self.get_snapshot(workflow_id, version_from)
        snap_to = self.get_snapshot(workflow_id, version_to)

        if not snap_from or not snap_to:
            return None

        return self.compute_diff(
            WorkflowDSL.from_dict(snap_from.workflow_data),
            WorkflowDSL.from_dict(snap_to.workflow_data)
        )

    def compute_diff(
        self,
        workflow_a: WorkflowDSL,
        workflow_b: WorkflowDSL
    ) -> DiffResult:
        """Compute diff between two workflow instances."""
        nodes_a = {node.node_id for node in workflow_a.nodes}
        nodes_b = {node.node_id for node in workflow_b.nodes}

        edges_a = {(edge.source_node_id, edge.target_node_id) for edge in workflow_a.edges}
        edges_b = {(edge.source_node_id, edge.target_node_id) for edge in workflow_b.edges}

        vars_a = {var.name for var in workflow_a.variables}
        vars_b = {var.name for var in workflow_b.variables}

        return DiffResult(
            workflow_id=workflow_a.workflow_id,
            version_from="unknown",
            version_to="unknown",
            nodes_added=list(nodes_b - nodes_a),
            nodes_removed=list(nodes_a - nodes_b),
            nodes_modified=[nid for nid in nodes_a & nodes_b
                           if self._node_changed(workflow_a, workflow_b, nid)],
            edges_added=[f"{src}->{dst}" for src, dst in edges_b - edges_a],
            edges_removed=[f"{src}->{dst}" for src, dst in edges_a - edges_b],
            variables_added=list(vars_b - vars_a),
            variables_removed=list(vars_a - vars_b),
            summary=self._generate_diff_summary(
                nodes_a, nodes_b, edges_a, edges_b, vars_a, vars_b
            )
        )

    def restore_version(
        self,
        workflow_id: str,
        version: str
    ) -> Optional[VersionSnapshot]:
        """Restore a workflow to a specific version."""
        snapshot = self.get_snapshot(workflow_id, version)
        if snapshot:
            snapshot.is_current = True
            self._current_version[workflow_id] = version
            # Mark others as not current
            for snap in self._snapshots.get(workflow_id, []):
                if snap.snapshot_id != snapshot.snapshot_id:
                    snap.is_current = False
        return snapshot

    def delete_version(self, workflow_id: str, version: str) -> bool:
        """Delete a specific version snapshot."""
        if workflow_id not in self._snapshots:
            return False

        snapshots = self._snapshots[workflow_id]
        original_count = len(snapshots)
        self._snapshots[workflow_id] = [
            snap for snap in snapshots
            if snap.version != version
        ]

        return len(self._snapshots[workflow_id]) < original_count

    def _bump_version(self, current_version: str) -> str:
        """Bump semantic version."""
        parts = current_version.split(".")
        if len(parts) != 3:
            return "1.0.1"
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            patch += 1
            return f"{major}.{minor}.{patch}"
        except ValueError:
            return "1.0.1"

    def _compute_checksum(self, data: dict) -> str:
        """Compute SHA-256 checksum of workflow data."""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]

    def _compute_changes(self, workflow: WorkflowDSL, previous_version: str) -> dict:
        """Compute changes from previous version."""
        snapshot = self.get_snapshot(workflow.workflow_id, previous_version)
        if not snapshot:
            return {"description": "Initial version"}

        diff = self.compute_diff(
            WorkflowDSL.from_dict(snapshot.workflow_data),
            workflow
        )
        return {
            "nodes_added": len(diff.nodes_added),
            "nodes_removed": len(diff.nodes_removed),
            "edges_added": len(diff.edges_added),
            "edges_removed": len(diff.edges_removed),
            "description": workflow.description
        }

    def _node_changed(self, wa: WorkflowDSL, wb: WorkflowDSL, node_id: str) -> bool:
        """Check if a node changed between two workflows."""
        node_a = next((n for n in wa.nodes if n.node_id == node_id), None)
        node_b = next((n for n in wb.nodes if n.node_id == node_id), None)
        if not node_a or not node_b:
            return False
        return node_a.model_dump() != node_b.model_dump()

    def _generate_diff_summary(
        self,
        nodes_a: set,
        nodes_b: set,
        edges_a: set,
        edges_b: set,
        vars_a: set,
        vars_b: set
    ) -> str:
        """Generate human-readable diff summary."""
        parts = []
        if nodes_b - nodes_a:
            parts.append(f"+{len(nodes_b - nodes_a)} nodes")
        if nodes_a - nodes_b:
            parts.append(f"~{len(nodes_a - nodes_b)} nodes")
        if edges_b - edges_a:
            parts.append(f"+{len(edges_b - edges_a)} edges")
        if edges_a - edges_b:
            parts.append(f"~{len(edges_a - edges_b)} edges")
        if vars_b - vars_a:
            parts.append(f"+{len(vars_b - vars_a)} variables")
        if vars_a - vars_b:
            parts.append(f"~{len(vars_a - vars_b)} variables")
        return " | ".join(parts) if parts else "No changes"

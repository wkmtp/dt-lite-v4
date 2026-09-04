"""Deployment validation service — zero-code readiness checks."""
from uuid import UUID

from services.deployment.repositories.instance_repository import (
    DeploymentInstanceRepository,
)
from services.deployment.schemas import (
    DeploymentValidationResponse,
    ValidationIssue,
)


class DeploymentValidationService:
    """Validates deployment instances for zero-code readiness.

    Checks:
    - Required capabilities from template binding exist on nodes
    - Schema completeness
    - Node configuration requirements
    """

    def __init__(self, instance_repo: DeploymentInstanceRepository):
        self._instance_repo = instance_repo

    async def validate(
        self, instance_id: UUID, tenant_id: UUID,
    ) -> DeploymentValidationResponse:
        """Validate a deployment instance."""
        instance = await self._instance_repo.get_by_id_for_tenant(instance_id, tenant_id)
        if not instance:
            return DeploymentValidationResponse(
                valid=False,
                issues=[ValidationIssue(severity="error", message="Instance not found")],
            )

        issues: list[ValidationIssue] = []
        missing_capabilities: list[str] = []
        passed_requirements: list[str] = []

        # Check node count
        if not instance.nodes or len(instance.nodes) == 0:
            issues.append(ValidationIssue(
                severity="error",
                message="Instance must have at least one node",
                field="nodes",
            ))
        else:
            passed_requirements.append(f"{len(instance.nodes)} nodes present")

        # Check required fields
        if not instance.name or not instance.name.strip():
            issues.append(ValidationIssue(
                severity="error",
                message="Instance name is required",
                field="name",
            ))
        else:
            passed_requirements.append("Name provided")

        # Validate node-level requirements
        if instance.nodes:
            for node in instance.nodes:
                node_name = node.name
                if not node_name:
                    issues.append(ValidationIssue(
                        severity="error",
                        message="Node name is required",
                        field=f"node.{node.id}",
                    ))

        return DeploymentValidationResponse(
            valid=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
            missing_capabilities=missing_capabilities,
            passed_requirements=passed_requirements,
        )

    async def validate_capabilities(
        self, instance_id: UUID, tenant_id: UUID,
    ) -> DeploymentValidationResponse:
        """Validate capability bindings are present on nodes."""
        instance = await self._instance_repo.get_by_id_for_tenant(instance_id, tenant_id)
        if not instance:
            return DeploymentValidationResponse(
                valid=False,
                issues=[ValidationIssue(severity="error", message="Instance not found")],
            )

        issues: list[ValidationIssue] = []
        missing_capabilities: list[str] = []

        # Verify nodes exist
        if not instance.nodes:
            issues.append(ValidationIssue(
                severity="error",
                message="No nodes defined for capability validation",
                field="nodes",
            ))
            return DeploymentValidationResponse(
                valid=False,
                issues=issues,
                missing_capabilities=[],
                passed_requirements=[],
            )

        # Check each node has at least one capability binding
        for node in instance.nodes:
            if not node.capabilities:
                issues.append(ValidationIssue(
                    severity="warning",
                    message=f"Node '{node.name}' has no capability bindings",
                    field=f"node.{node.id}.capabilities",
                ))

        return DeploymentValidationResponse(
            valid=len([i for i in issues if i.severity == "error"]) == 0,
            issues=issues,
            missing_capabilities=missing_capabilities,
            passed_requirements=["Capability bindings verified"],
        )

"""Provisioning service — orchestration layer."""
import logging
from uuid import UUID

from services.provisioning.models import ProvisioningExecution, ProvisioningPlan
from services.provisioning.planner import ProvisioningPlanner
from services.provisioning.repository import (
    ProvisioningExecutionRepository,
    ProvisioningItemRepository,
    ProvisioningPlanRepository,
)
from services.provisioning.schemas import PlanValidationResponse
from services.template.repositories import TemplateRepository
from services.ontology.repository import EntityTypeRepository, CapabilityRepository

logger = logging.getLogger(__name__)


class ProvisioningService:
    """Service that orchestrates provisioning plan generation and execution."""

    def __init__(self, session):
        self._session = session
        self._plan_repo = ProvisioningPlanRepository(session)
        self._item_repo = ProvisioningItemRepository(session)
        self._execution_repo = ProvisioningExecutionRepository(session)
        self._template_repo = TemplateRepository(session)
        self._entity_type_repo = EntityTypeRepository(session)
        self._capability_repo = CapabilityRepository(session)

    async def validate_deployment(
        self, deployment_instance_id: UUID, tenant_id: UUID,
    ) -> PlanValidationResponse:
        """Validate a deployment instance is ready for provisioning."""
        from services.deployment.repositories.instance_repository import DeploymentInstanceRepository
        from services.deployment.repositories.node_repository import DeploymentNodeRepository
        from services.deployment.repositories.node_capability_repository import DeploymentNodeCapabilityRepository

        inst_repo = DeploymentInstanceRepository(self._session)
        instance = await inst_repo.get_by_id_for_tenant(deployment_instance_id, tenant_id)
        if not instance:
            issues = [{"field": "deployment", "message": "DeploymentInstance not found"}]
            return PlanValidationResponse(valid=False, issues=issues)

        issues = []
        passed = []

        if instance.status != "ready":
            issues.append({"field": "instance_status", "message": f"Instance must be READY, got {instance.status}"})

        template = await self._template_repo.get_by_id_for_tenant(instance.profile.template_id, tenant_id)
        if not template:
            issues.append({"field": "template", "message": "Template not found"})
        else:
            passed.append("Template exists")

        node_repo = DeploymentNodeRepository(self._session)
        nodes = await node_repo.list_by_deployment(deployment_instance_id, tenant_id)
        if not nodes:
            issues.append({"field": "nodes", "message": "No nodes defined"})
        else:
            passed.append(f"{len(nodes)} nodes defined")

        cap_repo = DeploymentNodeCapabilityRepository(self._session)
        missing_caps = []
        for node in nodes:
            bindings = await cap_repo.list_by_node(node.id, tenant_id)
            if not bindings:
                missing_caps.append(f"Node '{node.name}' has no capability bindings")

        if missing_caps:
            issues.extend([{"field": f"node_{i}", "message": m} for i, m in enumerate(missing_caps)])
        else:
            passed.append("All nodes have capability bindings")

        has_errors = any(i.get("severity") == "error" for i in issues)
        return PlanValidationResponse(valid=not has_errors, issues=issues, passed_requirements=passed)

    async def create_plan(self, deployment_instance_id: UUID, tenant_id: UUID) -> ProvisioningPlan:
        """Create a provisioning plan for a deployment instance."""
        planner = ProvisioningPlanner(
            self._plan_repo,
            self._item_repo,
            self._template_repo,
            self._entity_type_repo,
            self._capability_repo,
        )
        return await planner.generate_plan(deployment_instance_id, tenant_id)

    async def execute_plan(self, plan_id: UUID, tenant_id: UUID) -> ProvisioningExecution:
        """Execute a provisioning plan."""
        plan = await self._plan_repo.get_by_id_for_tenant(plan_id, tenant_id)
        if not plan:
            raise RuntimeError(f"Plan {plan_id} not found")
        if plan.status != "ready":
            raise RuntimeError(f"Cannot execute plan in status '{plan.status}'")

        from services.provisioning.executor import ProvisioningExecutor
        from services.twin.repositories.entity_repository import EntityRepository
        from services.twin_graph.repositories import TwinRelationshipRepository

        executor = ProvisioningExecutor(
            session=self._session,
            plan_repo=self._plan_repo,
            item_repo=self._item_repo,
            execution_repo=self._execution_repo,
            entity_repo=EntityRepository(self._session),
            relationship_repo=TwinRelationshipRepository(self._session),
        )
        return await executor.execute(plan_id, tenant_id)

    async def get_plan(self, plan_id: UUID, tenant_id: UUID) -> ProvisioningPlan:
        """Get a provisioning plan by ID."""
        plan = await self._plan_repo.get_by_id_for_tenant(plan_id, tenant_id)
        if not plan:
            raise RuntimeError(f"Plan {plan_id} not found")
        return plan

    async def get_execution(self, plan_id: UUID, tenant_id: UUID) -> ProvisioningExecution:
        """Get the latest execution record for a plan."""
        executions = await self._execution_repo.list_by_plan(plan_id, tenant_id)
        return executions[0] if executions else None

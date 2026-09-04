"""ProvisioningPlanner — Generate provisioning plans from deployment instances."""
import logging
from uuid import UUID

from services.deployment.models import DeploymentNode
from services.deployment.repositories.instance_repository import DeploymentInstanceRepository
from services.provisioning.exceptions import MissingTemplateError
from services.provisioning.models import ProvisioningItem, ProvisioningPlan
from services.provisioning.repository import ProvisioningItemRepository, ProvisioningPlanRepository
from services.template.models import TwinTemplate
from services.template.repositories import TemplateRepository

logger = logging.getLogger(__name__)


class ProvisioningPlanner:
    """Generates provisioning plans from deployment instances.

    Reads:
    - DeploymentInstance nodes
    - Template for relationship definitions

    Produces:
    - ProvisioningPlan with CREATE_ENTITY and CREATE_RELATIONSHIP items
    """

    def __init__(
        self,
        plan_repo: ProvisioningPlanRepository,
        item_repo: ProvisioningItemRepository,
        template_repo: TemplateRepository,
    ):
        self._plan_repo = plan_repo
        self._item_repo = item_repo
        self._template_repo = template_repo

    async def generate_plan(
        self,
        deployment_instance_id: UUID,
        tenant_id: UUID,
    ) -> ProvisioningPlan:
        """Generate a provisioning plan for a deployment instance."""
        # Check idempotency
        existing = await self._plan_repo.get_by_deployment_id(deployment_instance_id, tenant_id)
        if existing:
            if existing.status == "completed":
                return existing
            raise RuntimeError(f"Existing plan in status '{existing.status}' cannot be regenerated")

        # Fetch deployment instance
        instance_repo = DeploymentInstanceRepository(self._plan_repo.session)
        instance = await instance_repo.get_by_id_for_tenant(deployment_instance_id, tenant_id)
        if instance is None:
            raise RuntimeError(f"DeploymentInstance {deployment_instance_id} not found")

        # Fetch template
        template = await self._template_repo.get_by_id_for_tenant(instance.profile.template_id, tenant_id)
        if template is None:
            raise MissingTemplateError(instance.profile.template_id)

        # Create plan
        plan = ProvisioningPlan(
            tenant_id=tenant_id,
            deployment_instance_id=deployment_instance_id,
            status="draft",
            total_items=0,
            completed_items=0,
        )
        await self._plan_repo.session.add(plan)
        await self._plan_repo.session.flush()

        items: list[ProvisioningItem] = []
        nodes = instance.nodes or []

        # Phase 1: CREATE_ENTITY for each node
        for node in nodes:
            external_id = self._build_external_id(node)
            item = ProvisioningItem(
                tenant_id=tenant_id,
                plan_id=plan.id,
                template_id=template.id,
                entity_type_id=node.entity_type_id,
                external_id=external_id,
                action="CREATE_ENTITY",
                status="pending",
            )
            items.append(item)

        # Phase 2: CREATE_RELATIONSHIP for node pairs
        for i, source_node in enumerate(nodes):
            for target_node in nodes[i + 1:]:
                ext_source = self._build_external_id(source_node)
                ext_target = self._build_external_id(target_node)
                item = ProvisioningItem(
                    tenant_id=tenant_id,
                    plan_id=plan.id,
                    template_id=template.id,
                    external_id=f"rel-{ext_source}-{ext_target}",
                    action="CREATE_RELATIONSHIP",
                    source_twin_id=None,  # Will be resolved during execution
                    target_twin_id=None,
                    status="pending",
                )
                items.append(item)

        # Persist items
        await self._plan_repo.session.add_all(items)
        await self._plan_repo.session.flush()

        plan.total_items = len(items)
        plan.status = "ready"
        await self._plan_repo.session.flush()

        logger.info("Generated plan %s with %d items for deployment %s",
                     plan.id, len(items), deployment_instance_id)
        return plan

    def _build_external_id(self, node: DeploymentNode) -> str:
        """Build stable external ID for idempotency."""
        safe_name = node.name.replace(" ", "_").replace("/", "_")
        return f"{node.node_type}_{safe_name}_{str(node.id)[:8]}"

    def _resolve_relationship_type(self, source: DeploymentNode, target: DeploymentNode,
                                    template: TwinTemplate) -> str:
        """Resolve relationship type between two nodes based on template."""
        if template.relationships:
            return template.relationships[0].relationship_type
        return "contains"  # Default

"""ProvisioningExecutor — Execute provisioning plans to create TwinEntities."""
import logging
from uuid import UUID

from services.core.repositories.base import AsyncSession
from services.provisioning.models import ProvisioningExecution, ProvisioningItem
from services.provisioning.repository import (
    ProvisioningExecutionRepository,
    ProvisioningItemRepository,
    ProvisioningPlanRepository,
)
from services.twin.models.entity import PersistentTwinEntity
from services.twin.repositories.entity_repository import EntityRepository
from services.twin_graph.models import TwinRelationship
from services.twin_graph.repositories import TwinRelationshipRepository

logger = logging.getLogger(__name__)


class ProvisioningExecutor:
    """Executes provisioning plans by creating TwinEntities and relationships.

    This service bridges Deployment → Twin, without touching device/protocol/telemetry layers.
    """

    def __init__(
        self,
        session: AsyncSession,
        plan_repo: ProvisioningPlanRepository,
        item_repo: ProvisioningItemRepository,
        execution_repo: ProvisioningExecutionRepository,
        entity_repo: EntityRepository,
        relationship_repo: TwinRelationshipRepository,
    ):
        self._session = session
        self._plan_repo = plan_repo
        self._item_repo = item_repo
        self._execution_repo = execution_repo
        self._entity_repo = entity_repo
        self._relationship_repo = relationship_repo

    async def execute(self, plan_id: UUID, tenant_id: UUID) -> ProvisioningExecution:
        """Execute a provisioning plan.

        1. Create execution record
        2. Process each item (CREATE_ENTITY or CREATE_RELATIONSHIP)
        3. Update plan status based on results
        4. Mark execution complete/fail

        Returns:
            ProvisioningExecution record with final status
        """
        plan = await self._plan_repo.get_by_id_for_tenant(plan_id, tenant_id)
        if not plan:
            raise RuntimeError(f"Plan {plan_id} not found for tenant {tenant_id}")
        if plan.status != "ready":
            raise RuntimeError(f"Cannot execute plan in status '{plan.status}'")

        # Create execution record
        execution = ProvisioningExecution(
            tenant_id=tenant_id,
            plan_id=plan_id,
            status="started",
            items_completed=0,
            items_failed=0,
        )
        await self._session.add(execution)
        await self._session.flush()

        items = await self._item_repo.list_by_plan(plan_id, tenant_id)
        completed = 0
        failed = 0

        try:
            for item in items:
                try:
                    if item.action == "CREATE_ENTITY":
                        twin_id = await self._execute_create_entity(item, tenant_id)
                        item.created_twin_id = twin_id
                        item.status = "completed"
                    elif item.action == "CREATE_RELATIONSHIP":
                        await self._execute_create_relationship(item, tenant_id)
                        item.status = "completed"
                    else:
                        item.status = "failed"
                        item.error_message = f"Unknown action: {item.action}"
                        failed += 1

                    completed += 1
                    execution.items_completed = completed
                    execution.items_failed = failed

                except Exception as e:
                    logger.warning("Item %s failed: %s", item.id, str(e))
                    item.status = "failed"
                    item.error_message = str(e)
                    failed += 1

            # Update plan and execution
            plan.completed_items = completed
            plan.total_items = len(items)
            execution.items_completed = completed
            execution.items_failed = failed

            if failed == 0:
                plan.status = "completed"
                execution.status = "completed"
            else:
                plan.status = "failed"
                execution.status = "failed"
                plan.error_summary = f"{failed}/{len(items)} items failed"
                execution.error_message = plan.error_summary

        except Exception as e:
            plan.status = "failed"
            execution.status = "failed"
            execution.error_message = str(e)
            logger.error("Plan execution failed: %s", str(e))

        await self._session.commit()
        return execution

    async def _execute_create_entity(
        self, item: ProvisioningItem, tenant_id: UUID
    ) -> UUID:
        """Create a PersistentTwinEntity from a provisioning item."""
        # Idempotency check: entity already created?
        existing = await self._entity_repo.get_by_external_id(item.external_id, tenant_id)
        if existing:
            item.created_twin_id = existing.id
            return existing.id

        # Create PersistentTwinEntity
        entity = PersistentTwinEntity(
            tenant_id=tenant_id,
            definition_id=item.template_id or None,
            external_id=item.external_id,
            name=item.external_id.replace("_", " ").title(),
            meta_data={
                "node_id": str(item.plan_id),
                "source_plan": str(item.plan_id),
            },
        )

        created_entity = await self._entity_repo.create(entity)
        item.created_twin_id = created_entity.id
        logger.info("Created TwinEntity %s for item %s", created_entity.id, item.id)
        return created_entity.id

    async def _execute_create_relationship(
        self, item: ProvisioningItem, tenant_id: UUID
    ) -> None:
        """Create a TwinRelationship from a provisioning item."""
        # For relationships, we use the node's external_id pattern to find related entities
        # The actual mapping happens during plan generation via source_twin_id/target_twin_id
        if item.source_twin_id and item.target_twin_id:
            # Check idempotency
            existing = await self._relationship_repo.get_by_ids(
                item.source_twin_id, item.target_twin_id, tenant_id
            )
            if existing:
                item.status = "skipped"
                return

            rel = TwinRelationship(
                tenant_id=tenant_id,
                source_twin_id=item.source_twin_id,
                target_twin_id=item.target_twin_id,
                relationship_type=item.rel_type or "contains",
                meta_data={"item_id": str(item.id)},
            )
            await self._relationship_repo.create(rel)
            logger.info("Created relationship %s --[%s]--> %s",
                       item.source_twin_id, item.rel_type, item.target_twin_id)
        else:
            # Skip relationship creation - entities may not exist yet
            item.status = "skipped"
            logger.debug("Skipped relationship item %s - missing source/target twin IDs", item.id)

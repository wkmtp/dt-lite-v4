"""Test provisioning idempotency."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


class TestProvisioningIdempotency:
    """Test idempotency requirements for provisioning."""

    def test_external_id_uniqueness_per_item(self):
        """Each item must have unique external_id within a plan."""
        from services.provisioning.models import ProvisioningItem
        table = ProvisioningItem.__table__
        unique_constraints = [c.name for c in table.constraints if hasattr(c, "name")]
        assert "uq_item_plan_external_action" in unique_constraints

    @pytest.mark.asyncio
    async def test_plan_generation_idempotent_on_completed(self):
        """Generating plan when one already exists (completed) returns existing."""
        from services.provisioning.planner import ProvisioningPlanner

        plan_repo = MagicMock()
        existing_plan = MagicMock()
        existing_plan.status = "completed"
        existing_plan.id = uuid4()
        plan_repo.get_by_deployment_id = AsyncMock(return_value=existing_plan)

        planner = ProvisioningPlanner(plan_repo, MagicMock(), MagicMock())
        result = await planner.generate_plan(uuid4(), uuid4())
        assert result == existing_plan

    @pytest.mark.asyncio
    async def test_plan_creation_not_allowed_when_running(self):
        """Cannot regenerate plan while it's in transitional status."""
        from services.provisioning.planner import ProvisioningPlanner

        plan_repo = MagicMock()
        running_plan = MagicMock()
        running_plan.status = "executing"
        running_plan.id = uuid4()
        plan_repo.get_by_deployment_id = AsyncMock(return_value=running_plan)

        planner = ProvisioningPlanner(plan_repo, MagicMock(), MagicMock())
        with pytest.raises(RuntimeError):
            await planner.generate_plan(uuid4(), uuid4())

    def test_execution_record_has_timestamps(self):
        """Execution record must track started_at and finished_at."""
        from services.provisioning.models import ProvisioningExecution
        annotations = ProvisioningExecution.__annotations__
        assert "started_at" in annotations
        assert "finished_at" in annotations

    @pytest.mark.asyncio
    async def test_item_can_track_created_twin_id(self):
        """Items must track created twin entity ID for later relationship resolution."""
        from services.provisioning.models import ProvisioningItem
        annotations = ProvisioningItem.__annotations__
        assert "created_twin_id" in annotations

    def test_plan_tracks_completion_progress(self):
        """Plan must track total_items and completed_items for progress."""
        from services.provisioning.models import ProvisioningPlan
        annotations = ProvisioningPlan.__annotations__
        assert "total_items" in annotations
        assert "completed_items" in annotations

    @pytest.mark.asyncio
    async def test_same_external_id_creates_only_one_entity(self):
        """Same external_id should not create duplicate entities."""
        from services.provisioning.executor import ProvisioningExecutor

        session = MagicMock()
        executor = ProvisioningExecutor(session, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
        executor._entity_repo = MagicMock()

        # First call returns existing entity
        existing = MagicMock()
        existing.id = uuid4()
        executor._entity_repo.get_by_external_id = AsyncMock(return_value=existing)

        item = MagicMock()
        item.external_id = "ahu_room_101"
        item.id = uuid4()

        result = await executor._execute_create_entity(item, uuid4())
        assert result == existing.id

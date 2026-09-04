"""Test provisioning executor."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.provisioning.executor import ProvisioningExecutor


class TestProvisioningExecutor:
    """Test ProvisioningExecutor logic."""

    def setup_method(self):
        self.session = MagicMock()
        self.session.add = AsyncMock()
        self.session.flush = AsyncMock()
        self.session.commit = AsyncMock()

        self.plan_repo = MagicMock()
        self.item_repo = MagicMock()
        self.execution_repo = MagicMock()
        self.entity_repo = MagicMock()
        self.rel_repo = MagicMock()

        self.executor = ProvisioningExecutor(
            session=self.session,
            plan_repo=self.plan_repo,
            item_repo=self.item_repo,
            execution_repo=self.execution_repo,
            entity_repo=self.entity_repo,
            relationship_repo=self.rel_repo,
        )

    @pytest.mark.asyncio
    async def test_execute_plan_not_found(self):
        """Test executing non-existent plan raises error."""
        self.plan_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        with pytest.raises(RuntimeError):
            await self.executor.execute(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_execute_plan_wrong_status(self):
        """Test executing plan in wrong status raises error."""
        plan = MagicMock()
        plan.status = "completed"
        plan.id = uuid4()
        self.plan_repo.get_by_id_for_tenant = AsyncMock(return_value=plan)

        with pytest.raises(RuntimeError):
            await self.executor.execute(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_execute_creates_execution_record(self):
        """Test execution creates execution record."""
        plan = MagicMock()
        plan.status = "ready"
        plan.id = uuid4()
        self.plan_repo.get_by_id_for_tenant = AsyncMock(return_value=plan)
        self.item_repo.list_by_plan = AsyncMock(return_value=[])

        result = await self.executor.execute(plan.id, uuid4())
        assert result is not None
        self.session.add.assert_called_once()

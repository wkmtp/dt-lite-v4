"""Test provisioning planner."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.provisioning.planner import ProvisioningPlanner


class TestProvisioningPlanner:
    """Test ProvisioningPlanner logic."""

    def setup_method(self):
        self.plan_repo = MagicMock()
        self.item_repo = MagicMock()
        self.template_repo = MagicMock()
        self.planner = ProvisioningPlanner(
            self.plan_repo,
            self.item_repo,
            self.template_repo,
        )

    @pytest.mark.asyncio
    async def test_generate_plan_idempotent_completed(self):
        """Test that existing completed plan is returned."""
        existing_plan = MagicMock()
        existing_plan.status = "completed"
        existing_plan.id = uuid4()
        self.plan_repo.get_by_deployment_id = AsyncMock(return_value=existing_plan)

        result = await self.planner.generate_plan(uuid4(), uuid4())
        assert result == existing_plan

    @pytest.mark.asyncio
    async def test_generate_plan_transitional_status_raises(self):
        """Test that transitional status raises error."""
        existing_plan = MagicMock()
        existing_plan.status = "executing"
        existing_plan.id = uuid4()
        self.plan_repo.get_by_deployment_id = AsyncMock(return_value=existing_plan)

        with pytest.raises(RuntimeError):
            await self.planner.generate_plan(uuid4(), uuid4())

    def test_build_external_id_format(self):
        """Test external ID generation is stable."""
        node = MagicMock()
        node.name = "AHU Room 101"
        node.node_type = "room"
        node.id = uuid4()

        external_id = self.planner._build_external_id(node)
        assert node.node_type in external_id
        assert str(node.id)[:8] in external_id

    @pytest.mark.asyncio
    async def test_missing_template_raises_error(self):
        """Test missing template raises error."""
        self.plan_repo.get_by_deployment_id = AsyncMock(return_value=None)

        instance = MagicMock()
        instance.profile.template_id = uuid4()

        import services.provisioning.planner as planner_module
        original_repo = planner_module.DeploymentInstanceRepository
        inst_repo_mock = MagicMock()
        inst_repo_mock.get_by_id_for_tenant = AsyncMock(return_value=instance)
        planner_module.DeploymentInstanceRepository = lambda s: inst_repo_mock
        self.template_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        try:
            from services.provisioning.exceptions import MissingTemplateError
            with pytest.raises(MissingTemplateError):
                await self.planner.generate_plan(uuid4(), uuid4())
        finally:
            planner_module.DeploymentInstanceRepository = original_repo

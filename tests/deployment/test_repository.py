"""Test deployment repositories."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.deployment.repositories.instance_repository import (
    DeploymentInstanceRepository,
)
from services.deployment.repositories.node_repository import DeploymentNodeRepository
from services.deployment.repositories.profile_repository import (
    DeploymentProfileRepository,
)


class TestDeploymentProfileRepository:
    """Test DeploymentProfileRepository."""

    def setup_method(self):
        self.session = MagicMock()
        self.session.execute = AsyncMock()
        self.repo = DeploymentProfileRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_id_for_tenant_found(self):
        mock_obj = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_obj
        self.session.execute.return_value = result

        self.repo = DeploymentProfileRepository(self.session)
        r = await self.repo.get_by_id_for_tenant(uuid4(), uuid4())
        assert r is not None

    @pytest.mark.asyncio
    async def test_get_by_name_returns_none_when_not_found(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = result

        r = await self.repo.get_by_name("nonexistent", uuid4())
        assert r is None

    @pytest.mark.asyncio
    async def test_count_active(self):
        result = MagicMock()
        result.scalar_one.return_value = 5
        self.session.execute.return_value = result

        c = await self.repo.count_active(uuid4())
        assert c == 5

    @pytest.mark.asyncio
    async def test_list_by_template(self):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        self.session.execute.return_value = result

        items = await self.repo.list_by_template(uuid4(), uuid4())
        assert isinstance(items, list)

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_queries(self):
        """Verify tenant_id filter is present in queries."""
        call_args = None

        async def mock_execute(stmt):
            nonlocal call_args
            call_args = str(stmt)
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            return result

        self.session.execute = mock_execute
        await self.repo.get_by_id_for_tenant(uuid4(), uuid4())
        assert "tenant_id" in call_args


class TestDeploymentInstanceRepository:
    """Test DeploymentInstanceRepository."""

    def setup_method(self):
        self.session = MagicMock()
        self.session.execute = AsyncMock()
        self.repo = DeploymentInstanceRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_id_for_tenant_found(self):
        mock_obj = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_obj
        self.session.execute.return_value = result

        r = await self.repo.get_by_id_for_tenant(uuid4(), uuid4())
        assert r is not None

    @pytest.mark.asyncio
    async def test_list_by_profile(self):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        self.session.execute.return_value = result

        items = await self.repo.list_by_profile(uuid4(), uuid4())
        assert isinstance(items, list)

    @pytest.mark.asyncio
    async def test_count_active_instances(self):
        result = MagicMock()
        result.scalar_one.return_value = 3
        self.session.execute.return_value = result

        c = await self.repo.count_active(uuid4())
        assert c == 3

    @pytest.mark.asyncio
    async def test_update_status(self):
        result = MagicMock()
        obj = MagicMock()
        obj.status = "draft"
        result.scalar_one_or_none.return_value = obj
        self.session.execute.return_value = result
        self.session.flush = AsyncMock()

        updated = await self.repo.update_status(uuid4(), "ready", uuid4())
        assert updated.status == "ready"


class TestDeploymentNodeRepository:
    """Test DeploymentNodeRepository."""

    def setup_method(self):
        self.session = MagicMock()
        self.session.execute = AsyncMock()
        self.repo = DeploymentNodeRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_id_for_tenant(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = MagicMock()
        self.session.execute.return_value = result

        r = await self.repo.get_by_id_for_tenant(uuid4(), uuid4())
        assert r is not None

    @pytest.mark.asyncio
    async def test_list_by_deployment(self):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        self.session.execute.return_value = result

        items = await self.repo.list_by_deployment(uuid4(), uuid4())
        assert isinstance(items, list)

    @pytest.mark.asyncio
    async def test_count_by_deployment(self):
        result = MagicMock()
        result.scalar_one.return_value = 5
        self.session.execute.return_value = result

        c = await self.repo.count_by_deployment(uuid4())
        assert c == 5

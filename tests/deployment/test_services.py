"""Test deployment services."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.deployment.exceptions import (
    DuplicateCodeError,
    InstanceNotFoundError,
    InvalidStatusTransitionError,
    ProfileNotFoundError,
)
from services.deployment.services.deployment_service import DeploymentService
from services.deployment.services.validation_service import DeploymentValidationService


class TestDeploymentService:
    """Test DeploymentService business logic."""

    def setup_method(self):
        self.profile_repo = MagicMock()
        self.instance_repo = MagicMock()
        self.service = DeploymentService(self.profile_repo, self.instance_repo)

    @pytest.mark.asyncio
    async def test_create_profile_success(self):
        """Test successful profile creation."""
        self.profile_repo.get_by_name = AsyncMock(return_value=None)
        self.profile_repo.session.flush = AsyncMock()

        result = await self.service.create_profile(
            name="SmartBuilding",
            industry="general",
            template_id=uuid4(),
            description="Test profile",
            tenant_id=uuid4(),
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_profile_duplicate_rejected(self):
        """Test duplicate profile name rejected."""
        existing = MagicMock()
        self.profile_repo.get_by_name = AsyncMock(return_value=existing)

        with pytest.raises(DuplicateCodeError):
            await self.service.create_profile(
                name="SmartBuilding",
                industry="general",
                template_id=uuid4(),
                description="",
                tenant_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_get_profile_found(self):
        """Test getting existing profile."""
        profile = MagicMock()
        profile.id = uuid4()
        self.profile_repo.get_by_id_for_tenant = AsyncMock(return_value=profile)

        result = await self.service.get_profile(profile.id, uuid4())
        assert result == profile

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self):
        """Test getting non-existent profile."""
        self.profile_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        with pytest.raises(ProfileNotFoundError):
            await self.service.get_profile(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_create_instance_success(self):
        """Test successful instance creation."""
        profile = MagicMock()
        profile.id = uuid4()
        self.profile_repo.get_by_id_for_tenant = AsyncMock(return_value=profile)
        self.instance_repo.get_by_name = AsyncMock(return_value=None)
        self.instance_repo.session.flush = AsyncMock()

        from services.deployment.schemas import DeploymentInstanceCreateRequest
        request = DeploymentInstanceCreateRequest(
            profile_id=profile.id,
            name="MyInstance",
        )

        result = await self.service.create_instance(request, uuid4())
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_instance_profile_not_found(self):
        """Test instance creation with missing profile."""
        self.profile_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        from services.deployment.schemas import DeploymentInstanceCreateRequest
        request = DeploymentInstanceCreateRequest(
            profile_id=uuid4(),
            name="MyInstance",
        )

        with pytest.raises(ProfileNotFoundError):
            await self.service.create_instance(request, uuid4())

    @pytest.mark.asyncio
    async def test_transition_status_valid(self):
        """Test valid status transition."""
        instance = MagicMock()
        instance.id = uuid4()
        instance.status = "draft"
        self.instance_repo.get_by_id_for_tenant = AsyncMock(return_value=instance)

        updated_instance = MagicMock()
        updated_instance.status = "validating"
        self.instance_repo.update_status = AsyncMock(return_value=updated_instance)

        updated = await self.service.transition_instance_status(instance.id, "validating", uuid4())
        assert updated.status == "validating"

    @pytest.mark.asyncio
    async def test_transition_status_invalid(self):
        """Test invalid status transition rejected."""
        instance = MagicMock()
        instance.id = uuid4()
        instance.status = "archived"
        self.instance_repo.get_by_id_for_tenant = AsyncMock(return_value=instance)

        with pytest.raises(InvalidStatusTransitionError):
            await self.service.transition_instance_status(instance.id, "running", uuid4())

    @pytest.mark.asyncio
    async def test_get_instance_not_found(self):
        """Test getting non-existent instance."""
        self.instance_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        with pytest.raises(InstanceNotFoundError):
            await self.service.get_instance(uuid4(), uuid4())


class TestDeploymentValidationService:
    """Test DeploymentValidationService."""

    def setup_method(self):
        self.instance_repo = MagicMock()
        self.service = DeploymentValidationService(self.instance_repo)

    @pytest.mark.asyncio
    async def test_validate_instance_not_found(self):
        """Test validation when instance not found."""
        self.instance_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        result = await self.service.validate(uuid4(), uuid4())
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_validate_empty_nodes(self):
        """Test validation fails with no nodes."""
        instance = MagicMock()
        instance.nodes = []
        instance.name = "Test"
        self.instance_repo.get_by_id_for_tenant = AsyncMock(return_value=instance)

        result = await self.service.validate(instance.id, uuid4())
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_validate_with_nodes(self):
        """Test validation passes with nodes."""
        node = MagicMock()
        node.id = uuid4()
        node.name = "Node 1"
        node.capabilities = [MagicMock()]
        instance = MagicMock()
        instance.nodes = [node]
        instance.name = "Test"
        self.instance_repo.get_by_id_for_tenant = AsyncMock(return_value=instance)

        result = await self.service.validate(instance.id, uuid4())
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_validate_capabilities_no_bindings(self):
        """Test capability validation warns on missing bindings."""
        node = MagicMock()
        node.id = uuid4()
        node.name = "Node 1"
        node.capabilities = []
        instance = MagicMock()
        instance.nodes = [node]
        instance.name = "Test"
        self.instance_repo.get_by_id_for_tenant = AsyncMock(return_value=instance)

        result = await self.service.validate_capabilities(instance.id, uuid4())
        assert result.passed_requirements

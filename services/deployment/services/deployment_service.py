"""Deployment service — orchestration layer for deployment lifecycle."""
from typing import Optional
from uuid import UUID

from services.deployment.exceptions import (
    DuplicateCodeError,
    InstanceNotFoundError,
    InvalidStatusTransitionError,
    ProfileNotFoundError,
)
from services.deployment.models import DeploymentInstance, DeploymentProfile
from services.deployment.repositories.instance_repository import (
    DeploymentInstanceRepository,
)
from services.deployment.repositories.profile_repository import (
    DeploymentProfileRepository,
)
from services.deployment.schemas import DeploymentInstanceCreateRequest


# Valid status transitions
_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"validating", "ready", "archived"},
    "validating": {"ready", "draft"},
    "ready": {"deployed", "draft"},
    "deployed": {"running", "offline", "draft"},
    "running": {"offline", "draft"},
    "offline": {"running", "draft"},
    "archived": set(),  # Terminal state
}


class DeploymentService:
    """Service for deployment profile and instance management."""

    def __init__(
        self,
        profile_repo: DeploymentProfileRepository,
        instance_repo: DeploymentInstanceRepository,
    ):
        self._profile_repo = profile_repo
        self._instance_repo = instance_repo

    async def create_profile(
        self, name: str, industry: str, template_id: UUID,
        description: Optional[str], tenant_id: UUID,
    ) -> DeploymentProfile:
        """Create a new deployment profile."""
        existing = await self._profile_repo.get_by_name(name, tenant_id)
        if existing:
            raise DuplicateCodeError("Deployment profile", name)

        profile = DeploymentProfile(
            tenant_id=tenant_id,
            name=name.strip(),
            industry=industry.lower(),
            template_id=template_id,
            description=description,
            status="draft",
        )
        await self._profile_repo.session.flush()
        return profile

    async def update_profile_status(
        self, profile_id: UUID, new_status: str, tenant_id: UUID,
    ) -> DeploymentProfile:
        """Update profile status."""
        profile = await self._profile_repo.get_by_id_for_tenant(profile_id, tenant_id)
        if not profile:
            raise ProfileNotFoundError(profile_id)

        profile.status = new_status
        await self._profile_repo.session.flush()
        return profile

    async def get_profile(self, profile_id: UUID, tenant_id: UUID) -> DeploymentProfile:
        """Get profile by ID with tenant isolation."""
        profile = await self._profile_repo.get_by_id_for_tenant(profile_id, tenant_id)
        if not profile:
            raise ProfileNotFoundError(profile_id)
        return profile

    async def create_instance(
        self, request: DeploymentInstanceCreateRequest, tenant_id: UUID,
    ) -> DeploymentInstance:
        """Create a new deployment instance from a profile."""
        profile = await self._profile_repo.get_by_id_for_tenant(request.profile_id, tenant_id)
        if not profile:
            raise ProfileNotFoundError(request.profile_id)

        existing = await self._instance_repo.get_by_name(request.name, tenant_id)
        if existing:
            raise DuplicateCodeError("Deployment instance", request.name)

        instance = DeploymentInstance(
            tenant_id=tenant_id,
            profile_id=request.profile_id,
            name=request.name.strip(),
            location=request.location,
            status=request.status,
        )
        await self._instance_repo.session.flush()
        return instance

    async def get_instance(self, instance_id: UUID, tenant_id: UUID) -> DeploymentInstance:
        """Get instance by ID with tenant isolation."""
        instance = await self._instance_repo.get_by_id_for_tenant(instance_id, tenant_id)
        if not instance:
            raise InstanceNotFoundError(instance_id)
        return instance

    async def transition_instance_status(
        self, instance_id: UUID, new_status: str, tenant_id: UUID,
    ) -> DeploymentInstance:
        """Transition instance to a new status."""
        instance = await self._instance_repo.get_by_id_for_tenant(instance_id, tenant_id)
        if not instance:
            raise InstanceNotFoundError(instance_id)

        current = instance.status
        if new_status not in _STATUS_TRANSITIONS.get(current, set()):
            raise InvalidStatusTransitionError(current, new_status)

        updated = await self._instance_repo.update_status(instance_id, new_status, tenant_id)
        return updated

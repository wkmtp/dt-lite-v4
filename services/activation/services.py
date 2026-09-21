"""TwinActivationService — Activate/deactivate PersistentTwinEntity in runtime registry."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from services.activation.exceptions import (
    ActivationAlreadyActiveError,
    ActivationAlreadyInactiveError,
    ActivationNotFoundError,
    ActivationStateError,
)
from services.activation.models import TwinActivationLog
from services.activation.repository import TwinActivationLogRepository
from services.twin.exceptions import TwinEntityNotFoundError
from services.twin.registry import TwinEntityRegistry
from services.twin.repositories.definition_repository import DefinitionRepository
from services.twin.repositories.entity_repository import EntityRepository

logger = logging.getLogger(__name__)


class TwinActivationService:
    """Manages the activation lifecycle of PersistentTwinEntity instances.

    Activation transforms a provisioned entity (PersistentTwinEntity in DB)
    into an operational twin (TwinEntity in registry).

    State machine:
      CREATED → BOUND → ACTIVE → INACTIVE
                       ↘ ERROR
    """

    def __init__(self, session, registry: TwinEntityRegistry):
        self._session = session
        self._log_repo = TwinActivationLogRepository(session)
        self._entity_repo = EntityRepository(session)
        self._definition_repo = DefinitionRepository(session)
        self._registry = registry

    async def ensure_log(
        self, entity_id: UUID, tenant_id: UUID,
    ) -> TwinActivationLog:
        """Get or create activation log for an entity."""
        log = await self._log_repo.get_by_entity_for_tenant(entity_id, tenant_id)
        if log is None:
            log = TwinActivationLog(
                tenant_id=tenant_id,
                twin_entity_id=entity_id,
                state="created",
            )
            await self._log_repo.session.add(log)
            await self._log_repo.session.flush()
        return log

    async def activate(
        self, entity_id: UUID, tenant_id: UUID,
    ) -> TwinActivationLog:
        """Activate a PersistentTwinEntity — register in TwinEntityRegistry.

        Flow:
          1. Validate entity exists for tenant
          2. Fetch TwinDefinition to get entity_type code
          3. Check current activation state
          4. Create TwinEntity runtime object
          5. Register in TwinEntityRegistry
          6. Update activation log to ACTIVE
        """
        # Validate entity
        entity = await self._entity_repo.get_by_id_for_tenant(entity_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(entity_id)

        # Get definition to determine entity_type
        definition = await self._definition_repo.get_by_id_for_tenant(
            entity.definition_id, tenant_id,
        )
        entity_type = definition.code if definition else "generic"

        # Get or create activation log
        log = await self.ensure_log(entity_id, tenant_id)

        if log.state == "active":
            raise ActivationAlreadyActiveError(entity_id)

        if log.state not in ("created", "bound"):
            raise ActivationStateError(entity_id, log.state, "active")

        # Build runtime TwinEntity and register
        from services.twin.models import TwinEntity
        runtime_entity = TwinEntity(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name,
            entity_type=entity_type,
            template={},
            runtime_state={},
        )
        self._registry.register(runtime_entity)

        # Update log
        log.state = "active"
        log.activated_at = datetime.now(timezone.utc)
        log.updated_at = datetime.now(timezone.utc)
        log.error_message = None
        await self._log_repo.session.flush()

        logger.info("Activated entity %s for tenant %s", entity_id, tenant_id)
        return log

    async def deactivate(
        self, entity_id: UUID, tenant_id: UUID,
    ) -> TwinActivationLog:
        """Deactivate a PersistentTwinEntity — remove from TwinEntityRegistry.

        Flow:
          1. Validate entity exists for tenant
          2. Check current activation state
          3. Remove from TwinEntityRegistry
          4. Update activation log to INACTIVE
        """
        # Validate entity
        entity = await self._entity_repo.get_by_id_for_tenant(entity_id, tenant_id)
        if entity is None:
            raise TwinEntityNotFoundError(entity_id)

        # Get activation log
        log = await self._log_repo.get_by_entity_for_tenant(entity_id, tenant_id)
        if log is None:
            raise ActivationNotFoundError(entity_id)

        if log.state == "inactive":
            raise ActivationAlreadyInactiveError(entity_id)

        if log.state != "active":
            raise ActivationStateError(entity_id, log.state, "inactive")

        # Remove from registry
        self._registry.remove(entity_id, tenant_id)

        # Update log
        log.state = "inactive"
        log.deactivated_at = datetime.now(timezone.utc)
        log.updated_at = datetime.now(timezone.utc)
        await self._log_repo.session.flush()

        logger.info("Deactivated entity %s for tenant %s", entity_id, tenant_id)
        return log

    async def get_status(
        self, entity_id: UUID, tenant_id: UUID,
    ) -> TwinActivationLog:
        """Get activation status for an entity."""
        log = await self._log_repo.get_by_entity_for_tenant(entity_id, tenant_id)
        if log is None:
            # Entity exists but has no activation log — treat as CREATED
            return await self.ensure_log(entity_id, tenant_id)
        return log

    async def bind_device(
        self, entity_id: UUID, binding_id: UUID, tenant_id: UUID,
    ) -> TwinActivationLog:
        """Link a TwinBinding (Task 9) to the activation log.

        Updates state from CREATED to BOUND.
        """
        log = await self._log_repo.get_by_entity_for_tenant(entity_id, tenant_id)
        if log is None:
            log = await self.ensure_log(entity_id, tenant_id)

        if log.state not in ("created", "bound"):
            raise ActivationStateError(entity_id, log.state, "bound")

        log.binding_id = binding_id
        log.state = "bound"
        log.updated_at = datetime.now(timezone.utc)
        await self._log_repo.session.flush()

        logger.info("Bound entity %s to binding %s for tenant %s",
                     entity_id, binding_id, tenant_id)
        return log

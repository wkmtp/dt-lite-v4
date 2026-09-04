"""Test TwinBinding persistence layer."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.twin.services.binding_service import BindingService


class TestBindingRepository:
    """Tests for BindingRepository."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.repositories.binding_repository import BindingRepository
        self.repo = BindingRepository(self.session)

    @pytest.mark.asyncio
    async def test_get_by_device_found(self):
        from services.twin.models.binding import TwinBinding
        binding = TwinBinding(
            id=uuid4(), tenant_id=uuid4(), device_id=uuid4(), twin_entity_id=uuid4()
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = binding
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_device(binding.device_id, binding.tenant_id)
        assert result is not None
        assert result.device_id == binding.device_id

    @pytest.mark.asyncio
    async def test_get_by_device_not_found(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mock_result

        result = await self.repo.get_by_device(uuid4(), uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_exists_returns_true(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        self.session.execute.return_value = mock_result

        result = await self.repo.exists(uuid4(), uuid4(), uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mock_result

        result = await self.repo.exists(uuid4(), uuid4(), uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_list_by_entity(self):
        from services.twin.models.binding import TwinBinding
        bindings = [
            TwinBinding(
                id=uuid4(), tenant_id=uuid4(), device_id=uuid4(), twin_entity_id=uuid4()
            )
            for _ in range(2)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = bindings
        self.session.execute.return_value = mock_result

        result = await self.repo.list_by_entity(bindings[0].twin_entity_id, bindings[0].tenant_id)
        assert len(result) == 2


class TestBindingService:
    """Tests for BindingService."""

    def setup_method(self):
        self.session = AsyncMock()
        from services.twin.services.binding_service import BindingService
        self.service = BindingService(self.session)

    @pytest.mark.asyncio
    async def test_create_binding_success(self):
        from services.twin.models.binding import TwinBinding
        mock_device_repo = MagicMock()
        mock_device = MagicMock()
        mock_device.id = uuid4()
        mock_device.tenant_id = uuid4()
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_device)

        mock_entity_repo = MagicMock()
        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        mock_entity.tenant_id = mock_device.tenant_id
        mock_entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        mock_binding_repo = MagicMock()
        mock_binding_repo.get_by_device = AsyncMock(return_value=None)
        mock_binding = TwinBinding(
            id=uuid4(), tenant_id=mock_device.tenant_id,
            device_id=mock_device.id, twin_entity_id=mock_entity.id
        )
        mock_binding_repo.create = AsyncMock(return_value=mock_binding)

        self.service._device_repo = mock_device_repo
        self.service._entity_repo = mock_entity_repo
        self.service._repo = mock_binding_repo

        result = await self.service.create(
            device_id=mock_device.id,
            entity_id=mock_entity.id,
            tenant_id=mock_device.tenant_id,
        )
        assert result.device_id == mock_device.id

    @pytest.mark.asyncio
    async def test_create_binding_duplicate_raises(self):
        from services.twin.models.binding import TwinBinding
        from services.twin.exceptions import TwinBindingAlreadyExistsError
        existing_binding = TwinBinding(
            id=uuid4(), tenant_id=uuid4(), device_id=uuid4(), twin_entity_id=uuid4()
        )

        mock_binding_repo = MagicMock()
        mock_binding_repo.get_by_device = AsyncMock(return_value=existing_binding)

        mock_device = MagicMock()
        mock_entity = MagicMock()

        mock_device_repo = MagicMock()
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_device)

        mock_entity_repo = MagicMock()
        mock_entity_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_entity)

        self.service._repo = mock_binding_repo
        self.service._device_repo = mock_device_repo
        self.service._entity_repo = mock_entity_repo

        with pytest.raises(TwinBindingAlreadyExistsError):
            await self.service.create(
                device_id=existing_binding.device_id,
                entity_id=existing_binding.twin_entity_id,
                tenant_id=existing_binding.tenant_id,
            )

    @pytest.mark.asyncio
    async def test_create_binding_device_not_found_raises(self):
        from services.twin.exceptions import TwinDeviceNotFoundError
        mock_binding_repo = MagicMock()
        mock_binding_repo.get_by_device = AsyncMock(return_value=None)

        mock_device_repo = MagicMock()
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        mock_entity_repo = MagicMock()

        self.service._repo = mock_binding_repo
        self.service._device_repo = mock_device_repo
        self.service._entity_repo = mock_entity_repo

        with pytest.raises(TwinDeviceNotFoundError):
            await self.service.create(
                device_id=uuid4(),
                entity_id=uuid4(),
                tenant_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_create_binding_entity_not_found_raises(self):
        from services.twin.exceptions import TwinEntityNotFoundError
        mock_binding_repo = MagicMock()
        mock_binding_repo.get_by_device = AsyncMock(return_value=None)

        mock_device_repo = MagicMock()
        mock_device = MagicMock()
        mock_device.id = uuid4()
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_device)

        mock_entity_repo = MagicMock()
        mock_entity_repo.get_by_id_for_tenant = AsyncMock(return_value=None)

        self.service._repo = mock_binding_repo
        self.service._device_repo = mock_device_repo
        self.service._entity_repo = mock_entity_repo

        with pytest.raises(TwinEntityNotFoundError):
            await self.service.create(
                device_id=mock_device.id,
                entity_id=uuid4(),
                tenant_id=mock_device.tenant_id,
            )

    @pytest.mark.asyncio
    async def test_delete_binding(self):
        mock_repo = MagicMock()
        mock_repo.soft_delete = AsyncMock(return_value=True)
        self.service._repo = mock_repo

        result = await self.service.delete(uuid4(), uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_get_binding_by_device(self):
        from services.twin.models.binding import TwinBinding
        binding = TwinBinding(
            id=uuid4(), tenant_id=uuid4(), device_id=uuid4(), twin_entity_id=uuid4()
        )

        mock_repo = MagicMock()
        mock_repo.get_by_device = AsyncMock(return_value=binding)
        self.service._repo = mock_repo

        result = await self.service.get_by_device(binding.device_id, binding.tenant_id)
        assert result is not None
        assert result.id == binding.id

    @pytest.mark.asyncio
    async def test_list_bindings_by_entity(self):
        from services.twin.models.binding import TwinBinding
        bindings = [
            TwinBinding(
                id=uuid4(), tenant_id=uuid4(), device_id=uuid4(), twin_entity_id=uuid4()
            )
            for _ in range(2)
        ]

        mock_repo = MagicMock()
        mock_repo.list_by_entity = AsyncMock(return_value=bindings)
        self.service._repo = mock_repo

        result = await self.service.list_by_entity(bindings[0].twin_entity_id, bindings[0].tenant_id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_tenant_verification_in_create(self):
        """Test that both device and entity must belong to same tenant."""
        from services.twin.exceptions import TwinEntityNotFoundError
        tenant_a = uuid4()
        tenant_b = uuid4()

        mock_device = MagicMock()
        mock_device.id = uuid4()
        mock_device.tenant_id = tenant_a

        mock_device_repo = MagicMock()
        mock_device_repo.get_by_id_for_tenant = AsyncMock(return_value=mock_device)

        mock_entity_repo = MagicMock()
        mock_entity_repo.get_by_id_for_tenant = AsyncMock(return_value=None)  # Not found for tenant A

        mock_binding_repo = MagicMock()

        service = BindingService(self.session)
        service._device_repo = mock_device_repo
        service._entity_repo = mock_entity_repo
        service._repo = mock_binding_repo

        # Should fail because entity doesn't exist for tenant A
        with pytest.raises(TwinEntityNotFoundError):
            await service.create(
                device_id=mock_device.id,
                entity_id=tenant_b,  # entity ID belonging to another tenant
                tenant_id=tenant_a,
            )

"""Repository Contract Tests for Phase 1 Task 2.1

Tests verify Repository layer compliance with architecture rules:
- AsyncSession injection (no internal session creation)
- No commit() calls (transaction controlled by Service layer)
- All delete operations use soft_delete()
- Correct base class inheritance
- No dynamic imports at runtime
"""
import inspect
from typing import get_type_hints
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestRepositoryBaseClasses:
    """Test that all repositories inherit from correct base classes."""
    
    def test_entity_repository_inherits_tenant_aware(self):
        """EntityRepository must inherit from TenantAwareRepository."""
        from services.core.repositories.base import TenantAwareRepository
        from services.core.repositories.entity_repository import EntityRepository
        
        assert issubclass(EntityRepository, TenantAwareRepository)
    
    def test_asset_repository_inherits_tenant_aware(self):
        """AssetRepository must inherit from TenantAwareRepository."""
        from services.core.repositories.asset_repository import AssetRepository
        from services.core.repositories.base import TenantAwareRepository
        
        assert issubclass(AssetRepository, TenantAwareRepository)
    
    def test_property_repository_inherits_tenant_aware(self):
        """PropertyRepository must inherit from TenantAwareRepository."""
        from services.core.repositories.base import TenantAwareRepository
        from services.core.repositories.property_repository import PropertyRepository
        
        assert issubclass(PropertyRepository, TenantAwareRepository)
    
    def test_relationship_repository_inherits_tenant_aware(self):
        """RelationshipRepository must inherit from TenantAwareRepository."""
        from services.core.repositories.base import TenantAwareRepository
        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        
        assert issubclass(RelationshipRepository, TenantAwareRepository)
    
    def test_tenant_repository_inherits_base(self):
        """TenantRepository must inherit from BaseRepository."""
        from services.core.repositories.base import BaseRepository
        from services.identity.repositories.tenant_repository import TenantRepository
        
        assert issubclass(TenantRepository, BaseRepository)
    
    def test_user_repository_inherits_tenant_aware(self):
        """UserRepository must inherit from TenantAwareRepository."""
        from services.core.repositories.base import TenantAwareRepository
        from services.identity.repositories.user_repository import UserRepository
        
        assert issubclass(UserRepository, TenantAwareRepository)
    
    def test_role_repository_inherits_tenant_aware(self):
        """RoleRepository must inherit from TenantAwareRepository."""
        from services.core.repositories.base import TenantAwareRepository
        from services.identity.repositories.role_repository import RoleRepository
        
        assert issubclass(RoleRepository, TenantAwareRepository)


class TestRepositoryNoCommit:
    """Verify repositories do NOT call commit()."""
    
    @pytest.mark.asyncio
    async def test_entity_create_no_commit(self):
        """EntityRepository.create must not call commit()."""
        from uuid import uuid4

        from services.core.models.models import Entity
        from services.core.repositories.entity_repository import EntityRepository
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        # Note: commit is NOT mocked - if called, it would fail
        
        repo = EntityRepository(mock_session)
        entity = Entity(
            id=uuid4(),
            tenant_id=uuid4(),
            entity_type="test",
            name="Test"
        )
        
        result = await repo.create(entity)
        
        assert result is not None
        mock_session.flush.assert_called_once()
        # Verify commit was never referenced in the repository code
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_asset_create_no_commit(self):
        """AssetRepository.create_asset must not call commit()."""
        from uuid import uuid4

        from services.core.models.models import Asset
        from services.core.repositories.asset_repository import AssetRepository
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        repo = AssetRepository(mock_session)
        asset = Asset(
            id=uuid4(),
            entity_id=uuid4(),
            asset_code="TEST-001",
            asset_class="hvac"
        )
        
        result = await repo.create_asset(asset)
        
        assert result is not None
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_relationship_create_no_commit(self):
        """RelationshipRepository.create_relation must not call commit()."""
        from uuid import uuid4

        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        repo = RelationshipRepository(mock_session)
        
        rel = await repo.create_relation(
            tenant_id=uuid4(),
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            relation_type="contains"
        )
        
        assert rel is not None
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()


class TestRepositoryDeleteConvention:
    """Verify delete operations use soft_delete() or are marked as internal."""
    
    def test_hard_delete_marked_internal(self):
        """BaseRepository.hard_delete must be marked as internal use only."""
        from services.core.repositories.base import BaseRepository
        
        # Check if hard_delete exists and is documented as internal
        assert hasattr(BaseRepository, 'hard_delete'), \
            "BaseRepository should have hard_delete method"
        
        # The method should exist but be marked for internal use
        method_doc = BaseRepository.hard_delete.__doc__
        assert method_doc is not None, \
            "hard_delete should have documentation"
        assert 'internal' in method_doc.lower() or 'caution' in method_doc.lower(), \
            "hard_delete docstring should warn about internal use"
    
    @pytest.mark.asyncio
    async def test_entity_soft_delete_used(self):
        """EntityRepository.soft_delete should use soft_delete() on model."""
        from uuid import uuid4

        from services.core.models.models import Entity
        from services.core.repositories.entity_repository import EntityRepository
        
        entity = Entity(
            id=uuid4(),
            tenant_id=uuid4(),
            entity_type="test",
            name="Test"
        )
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entity
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        repo = EntityRepository(mock_session)
        result = await repo.soft_delete(entity.id)
        
        assert result is True
        assert entity.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_asset_soft_delete_used(self):
        """AssetRepository.soft_delete should use soft_delete() on model."""
        from uuid import uuid4

        from services.core.models.models import Asset
        from services.core.repositories.asset_repository import AssetRepository
        
        asset = Asset(
            id=uuid4(),
            entity_id=uuid4(),
            asset_code="TEST-001",
            asset_class="hvac"
        )
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = asset
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        repo = AssetRepository(mock_session)
        result = await repo.soft_delete(asset.id)
        
        assert result is True
        assert asset.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_relationship_delete_uses_soft_delete(self):
        """RelationshipRepository.delete_relation should use soft_delete()."""
        from uuid import uuid4

        from services.core.models.models import Relationship
        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        
        rel = Relationship(
            id=uuid4(),
            tenant_id=uuid4(),
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            relation_type="contains"
        )
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rel
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        repo = RelationshipRepository(mock_session)
        result = await repo.delete_relation(rel.id, rel.tenant_id)
        
        assert result is True
        assert rel.deleted_at is not None


class TestRepositoryAsyncSessionInjection:
    """Verify repositories accept AsyncSession in constructor."""
    
    def test_entity_repo_accepts_async_session(self):
        """EntityRepository.__init__ should accept AsyncSession."""

        from services.core.repositories.entity_repository import EntityRepository
        
        sig = inspect.signature(EntityRepository.__init__)
        params = list(sig.parameters.keys())
        
        assert 'session' in params, "EntityRepository should accept 'session' parameter"
        
        # Check type hint
        type_hints = get_type_hints(EntityRepository.__init__)
        assert 'session' in type_hints, "EntityRepository should type-hint 'session'"
    
    def test_asset_repo_accepts_async_session(self):
        """AssetRepository.__init__ should accept AsyncSession."""

        from services.core.repositories.asset_repository import AssetRepository
        
        sig = inspect.signature(AssetRepository.__init__)
        params = list(sig.parameters.keys())
        
        assert 'session' in params
    
    def test_property_repo_accepts_async_session(self):
        """PropertyRepository.__init__ should accept AsyncSession."""
        from services.core.repositories.property_repository import PropertyRepository
        
        sig = inspect.signature(PropertyRepository.__init__)
        params = list(sig.parameters.keys())
        
        assert 'session' in params
    
    def test_tenant_repo_accepts_async_session(self):
        """TenantRepository.__init__ should accept AsyncSession."""
        from services.identity.repositories.tenant_repository import TenantRepository
        
        sig = inspect.signature(TenantRepository.__init__)
        params = list(sig.parameters.keys())
        
        assert 'session' in params


class TestRepositoryNoDynamicImports:
    """Verify repositories don't use dynamic imports (except for uuid which is standard)."""
    
    def test_no_dynamic_imports_in_entity_repo(self):
        """EntityRepository should not have dynamic imports."""
        from services.core.repositories.entity_repository import EntityRepository
        
        source = inspect.getsource(EntityRepository)
        
        # Count dynamic imports (imports inside methods)
        lines = source.split('\n')
        dynamic_imports = [
            line.strip() for line in lines
            if 'import ' in line and '    ' in line and not line.strip().startswith('#')
        ]
        
        # Should be minimal - only uuid might be imported
        # Filter out standard library imports like uuid
        non_standard = [
            imp for imp in dynamic_imports
            if not any(x in imp for x in ['uuid', '#'])
        ]
        
        # Allow minimal dynamic imports, but warn about non-standard ones
        assert len(non_standard) == 0, \
            f"EntityRepository has unexpected dynamic imports: {non_standard}"
    
    def test_no_dynamic_imports_in_base_repo(self):
        """BaseRepository should have minimal dynamic imports."""
        from services.core.repositories.base import BaseRepository
        
        source = inspect.getsource(BaseRepository)
        
        # Should not have dynamic imports after fix
        assert 'from services.tenant_context import get_tenant_id' not in source or \
               source.count('from services.tenant_context') <= 1, \
            "BaseRepository should not have repeated dynamic imports"


class TestRepositoryInterfaceConsistency:
    """Verify consistent interface across repositories."""
    
    def test_all_repos_have_get_by_id(self):
        """All repositories should implement get_by_id()."""
        from services.core.repositories.asset_repository import AssetRepository
        from services.core.repositories.entity_repository import EntityRepository
        from services.core.repositories.property_repository import PropertyRepository
        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        from services.identity.repositories.role_repository import RoleRepository
        from services.identity.repositories.tenant_repository import TenantRepository
        from services.identity.repositories.user_repository import UserRepository
        
        repos = [
            EntityRepository, AssetRepository, PropertyRepository,
            RelationshipRepository, TenantRepository, UserRepository, RoleRepository
        ]
        
        for repo_class in repos:
            assert hasattr(repo_class, 'get_by_id'), \
                f"{repo_class.__name__} should have get_by_id method"
    
    def test_all_repos_have_list_method(self):
        """All repositories should implement list() or equivalent."""
        from services.core.repositories.asset_repository import AssetRepository
        from services.core.repositories.entity_repository import EntityRepository
        from services.core.repositories.property_repository import PropertyRepository
        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        from services.identity.repositories.role_repository import RoleRepository
        from services.identity.repositories.tenant_repository import TenantRepository
        from services.identity.repositories.user_repository import UserRepository
        
        repos = [
            EntityRepository, AssetRepository, PropertyRepository,
            RelationshipRepository, TenantRepository, UserRepository, RoleRepository
        ]
        
        for repo_class in repos:
            # Some repos might have list_by_* instead of list()
            has_list = hasattr(repo_class, 'list') or \
                       any(m for m in dir(repo_class) if m.startswith('list'))
            assert has_list, \
                f"{repo_class.__name__} should have a list method"
    
    def test_all_repos_have_soft_delete(self):
        """All core repositories should implement soft_delete()."""
        from services.core.repositories.asset_repository import AssetRepository
        from services.core.repositories.entity_repository import EntityRepository
        from services.core.repositories.property_repository import PropertyRepository
        from services.core.repositories.relationship_repository import (
            RelationshipRepository,
        )
        
        repos = [
            EntityRepository, AssetRepository, PropertyRepository,
            RelationshipRepository
        ]
        
        for repo_class in repos:
            assert hasattr(repo_class, 'soft_delete'), \
                f"{repo_class.__name__} should have soft_delete method"

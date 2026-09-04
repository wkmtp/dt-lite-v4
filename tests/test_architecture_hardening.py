"""Task 1.5 Tests: Architecture Hardening - Metadata, Types, TenantContext"""
import pytest
import uuid


class TestUnifiedBaseMetadata:
    """Test that Identity and Core models share unified Base metadata"""
    
    def test_unified_base_import(self):
        """Verify unified Base can be imported from services.core.models.base"""
        from services.core.models.base import Base
        assert Base is not None
    
    def test_identity_models_use_unified_base(self):
        """Verify Identity models inherit from unified Base"""
        from services.core.models.base import Base
        from services.identity.models.models import Tenant, User, Role, Permission
        
        # All models should share the same metadata
        assert Tenant.__table__.metadata is Base.metadata
        assert User.__table__.metadata is Base.metadata
        assert Role.__table__.metadata is Base.metadata
        assert Permission.__table__.metadata is Base.metadata
    
    def test_core_models_use_unified_base(self):
        """Verify Core models inherit from unified Base"""
        from services.core.models.base import Base
        from services.core.models.models import Entity, Asset, PropertyDefinition
        
        assert Entity.__table__.metadata is Base.metadata
        assert Asset.__table__.metadata is Base.metadata
        assert PropertyDefinition.__table__.metadata is Base.metadata
    
    def test_single_metadata_across_services(self):
        """Verify all models share exactly one metadata instance"""
        from services.identity.models.models import Tenant, User
        from services.core.models.models import Entity, Asset
        
        metadata = Tenant.__table__.metadata
        assert User.__table__.metadata is metadata
        assert Entity.__table__.metadata is metadata
        assert Asset.__table__.metadata is metadata


class TestPropertyDefinitionBooleanFields:
    """Test that required and writable fields are Boolean type"""
    
    def test_required_is_boolean_type(self):
        """Verify required column is Boolean type"""
        from services.core.models.models import PropertyDefinition
        from sqlalchemy import inspect, Boolean
        
        mapper = inspect(PropertyDefinition)
        required_col = mapper.columns['required']
        assert isinstance(required_col.type, Boolean), \
            f"required column should be Boolean, got {type(required_col.type)}"
    
    def test_writable_is_boolean_type(self):
        """Verify writable column is Boolean type"""
        from services.core.models.models import PropertyDefinition
        from sqlalchemy import inspect, Boolean
        
        mapper = inspect(PropertyDefinition)
        writable_col = mapper.columns['writable']
        assert isinstance(writable_col.type, Boolean), \
            f"writable column should be Boolean, got {type(writable_col.type)}"
    
    def test_property_definition_creation_with_boolean_values(self):
        """Test creating PropertyDefinition with boolean values"""
        from services.core.models.models import PropertyDefinition
        
        prop_def = PropertyDefinition(
            entity_type="building",
            key="temperature",
            data_type="number",
            required=True,
            writable=False,
        )
        assert prop_def.required is True
        assert prop_def.writable is False
    
    def test_property_definition_default_boolean_values(self):
        """Test default boolean values for new PropertyDefinition"""
        from services.core.models.models import PropertyDefinition
        
        prop_def = PropertyDefinition(
            entity_type="test",
            key="key1",
            data_type="string",
        )
        # Default values may be None when not explicitly set, check they are boolean-like
        assert prop_def.required in (False, None)
        assert prop_def.writable in (False, None)


class TestTenantContext:
    """Test TenantContext foundation framework"""
    
    def test_tenant_context_creation(self):
        """Test creating TenantContext instance"""
        from services.tenant_context import TenantContext
        
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        ctx = TenantContext(tenant_id=tenant_id, user_id=user_id, user_roles=["admin"])
        
        assert ctx.tenant_id == tenant_id
        assert ctx.user_id == user_id
        assert ctx.tenant_id_str == str(tenant_id)
        assert ctx.user_roles == ["admin"]
    
    def test_tenant_context_defaults(self):
        """Test TenantContext with default values"""
        from services.tenant_context import TenantContext
        
        ctx = TenantContext(tenant_id=uuid.uuid4())
        assert ctx.user_id is None
        assert ctx.user_roles == []
    
    def test_get_tenant_context_none_by_default(self):
        """Test get_tenant_context returns None when no context set"""
        from services.tenant_context import get_tenant_context, clear_tenant_context
        
        # After clearing, should return None
        clear_tenant_context()
        assert get_tenant_context() is None
    
    def test_set_and_get_tenant_context(self):
        """Test setting and getting tenant context"""
        from services.tenant_context import (
            set_tenant_context, get_tenant_context, 
            get_tenant_id, clear_tenant_context, TenantContext
        )
        
        tenant_id = uuid.uuid4()
        ctx = TenantContext(tenant_id=tenant_id)
        
        try:
            set_tenant_context(ctx)
            current_ctx = get_tenant_context()
            assert current_ctx is not None
            assert current_ctx.tenant_id == tenant_id
            assert get_tenant_id() == str(tenant_id)
        finally:
            clear_tenant_context()


class TestPropertyDefinitionIndexes:
    """Task 2 Pre-check: Verify property_definitions partial unique indexes exist in migration"""
    
    def test_phase1_migration_contains_system_index(self):
        """Verify phase1_identity_core migration creates system-level partial unique index"""
        import os
        migration_path = 'database/migrations/versions/phase1_identity_core.py'
        
        with open(migration_path, 'r') as f:
            content = f.read()
        
        # Check for system-level index
        assert "uq_property_definition_system" in content, \
            "Missing system-level partial unique index 'uq_property_definition_system'"
        assert "tenant_id IS NULL" in content, \
            "System-level index must have WHERE tenant_id IS NULL condition"
    
    def test_phase1_migration_contains_tenant_index(self):
        """Verify phase1_identity_core migration creates tenant-level partial unique index"""
        import os
        migration_path = 'database/migrations/versions/phase1_identity_core.py'
        
        with open(migration_path, 'r') as f:
            content = f.read()
        
        # Check for tenant-level index
        assert "uq_property_definition_tenant" in content, \
            "Missing tenant-level partial unique index 'uq_property_definition_tenant'"
        assert "tenant_id IS NOT NULL" in content, \
            "Tenant-level index must have WHERE tenant_id IS NOT NULL condition"
    
    def test_model_has_unique_constraint(self):
        """Verify PropertyDefinition model has UniqueConstraint for (tenant_id, entity_type, key)"""
        from services.core.models.models import PropertyDefinition
        from sqlalchemy import UniqueConstraint
        
        # Check that the table has a UniqueConstraint involving tenant_id, entity_type, key
        constraints = list(PropertyDefinition.__table__.constraints)
        unique_constraints = [c for c in constraints if isinstance(c, UniqueConstraint)]
        
        assert len(unique_constraints) > 0, \
            "PropertyDefinition should have at least one UniqueConstraint"
        
        # At least one unique constraint should involve these columns
        found = False
        for uc in unique_constraints:
            cols = {c.name for c in uc.columns}
            if {'tenant_id', 'entity_type', 'key'}.issubset(cols):
                found = True
                break
        
        assert found, "PropertyDefinition should have a UniqueConstraint on (tenant_id, entity_type, key)"
    
    def test_index_names_follow_convention(self):
        """Verify index names follow naming convention"""
        import os
        migration_path = 'database/migrations/versions/phase1_identity_core.py'
        
        with open(migration_path, 'r') as f:
            content = f.read()
        
        # Both indexes should be named consistently
        assert "uq_property_definition_system" in content
        assert "uq_property_definition_tenant" in content


class TestMigrationChain:
    """Test that migration chain is correct"""
    
    def test_migration_file_exists(self):
        """Verify migration file exists"""
        import os
        migration_path = 'database/migrations/versions/phase1_fix_property_boolean.py'
        assert os.path.exists(migration_path), f"Migration file not found: {migration_path}"
    
    def test_migration_revision_values(self):
        """Verify migration has correct revision values by reading file"""
        import os
        migration_path = 'database/migrations/versions/phase1_fix_property_boolean.py'
        
        with open(migration_path, 'r') as f:
            content = f.read()
        
        assert "revision = 'phase1_fix_property_boolean'" in content
        assert "down_revision = 'phase1_identity_core'" in content

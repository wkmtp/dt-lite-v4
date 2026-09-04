"""Phase 1 Tests for Identity Service - Tenant, User, Auth"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
import uuid

from services.identity.models.models import Tenant, User, Role, Permission


class TestTenantModel:
    def test_tenant_creation(self):
        """Test creating a tenant instance"""
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Test Tenant",
            code="TEST",
            status="active"
        )
        assert tenant.name == "Test Tenant"
        assert tenant.code == "TEST"
        assert tenant.status == "active"
    
    def test_tenant_is_active_property(self):
        """Test is_active property"""
        tenant = Tenant(status="active")
        assert tenant.is_active is True
        
        tenant.status = "suspended"
        assert tenant.is_active is False


class TestUserModel:
    def test_user_creation(self):
        """Test creating a user instance"""
        user = User(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$examplehash",
            status="active"
        )
        assert user.username == "testuser"
        assert user.status == "active"
    
    def test_user_is_active_property(self):
        """Test is_active property"""
        user = User(status="active")
        assert user.is_active is True
        
        user.status = "inactive"
        assert user.is_active is False


class TestRoleModel:
    def test_role_creation(self):
        """Test creating a role instance"""
        role = Role(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Administrator",
            code="admin"
        )
        assert role.code == "admin"


class TestPermissionModel:
    def test_permission_creation(self):
        """Test creating a permission instance"""
        permission = Permission(
            id=uuid.uuid4(),
            code="entity:read",
            description="Read entities"
        )
        assert permission.code == "entity:read"


class TestTenantService:
    @pytest.mark.asyncio
    async def test_list_tenants_empty(self):
        """Test listing tenants returns empty when no data"""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        
        from services.identity.repositories import TenantRepository
        repo = TenantRepository(db)
        tenants = await repo.list(limit=20, offset=0)
        
        assert isinstance(tenants, list)
        assert len(tenants) == 0
    
    @pytest.mark.asyncio
    async def test_get_tenant_by_code_not_found(self):
        """Test getting a tenant by code that doesn't exist"""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        
        from services.identity.repositories import TenantRepository
        repo = TenantRepository(db)
        result = await repo.get_by_code("nonexistent")
        
        assert result is None


class TestAuthService:
    def test_create_access_token(self):
        """Test JWT access token creation"""
        from services.identity.services.auth_service import AuthService
        auth_service = AuthService()
        token = auth_service.create_access_token({"sub": str(uuid.uuid4())})
        
        assert token is not None
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        from services.identity.services.auth_service import AuthService
        auth_service = AuthService()
        token = auth_service.create_refresh_token({"sub": str(uuid.uuid4())})
        
        assert token is not None
        assert len(token) > 0
    
    def test_verify_valid_token(self):
        """Test token verification"""
        from services.identity.services.auth_service import AuthService
        auth_service = AuthService()
        token = auth_service.create_access_token({"sub": str(uuid.uuid4())})
        payload = auth_service.verify_token(token)
        
        assert "sub" in payload
        assert "exp" in payload
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        from services.identity.services.auth_service import AuthService
        auth_service = AuthService()
        with pytest.raises(ValueError):
            auth_service.verify_token("invalid.token.here")

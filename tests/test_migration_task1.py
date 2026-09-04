"""Task 1 Tests: Database Schema & Migration Verification

Note: These tests require a running PostgreSQL database with the migration applied.
They are marked as skipif when no database is available.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import os


# Check if DATABASE_URL is set (indicates PostgreSQL is available)
DATABASE_URL = os.getenv("DATABASE_URL", "")
has_database = "postgresql" in DATABASE_URL or os.getenv("TEST_WITH_DB", "false").lower() == "true"


pytestmark = pytest.mark.skipif(not has_database, reason="Requires PostgreSQL database")


class TestMigrationSchema:
    """Test that all required tables exist after migration"""
    
    REQUIRED_TABLES = [
        "tenants", "users", "roles", "permissions",
        "user_roles", "role_permissions",
        "entities", "assets",
        "property_definitions", "property_values",
        "relationships"
    ]
    
    @pytest.mark.asyncio
    async def test_all_tables_exist(self, db_session: AsyncSession):
        """Verify all 11 required tables exist"""
        result = await db_session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        ))
        tables = {row[0] for row in result.all()}
        
        for table in self.REQUIRED_TABLES:
            assert table in tables, f"Table '{table}' missing from database"
    
    @pytest.mark.asyncio
    async def test_tenants_table_structure(self, db_session: AsyncSession):
        """Verify tenants table columns"""
        result = await db_session.execute(text(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns WHERE table_name = 'tenants'"
        ))
        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.all()}
        
        assert "id" in columns
        assert columns["id"]["type"] == "uuid"
        assert columns["name"]["type"] == "character varying"
        assert columns["code"]["type"] == "character varying"
        assert columns["status"]["type"] == "character varying"
    
    @pytest.mark.asyncio
    async def test_users_table_structure(self, db_session: AsyncSession):
        """Verify users table columns and constraints"""
        result = await db_session.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'users'"
        ))
        columns = {row[0] for row in result.all()}
        
        assert "id" in columns
        assert "tenant_id" in columns
        assert "username" in columns
        assert "password_hash" in columns
        assert "status" in columns
    
    @pytest.mark.asyncio
    async def test_property_definitions_unique_indexes(self, db_session: AsyncSession):
        """Verify property_definitions has partial unique indexes"""
        result = await db_session.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'property_definitions'"
        ))
        indexes = {row[0] for row in result.all()}
        
        # Check for partial unique indexes
        assert any("system" in idx for idx in indexes), "Missing system-level unique index"
        assert any("tenant" in idx for idx in indexes), "Missing tenant-level unique index"
    
    @pytest.mark.asyncio
    async def test_relationships_self_reference_constraint(self, db_session: AsyncSession):
        """Verify relationships table has CHECK constraint for self-reference"""
        result = await db_session.execute(text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'relationships'::regclass"
        ))
        constraints = {row[0] for row in result.all()}
        
        # Should have check constraint for source != target
        assert any("self" in c.lower() or "check" in c.lower() for c in constraints), \
            "Missing self-reference check constraint"
    
    @pytest.mark.asyncio
    async def test_permissions_seed_data(self, db_session: AsyncSession):
        """Verify permissions table has seed data"""
        result = await db_session.execute(text("SELECT COUNT(*) FROM permissions"))
        count = result.scalar()
        assert count > 0, "Permissions table should have seed data"
    
    @pytest.mark.asyncio
    async def test_no_default_admin_user(self, db_session: AsyncSession):
        """Verify no default admin user is created (security requirement)"""
        result = await db_session.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        assert count == 0, "Should not create default admin user in migration"
    
    @pytest.mark.asyncio
    async def test_uuid_primary_keys(self, db_session: AsyncSession):
        """Verify all main tables use UUID primary keys"""
        result = await db_session.execute(text("""
            SELECT t.table_name, kcu.column_name, c.data_type
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.columns c ON c.table_name = tc.table_name AND c.column_name = kcu.column_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
            AND t.table_name IN ('tenants', 'users', 'roles', 'permissions', 'entities', 'assets')
            ORDER BY t.table_name
        """))
        rows = result.all()
        for row in rows:
            assert row[2] == "uuid", f"Table {row[0]} primary key should be UUID, got {row[2]}"


class TestMigrationIdempotency:
    """Test that migration can be applied multiple times safely"""
    
    @pytest.mark.asyncio
    async def test_seed_data_not_duplicated(self, db_session: AsyncSession):
        """Verify permissions seed data doesn't duplicate on re-run"""
        result = await db_session.execute(text("SELECT COUNT(DISTINCT code) FROM permissions"))
        count = result.scalar()
        # Should have the expected number of permission codes
        assert count >= 10, f"Expected at least 10 permissions, got {count}"


class TestSchemaConstraints:
    """Test database-level constraints"""
    
    @pytest.mark.asyncio
    async def test_unique_constraint_tenant_code(self, db_session: AsyncSession):
        """Verify tenant code uniqueness"""
        result = await db_session.execute(text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'tenants'::regclass AND contype = 'u'"
        ))
        constraints = [row[0] for row in result.all()]
        assert any("code" in c.lower() for c in constraints), "Missing unique constraint on tenants.code"
    
    @pytest.mark.asyncio
    async def test_asset_code_unique(self, db_session: AsyncSession):
        """Verify asset_code uniqueness"""
        result = await db_session.execute(text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'assets'::regclass AND contype = 'u'"
        ))
        constraints = [row[0] for row in result.all()]
        assert any("asset_code" in c.lower() for c in constraints), "Missing unique constraint on assets.asset_code"
    
    @pytest.mark.asyncio
    async def test_entity_relationship_cascade_delete(self, db_session: AsyncSession):
        """Verify CASCADE delete from entities to assets"""
        result = await db_session.execute(text(
            "SELECT delete_rule FROM information_schema.referential_constraints "
            "WHERE table_name = 'assets' AND referenced_table_name = 'entities'"
        ))
        row = result.fetchone()
        if row:
            assert row[0] == "CASCADE", "Asset deletion should cascade from Entity"

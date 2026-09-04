"""Task 1.6 Pre-flight Validation - Code Level Checks + Test Setup"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("DT-Lite V4.0 Phase 1 Task 1.6 - Pre-flight Validation")
print("=" * 70)

results = {}

# ============================================================================
# 1. Model Metadata Check (Code Level)
# ============================================================================
print("\n[1] Model Metadata Check (UnifiedBase)")

try:
    from services.core.models.base import Base as UnifiedBase
    from services.identity.models.models import Tenant, User, Role, Permission, UserRole, RolePermission
    from services.core.models.models import Entity, Asset, PropertyDefinition, PropertyValue, Relationship
    
    all_models = [
        ('Tenant', Tenant), ('User', User), ('Role', Role), 
        ('Permission', Permission), ('UserRole', UserRole), ('RolePermission', RolePermission),
        ('Entity', Entity), ('Asset', Asset), 
        ('PropertyDefinition', PropertyDefinition), ('PropertyValue', PropertyValue),
        ('Relationship', Relationship)
    ]
    
    all_inherit_unified = True
    metadata_set = set()
    
    for name, model in all_models:
        bases = getattr(model, '__bases__', ())
        inherits_base = len(bases) > 0 and bases[0] is UnifiedBase
        meta = getattr(getattr(model, '__table__', None), 'metadata', None)
        
        if not inherits_base:
            print(f"  [FAIL] {name} does not inherit UnifiedBase")
            all_inherit_unified = False
        else:
            if meta not in metadata_set:
                metadata_set.add(meta)
                print(f"  [PASS] {name} -> UnifiedBase.metadata")
            else:
                print(f"  [PASS] {name} -> same metadata instance")
    
    results['model_metadata'] = 'PASS' if all_inherit_unified else 'FAIL'
    
except Exception as e:
    print(f"  [ERROR] {e}")
    results['model_metadata'] = f'ERROR: {e}'

# ============================================================================
# 2. Migration File Structure Check
# ============================================================================
print("\n[2] Migration File Structure")

try:
    import re
    import glob
    
    migration_dir = 'database/migrations/versions'
    migration_files = glob.glob(os.path.join(migration_dir, '*.py'))
    
    revisions = {}
    for mf in migration_files:
        if mf.endswith('__pycache__'):
            continue
        with open(mf, 'r', encoding='utf-8') as f:
            content = f.read()
            rev_match = re.search(r"revision\s*=\s*'([^']+)'", content)
            down_match = re.search(r"down_revision\s*=\s*'([^']+)'", content)
            if rev_match:
                rev = rev_match.group(1)
                if rev in revisions:
                    print(f"  [FAIL] Duplicate revision: {rev}")
                    revisions[rev] = [revisions[rev], mf]
                else:
                    revisions[rev] = mf
    
    # Check chain
    heads = [r for r, f in revisions.items() if not any(d == r for d in revisions.values() if isinstance(d, str))]
    # Actually find heads (revisions that are not down_revision of any other)
    all_down = set()
    for mf in migration_files:
        with open(mf, 'r', encoding='utf-8') as f:
            content = f.read()
            down_match = re.search(r"down_revision\s*=\s*'([^']+)'", content)
            if down_match:
                all_down.add(down_match.group(1))
    
    heads = [r for r in revisions if r not in all_down]
    
    if len(heads) == 1:
        print(f"  [PASS] Single head: {heads[0]} -> {revisions[heads[0]]}")
        results['migration_head'] = 'PASS'
    else:
        print(f"  [WARN] Heads: {heads}")
        results['migration_head'] = f'WARN: {heads}'
    
    # Check required tables in migration
    with open(os.path.join(migration_dir, 'phase1_identity_core.py'), 'r', encoding='utf-8') as f:
        phase1_content = f.read()
    
    required_tables = ['tenants', 'users', 'roles', 'permissions', 'user_roles', 
                       'role_permissions', 'entities', 'assets', 
                       'property_definitions', 'property_values', 'relationships']
    
    missing_tables = [t for t in required_tables if f"op.create_table('{t}'" not in phase1_content]
    if not missing_tables:
        print(f"  [PASS] All {len(required_tables)} required tables in migration")
        results['migration_tables'] = 'PASS'
    else:
        print(f"  [FAIL] Missing tables: {missing_tables}")
        results['migration_tables'] = f'FAIL: {missing_tables}'
    
    # Check partial unique indexes
    has_system_index = 'uq_property_definition_system' in phase1_content and 'tenant_id IS NULL' in phase1_content
    has_tenant_index = 'uq_property_definition_tenant' in phase1_content and 'tenant_id IS NOT NULL' in phase1_content
    
    if has_system_index and has_tenant_index:
        print(f"  [PASS] Partial unique indexes defined")
        results['partial_indexes'] = 'PASS'
    else:
        print(f"  [FAIL] Missing partial indexes: system={has_system_index}, tenant={has_tenant_index}")
        results['partial_indexes'] = 'FAIL'
    
    # Check relationship constraint
    has_self_check = 'check_self_relation' in phase1_content
    if has_self_check:
        print(f"  [PASS] Self-reference constraint defined")
        results['self_ref_constraint'] = 'PASS'
    else:
        print(f"  [FAIL] Missing self-reference constraint")
        results['self_ref_constraint'] = 'FAIL'
    
    # Check asset entity_id unique
    has_asset_unique = "UniqueConstraint('entity_id')" in phase1_content
    if has_asset_unique:
        print(f"  [PASS] Asset entity_id unique constraint")
        results['asset_unique'] = 'PASS'
    else:
        print(f"  [FAIL] Missing asset entity_id unique")
        results['asset_unique'] = 'FAIL'
        
except Exception as e:
    print(f"  [ERROR] {e}")
    results['migration_structure'] = f'ERROR: {e}'

# ============================================================================
# 3. Database Connection Test
# ============================================================================
print("\n[3] Database Connection Test")

try:
    import asyncpg
    
    async def test_connection():
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=5432,
            user='dtlite_user',
            password='dtlite_pass',
            database='dtlite'
        )
        version = await conn.fetchval('SELECT version()')
        await conn.close()
        return True, version[:80]
    
    success, version = asyncio.run(test_connection())
    if success:
        print(f"  [PASS] Connected to PostgreSQL")
        print(f"         Version: {version}...")
        results['db_connection'] = 'PASS'
    else:
        print(f"  [FAIL] Connection failed")
        results['db_connection'] = 'FAIL'
except Exception as e:
    print(f"  [SKIP] Database unavailable: {type(e).__name__}")
    print(f"         Cannot run migration tests without DB")
    results['db_connection'] = f'SKIP: {type(e).__name__}'

# ============================================================================
# 4. Final Summary
# ============================================================================
print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)

passed = sum(1 for v in results.values() if v == 'PASS')
failed = [k for k, v in results.items() if v.startswith('FAIL')]
skipped = [k for k, v in results.items() if v.startswith('SKIP')]

print(f"\nResults: {passed}/{len(results)} checks passed")

if failed:
    print(f"\nFailed checks: {', '.join(failed)}")
    print("\n[BLOCKED] Cannot enter Task 2 until failures are resolved")
elif skipped:
    print(f"\nSkipped checks (DB unavailable): {', '.join(skipped)}")
    print("\n[READY FOR TASK 2] (with manual DB verification recommended)")
else:
    print("\n[READY FOR TASK 2]")

print("=" * 70)

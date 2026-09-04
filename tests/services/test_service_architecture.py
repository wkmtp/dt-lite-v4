"""
Architecture Boundary Tests - Ensures Service Layer does not directly access database.
"""
import re
from pathlib import Path



# Patterns that indicate direct database access in Service layer
VIOLATION_PATTERNS = [
    r'\bsession\.query\b',
    r'\bselect\s*\(',
    r'\.execute\(',
    r'\.insert\s*\(',
    r'\.delete\s*\(.*where',
    r'\.update\s*\(.*where',
]

# Exempt files/directories (repositories, ORM models, API routes, legacy code)
EXEMPT_PATTERNS = [
    r'repositories[\\/]?',
    r'models[\\/]?',
    r'__init__',
    r'api[\\/]routes',
    r'/auth\.py$',
    r'repositories\.py$',
    r'core_service\.py$',  # Legacy service file from earlier phase
]


def _is_exempt(filepath: Path) -> bool:
    """Check if file should be exempt from architecture checks."""
    for pattern in EXEMPT_PATTERNS:
        if re.search(pattern, str(filepath)):
            return True
    return False


def _check_service_file(filepath: Path) -> list[str]:
    """Check a single service file for violations."""
    violations = []
    if _is_exempt(filepath):
        return violations

    try:
        content = filepath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return violations

    lines = content.splitlines()
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        for pattern in VIOLATION_PATTERNS:
            if re.search(pattern, line):
                violations.append(f"{filepath.name}:{line_num} - {stripped[:80]}")
                break

    return violations


class TestServiceArchitectureBoundary:
    """Tests to enforce Service Layer architecture boundaries."""

    def test_no_direct_database_access_in_task3_services(self):
        """Task 3 service files must not contain direct database access patterns."""
        services_dir = Path(__file__).parent.parent.parent / 'services'

        # Only check Task 3 service files (core services + identity services)
        target_dirs = [
            services_dir / 'core' / 'services',
            services_dir / 'identity' / 'services',
        ]

        service_files = []
        for d in target_dirs:
            if d.exists():
                service_files.extend(d.rglob('*.py'))

        # Exclude pre-existing non-Task-3 files
        exclude_names = {'auth_service.py', 'core_service.py'}

        all_violations = {}
        for filepath in service_files:
            if filepath.name in exclude_names:
                continue
            if _is_exempt(filepath):
                continue
            violations = _check_service_file(filepath)
            if violations:
                all_violations[filepath] = violations

        if all_violations:
            msg = "Direct DB access found in Task 3 services:"
            for fp, vs in all_violations.items():
                for v in vs:
                    msg += f"\n  {fp.name}:{v}"
            raise AssertionError(msg)

    def test_tasks3_services_exist_and_use_uow(self):
        """All Task 3 services must exist and use UnitOfWork."""
        services_dir = Path(__file__).parent.parent.parent / 'services'

        expected_services = {
            'core/services': ['entity_service.py', 'asset_service.py',
                             'property_service.py', 'relationship_service.py'],
            'identity/services': ['tenant_service.py', 'user_service.py',
                                  'role_service.py', 'permission_service.py'],
        }

        for sub_dir, svc_files in expected_services.items():
            base = services_dir / sub_dir.replace('/', '\\')
            for svc in svc_files:
                filepath = base / svc
                assert filepath.exists(), f"Expected {svc} not found at {filepath}"

                content = filepath.read_text(encoding='utf-8')
                assert '_uow' in content or 'uow' in content, \
                    f"{svc} should use UnitOfWork"

"""Task 11 Architecture Dependency Scan — Enforce Phase 2 Extension Boundary."""
import inspect
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "services", "template")

FORBIDDEN_IMPORTS = [
    "services.adapter",
    "services.telemetry.runtime",
    "services.twin.models",
    "services.iot",
]

FORBIDDEN_KEYWORDS = [
    "bacnet",
    "modbus",
    "mqtt",
    "opcua",
    "plc",
    "bim",
    "three.js",
]


class TestArchitectureDependencyScan:
    """Test that template module has no forbidden dependencies."""

    def _scan_for_imports(self, forbidden: list[str]) -> list[str]:
        """Scan template module for forbidden imports."""
        violations = []
        for root, dirs, files in os.walk(TEMPLATE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                for imp in forbidden:
                    if imp in content:
                        violations.append(f"{filepath}: {imp}")
        return violations

    def test_no_adapter_imports(self):
        """Verify no imports from services.adapter in template module."""
        violations = self._scan_for_imports(FORBIDDEN_IMPORTS)
        assert not violations, f"Found forbidden imports: {violations}"

    def test_no_protocol_keywords(self):
        """Verify no protocol keywords in template module."""
        violations = []
        for root, dirs, files in os.walk(TEMPLATE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in FORBIDDEN_KEYWORDS:
                    if kw.lower() in content:
                        violations.append(f"{filepath}: found '{kw}'")
        assert not violations, f"Found protocol keywords: {violations}"

    def test_no_infra_imports(self):
        """Verify no infrastructure imports in template module."""
        violations = []
        for root, dirs, files in os.walk(TEMPLATE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for kw in ["kafka", "redis", "celery"]:
                    if kw in content:
                        violations.append(f"{filepath}: found '{kw}'")
        assert not violations, f"Found infra imports: {violations}"

    def test_no_graph_database_dependency(self):
        """Verify no Neo4j or NetworkX dependencies."""
        violations = []
        for root, dirs, files in os.walk(TEMPLATE_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                for lib in ["neo4j", "networkx"]:
                    if lib in content:
                        violations.append(f"{filepath}: found '{lib}'")
        assert not violations, f"Found graph DB dependencies: {violations}"

    def test_allows_core_and_identity_imports(self):
        """Verify template correctly imports from allowed modules."""
        from services.template.repositories import TemplateRepository
        from services.core.repositories.base import TenantAwareRepository
        assert issubclass(TemplateRepository, TenantAwareRepository)

    def test_service_has_zero_sql_execution(self):
        """Verify service layer contains no direct SQL execution."""
        from services.template.services import TemplateService

        source = inspect.getsource(TemplateService)
        assert "session.execute" not in source, "Service must not call session.execute()"
        assert ".execute(" not in source, "Service must not execute direct queries"

    def test_repository_uses_tenant_aware_pattern(self):
        """Verify repository extends TenantAwareRepository."""
        from services.template.repositories import TemplateRepository
        from services.core.repositories.base import TenantAwareRepository

        assert issubclass(TemplateRepository, TenantAwareRepository)

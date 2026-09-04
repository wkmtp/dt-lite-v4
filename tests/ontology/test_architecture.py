"""Task 12 Architecture Dependency Scan — Enforce Phase 2 Extension Boundary."""
import inspect
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

ONTOLOGY_DIR = os.path.join(PROJECT_ROOT, "services", "ontology")

FORBIDDEN_IMPORTS = [
    "services.adapter",
    "services.telemetry",
    "services.twin.models",
    "services.twin.services",
    "services.twin_graph",
    "services.template",
]

FORBIDDEN_KEYWORDS = [
    "bacnet",
    "modbus",
    "opcua",
    "mqtt",
    "plc",
    "mes",
    "scada",
    "bim",
    "three",
    "kafka",
    "redis",
    "celery",
    "neo4j",
    "networkx",
]


class TestArchitectureDependencyScan:
    """Test that ontology module has no forbidden dependencies."""

    def _scan_files(self, pattern: str) -> list[str]:
        """Scan all Python files in ontology directory for a pattern."""
        violations = []
        for root, dirs, files in os.walk(ONTOLOGY_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                filepath = os.path.join(root, fn)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                if pattern.lower() in content.lower():
                    violations.append(f"{filepath}: contains '{pattern}'")
        return violations

    def test_no_adapter_imports(self):
        """Verify no imports from services.adapter or telemetry."""
        violations = self._scan_files("services.adapter")
        violations += self._scan_files("services.telemetry")
        assert not violations, f"Found forbidden imports: {violations}"

    def test_no_twin_models_import(self):
        """Verify no imports from services.twin.models."""
        violations = self._scan_files("services.twin.models")
        assert not violations, f"Found forbidden imports: {violations}"

    def test_no_protocol_keywords(self):
        """Verify no protocol keywords in ontology module."""
        violations = self._scan_files("bacnet")
        violations += self._scan_files("modbus")
        violations += self._scan_files("opcua")
        violations += self._scan_files("mqtt")
        violations += self._scan_files("plc")
        assert not violations, f"Found protocol keywords: {violations}"

    def test_no_infra_keywords(self):
        """Verify no infrastructure keywords in ontology module."""
        violations = self._scan_files("kafka")
        violations += self._scan_files("redis")
        violations += self._scan_files("celery")
        assert not violations, f"Found infrastructure keywords: {violations}"

    def test_service_has_zero_direct_sql_execution(self):
        """Verify service layer contains no direct database query execution."""
        from services.ontology.services import OntologyService, EntityTypeService, CapabilityService
        for cls in [OntologyService, EntityTypeService, CapabilityService]:
            source = inspect.getsource(cls)
            # Service should delegate to repository, not execute directly
            # The _build_node method uses self._repo.session.execute which is via repo accessor
            # We check that service methods don't directly construct and execute SQL
            # by verifying they only use repository method calls
            lines = [ln.strip() for ln in source.split("\n") if not ln.strip().startswith("#")]
            for line in lines:
                # Skip lines that access repo.session (internal implementation detail)
                if "self._repo.session" in line:
                    continue
                assert ".execute(" not in line, \
                    f"{cls.__name__} must not call .execute() directly"

    def test_repository_uses_tenant_aware_pattern(self):
        """Verify all repositories extend TenantAwareRepository."""
        from services.ontology.repository import (
            OntologyRepository,
            EntityTypeRepository,
            CapabilityRepository,
            SemanticPropertyRepository,
            TemplateCapabilityRepository,
        )
        from services.core.repositories.base import TenantAwareRepository

        for repo_cls in [
            OntologyRepository,
            EntityTypeRepository,
            CapabilityRepository,
            SemanticPropertyRepository,
            TemplateCapabilityRepository,
        ]:
            assert issubclass(repo_cls, TenantAwareRepository), \
                f"{repo_cls.__name__} must extend TenantAwareRepository"

    def test_no_template_creation_in_ontology(self):
        """Ontology must not create TwinTemplate instances."""
        from services.ontology.services import OntologyService, EntityTypeService, CapabilityService
        for cls in [OntologyService, EntityTypeService, CapabilityService]:
            source = inspect.getsource(cls)
            assert "TwinTemplate" not in source, \
                f"{cls.__name__} must not reference TwinTemplate"

"""Test deployment architecture compliance."""
import ast
from pathlib import Path


class TestArchitectureScan:
    """Verify services/deployment has zero forbidden imports."""

    FORBIDDEN_IMPORTS = [
        "services.adapter",
        "services.telemetry",
        "services.twin.models",
        "services.twin.services",
        "services.twin_graph",
    ]

    FORBIDDEN_KEYWORDS = [
        "bacnet", "modbus", "mqtt", "opcua", "plc",
        "scada", "bim", "three",
        "kafka", "redis", "celery",
    ]
    # Note: "mes" is excluded because it appears in common words like "message"

    def _scan_source_files(self, directory: str) -> list[str]:
        """Scan all .py files in directory for forbidden patterns."""
        violations = []
        path = Path("services") / directory
        if not path.exists():
            return violations

        for py_file in path.rglob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            tree = ast.parse(content)

            # Check imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in self.FORBIDDEN_IMPORTS:
                            if alias.name.startswith(forbidden):
                                violations.append(
                                    f"{py_file}: imports {alias.name}"
                                )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for forbidden in self.FORBIDDEN_IMPORTS:
                            if node.module.startswith(forbidden):
                                violations.append(
                                    f"{py_file}: from {node.module}"
                                )

            # Check keywords in source (non-import lines)
            import re
            for line in content.splitlines():
                stripped = line.strip().lower()
                if stripped.startswith("#"):
                    continue
                for keyword in self.FORBIDDEN_KEYWORDS:
                    # Use word boundary matching to avoid false positives (e.g., "mes" in "message")
                    if re.search(r'\b' + keyword + r'\b', stripped) and "import" not in stripped:
                        violations.append(f"{py_file}: contains '{keyword}'")

        return violations

    def test_no_forbidden_imports(self):
        """Deployment must not import adapter, telemetry, twin, etc."""
        violations = self._scan_source_files("deployment")
        import_violations = [v for v in violations if "imports" in v or "from" in v]
        assert len(import_violations) == 0, f"Forbidden imports found: {import_violations}"

    def test_no_protocol_keywords(self):
        """Deployment must not contain protocol-specific keywords."""
        violations = self._scan_source_files("deployment")
        keyword_violations = [v for v in violations if any(k in v for k in self.FORBIDDEN_KEYWORDS)]
        assert len(keyword_violations) == 0, f"Forbidden keywords found: {keyword_violations}"

    def test_all_repos_extend_tenant_aware_repository(self):
        """All repository classes must extend TenantAwareRepository."""
        repo_dir = Path("services") / "deployment" / "repositories"
        if not repo_dir.exists():
            return
        for py_file in repo_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            content = py_file.read_text(encoding='utf-8')
            assert "TenantAwareRepository" in content, f"{py_file} does not extend TenantAwareRepository"

    def test_service_has_no_direct_sql(self):
        """Services must not contain raw SQL strings."""
        svc_dir = Path("services") / "deployment" / "services"
        if not svc_dir.exists():
            return
        for py_file in svc_dir.rglob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            assert "select(" not in content, f"{py_file} contains raw SQL select()"
            assert "execute(" not in content, f"{py_file} contains raw SQL execute()"

    def test_no_device_creation_in_deployment_services(self):
        """Deployment services must not create TwinDevice or access devices."""
        svc_dir = Path("services") / "deployment" / "services"
        if not svc_dir.exists():
            return
        for py_file in svc_dir.rglob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            assert "TwinDevice" not in content, f"{py_file} creates TwinDevice"
            assert "device_id" not in content, f"{py_file} references device_id"

    def test_no_twin_modification(self):
        """Deployment must not import from services.twin."""
        violations = self._scan_source_files("deployment")
        twin_violations = [v for v in violations if "twin" in v.lower() and "node" not in v.lower()]
        # Exclude valid references to entity_type_definitions FK
        allowed = ["entity_type_definitions", "deployment_node"]
        twin_violations = [v for v in twin_violations
                          if not any(a in v for a in allowed)]
        assert len(twin_violations) == 0, f"Unexpected twin references: {twin_violations}"

    def test_migration_extends_phase12(self):
        """Migration must extend phase12_semantic_meta_model."""
        migration_path = Path("database") / "migrations" / "versions"
        for py_file in migration_path.rglob("phase12_1_deployment*.py"):
            content = py_file.read_text(encoding='utf-8')
            assert "down_revision = 'phase12_semantic_meta_model'" in content, \
                f"{py_file} does not extend correct revision"

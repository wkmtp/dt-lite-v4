"""Test provisioning architecture compliance."""
import ast
from pathlib import Path
import re


class TestArchitectureScan:
    """Verify services/provisioning has zero forbidden imports."""

    FORBIDDEN_IMPORTS = [
        "services.adapter",
        "services.telemetry",
        "services.adapter.*",
        "services.telemetry.*",
        "services.bacnet",
        "services.modbus",
        "services.mqtt",
        "services.opcua",
        "services.plc",
        "services.ai",
        "services.kafka",
        "services.redis",
    ]
    # NOTE: services.twin.models.entity (PersistentTwinEntity) and services.twin_graph.* are ALLOWED
    # as they are part of the Twin persistence layer that provisioning bridges to.

    FORBIDDEN_KEYWORDS = [
        "bacnet", "modbus", "mqtt", "opcua", "plc",
        "kafka", "redis", "celery",
    ]

    def test_no_forbidden_imports(self):
        """Provisioning must not import adapter, telemetry, etc."""
        violations = []
        for py_file in Path("services/provisioning").rglob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in self.FORBIDDEN_IMPORTS:
                            if alias.name.startswith(forbidden):
                                violations.append(f"{py_file}: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for forbidden in self.FORBIDDEN_IMPORTS:
                            if node.module.startswith(forbidden):
                                violations.append(f"{py_file}: {node.module}")
        assert len(violations) == 0, f"Forbidden imports found: {violations}"

    def test_no_protocol_keywords(self):
        """Provisioning must not contain protocol-specific keywords."""
        violations = []
        for py_file in Path("services/provisioning").rglob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            for line in content.splitlines():
                stripped = line.strip().lower()
                if stripped.startswith("#"):
                    continue
                for keyword in self.FORBIDDEN_KEYWORDS:
                    if re.search(r'\b' + keyword + r'\b', stripped):
                        violations.append(f"{py_file}: '{keyword}'")
        assert len(violations) == 0, f"Forbidden keywords found: {violations}"

    def test_migration_chain_correct(self):
        """Migration must extend phase12_1_deployment_meta."""
        migration_path = Path("database/migrations/versions")
        found = False
        for py_file in migration_path.rglob("phase13_provisioning*.py"):
            content = py_file.read_text(encoding='utf-8')
            assert "down_revision = 'phase12_1_deployment_meta'" in content
            found = True
        assert found, "phase13_provisioning.py not found"

    def test_gateway_integrates_provisioning_router(self):
        """Gateway main.py must include provisioning_router."""
        gateway_path = Path("services/gateway/main.py")
        content = gateway_path.read_text(encoding='utf-8')
        assert "provisioning_router" in content
        assert 'from services.provisioning.routes import router as provisioning_router' in content

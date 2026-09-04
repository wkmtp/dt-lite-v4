"""
Base test configuration for DT-Lite services
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for API testing"""
    from services.gateway.main import app
    return TestClient(app)

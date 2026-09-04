"""
Gateway Service Tests
"""
import pytest
from fastapi.testclient import TestClient
from services.gateway.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_health(self):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_api_health(self):
        """Test /api/v1/health endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["service"] == "DT-Lite Gateway"


class TestRootEndpoint:
    def test_root(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "DT-Lite Gateway"
        assert data["version"] == "4.0.0"
        assert data["status"] == "running"


class TestProxyRouting:
    def test_proxy_routing(self):
        """Test proxy routing returns placeholder"""
        response = client.get("/api/v1/test/path")
        # Proxy routes are not yet configured, returns 404
        assert response.status_code in [200, 404]

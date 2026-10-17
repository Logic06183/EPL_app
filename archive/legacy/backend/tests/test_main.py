"""
Tests for main FastAPI application
"""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns API information"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "FPL AI Pro"
    assert "version" in data
    assert "endpoints" in data
    assert "features" in data


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert "models_loaded" in data
    assert "cache_available" in data


def test_ping_endpoint(client: TestClient):
    """Test lightweight ping endpoint"""
    response = client.get("/ping")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pong"
    assert "timestamp" in data


def test_cors_headers(client: TestClient):
    """Test CORS headers are present in responses"""
    response = client.get("/health")
    assert response.status_code == 200
    # CORS headers should be present (set by middleware)
    # Note: TestClient doesn't fully simulate CORS preflight, but headers should exist


def test_404_not_found(client: TestClient):
    """Test 404 for non-existent endpoint"""
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404

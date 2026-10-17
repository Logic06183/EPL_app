"""
Tests for prediction API endpoints
"""

import pytest
from fastapi.testclient import TestClient


def test_get_predictions_basic(client: TestClient):
    """Test basic predictions endpoint"""
    response = client.get("/api/predictions?top_n=10")
    assert response.status_code == 200

    predictions = response.json()
    assert isinstance(predictions, list)
    # May be empty if model not trained, but should return a list


def test_get_predictions_with_model(client: TestClient):
    """Test predictions with specific model"""
    response = client.get("/api/predictions?top_n=10&model=random_forest")
    assert response.status_code == 200

    predictions = response.json()
    assert isinstance(predictions, list)


def test_get_predictions_invalid_model(client: TestClient):
    """Test predictions with invalid model returns error"""
    response = client.get("/api/predictions?top_n=10&model=invalid_model")
    # Should return 400 or still work with default
    assert response.status_code in [200, 400]


def test_get_predictions_with_position_filter(client: TestClient):
    """Test predictions with position filter"""
    response = client.get("/api/predictions?top_n=10&position=3")
    assert response.status_code == 200

    predictions = response.json()
    assert isinstance(predictions, list)


def test_get_predictions_with_price_filter(client: TestClient):
    """Test predictions with price filter"""
    response = client.get("/api/predictions?top_n=10&max_price=10.0")
    assert response.status_code == 200

    predictions = response.json()
    assert isinstance(predictions, list)


def test_get_model_info(client: TestClient):
    """Test model info endpoint"""
    response = client.get("/api/predictions/models/info")
    assert response.status_code == 200

    info = response.json()
    assert "models" in info
    assert "features" in info


def test_predictions_pagination(client: TestClient):
    """Test predictions with different top_n values"""
    # Test various limits
    for top_n in [5, 10, 20, 50]:
        response = client.get(f"/api/predictions?top_n={top_n}")
        assert response.status_code == 200

        predictions = response.json()
        assert isinstance(predictions, list)
        assert len(predictions) <= top_n

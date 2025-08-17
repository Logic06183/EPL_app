"""
Comprehensive test suite for FPL AI Pro API
Tests all major endpoints, security, performance, and edge cases
"""

import pytest
import asyncio
import httpx
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api_production import app, fpl_manager, ai_predictor, multi_model_predictor
from security_utils import rate_limiter, security_validator
from performance_utils import performance_monitor, async_cache

@pytest.fixture
async def client():
    """Create test client"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def valid_token():
    """Valid test token"""
    return "demo_token"

@pytest.fixture
def invalid_token():
    """Invalid test token"""
    return "invalid_token_123"

class TestHealthAndStatus:
    """Test health check and status endpoints"""
    
    async def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "operational"
    
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert data["status"] == "healthy"
    
    async def test_api_test_endpoint(self, client):
        """Test API test endpoint"""
        response = await client.get("/api/test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "timestamp" in data
        assert "environment_variables" in data

class TestAuthentication:
    """Test authentication and security"""
    
    async def test_valid_token_authentication(self, client, valid_token):
        """Test valid token authentication"""
        headers = {"Authorization": f"Bearer {valid_token}"}
        response = await client.get("/api/models/available", headers=headers)
        assert response.status_code == 200
    
    async def test_invalid_token_authentication(self, client, invalid_token):
        """Test invalid token authentication"""
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = await client.get("/api/models/available", headers=headers)
        assert response.status_code == 401
    
    async def test_missing_token(self, client):
        """Test missing token"""
        response = await client.get("/api/models/available")
        assert response.status_code == 403  # FastAPI security dependency returns 403
    
    async def test_malformed_token(self, client):
        """Test malformed authorization header"""
        headers = {"Authorization": "InvalidFormat"}
        response = await client.get("/api/models/available", headers=headers)
        assert response.status_code == 403

class TestPlayerPredictions:
    """Test player prediction endpoints"""
    
    async def test_get_player_predictions_basic(self, client):
        """Test basic player predictions without auth"""
        response = await client.get("/api/players/predictions?top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "total_players" in data
        assert len(data["predictions"]) <= 5
    
    async def test_get_player_predictions_with_ai(self, client):
        """Test AI-enhanced predictions"""
        response = await client.get("/api/players/predictions?use_ai=true&top_n=3")
        assert response.status_code == 200
        data = response.json()
        assert data["ai_enhanced"] is True
        assert len(data["predictions"]) <= 3
    
    async def test_get_player_predictions_by_position(self, client):
        """Test predictions filtered by position"""
        response = await client.get("/api/players/predictions?position=4&top_n=5")  # Forwards
        assert response.status_code == 200
        data = response.json()
        for prediction in data["predictions"]:
            assert prediction["position"] == 4
    
    async def test_get_player_predictions_ensemble_model(self, client):
        """Test ensemble model predictions"""
        response = await client.get("/api/players/predictions?model_type=ensemble&top_n=3")
        assert response.status_code == 200
        data = response.json()
        assert "model_type" in data
    
    async def test_search_players(self, client):
        """Test player search functionality"""
        response = await client.get("/api/players/search?q=Haaland")
        assert response.status_code == 200
        data = response.json()
        assert "players" in data
        # Should find Haaland in mock data
        assert len(data["players"]) > 0
    
    async def test_search_players_no_results(self, client):
        """Test player search with no results"""
        response = await client.get("/api/players/search?q=NonexistentPlayer123")
        assert response.status_code == 200
        data = response.json()
        assert "players" in data
        assert len(data["players"]) == 0

class TestPlayerAnalysis:
    """Test individual player analysis"""
    
    async def test_player_ai_analysis(self, client):
        """Test AI analysis for specific player"""
        response = await client.get("/api/players/1/ai-analysis")
        assert response.status_code == 200
        data = response.json()
        assert "player" in data
        assert "stats" in data
        assert "analysis" in data
        assert data["analysis"]["ai_enhanced"] is True
    
    async def test_player_ai_analysis_nonexistent(self, client):
        """Test AI analysis for non-existent player"""
        response = await client.get("/api/players/99999/ai-analysis")
        assert response.status_code == 404

class TestSquadOptimization:
    """Test squad optimization endpoints"""
    
    async def test_optimize_squad_default(self, client):
        """Test squad optimization with default budget"""
        response = await client.post("/api/optimize/squad", json={})
        assert response.status_code == 200
        data = response.json()
        assert "squad" in data
        assert "total_cost" in data
        assert "predicted_points" in data
        assert len(data["squad"]) <= 15
    
    async def test_optimize_squad_custom_budget(self, client):
        """Test squad optimization with custom budget"""
        response = await client.post("/api/optimize/squad", json={"budget": 120.0})
        assert response.status_code == 200
        data = response.json()
        assert data["total_cost"] <= 120.0
    
    async def test_optimize_squad_low_budget(self, client):
        """Test squad optimization with very low budget"""
        response = await client.post("/api/optimize/squad", json={"budget": 50.0})
        assert response.status_code == 200
        data = response.json()
        # Should still return some players within budget
        assert "squad" in data

class TestGameweekAndFixtures:
    """Test gameweek and fixture endpoints"""
    
    async def test_get_current_gameweek(self, client):
        """Test current gameweek endpoint"""
        response = await client.get("/api/gameweek/current")
        assert response.status_code == 200
        data = response.json()
        assert "gameweek" in data
        assert "name" in data
        assert "deadline" in data
    
    async def test_get_fixtures_today(self, client):
        """Test today's fixtures"""
        response = await client.get("/api/fixtures?filter=today")
        assert response.status_code == 200
        data = response.json()
        assert "fixtures" in data
        assert "filter" in data
        assert data["filter"] == "today"
    
    async def test_get_fixtures_upcoming(self, client):
        """Test upcoming fixtures"""
        response = await client.get("/api/fixtures?filter=upcoming")
        assert response.status_code == 200
        data = response.json()
        assert data["filter"] == "upcoming"
    
    async def test_get_live_fixtures(self, client):
        """Test live fixtures endpoint"""
        response = await client.get("/api/fixtures/live")
        assert response.status_code == 200
        data = response.json()
        assert "live_fixtures" in data
        assert "count" in data

class TestModelEndpoints:
    """Test AI model endpoints"""
    
    async def test_get_available_models(self, client):
        """Test available models endpoint"""
        response = await client.get("/api/models/available")
        assert response.status_code == 200
        data = response.json()
        assert "available_models" in data
        assert "current_system" in data
        assert "recommendation" in data
    
    async def test_prediction_history(self, client):
        """Test prediction history endpoint"""
        response = await client.get("/api/predictions/history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "accuracy" in data
    
    async def test_model_improvements(self, client):
        """Test model improvements endpoint"""
        response = await client.get("/api/models/improvements")
        assert response.status_code == 200
        data = response.json()
        assert "improvements" in data

class TestHybridForecasting:
    """Test hybrid forecasting endpoints"""
    
    async def test_hybrid_forecast(self, client):
        """Test hybrid forecast for specific match"""
        response = await client.get("/api/hybrid-forecast/Liverpool/Manchester%20City")
        assert response.status_code == 200
        data = response.json()
        assert "forecast" in data
        assert "match" in data
    
    async def test_match_predictions(self, client):
        """Test upcoming match predictions"""
        response = await client.get("/api/match-predictions?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) <= 5

class TestSecurity:
    """Test security features"""
    
    def test_rate_limiter(self):
        """Test rate limiting functionality"""
        # Test within limits
        assert rate_limiter.is_allowed("test_user", 10, 60) is True
        
        # Test rate limit exceeded
        for _ in range(10):
            rate_limiter.is_allowed("test_user_2", 1, 60)
        assert rate_limiter.is_allowed("test_user_2", 1, 60) is False
    
    def test_security_validator(self):
        """Test security validation utilities"""
        # Test API key validation
        assert security_validator.validate_api_key("short") is False
        assert security_validator.validate_api_key("a" * 32) is True
        
        # Test email validation
        assert security_validator.validate_email("test@example.com") is True
        assert security_validator.validate_email("invalid-email") is False
        
        # Test input sanitization
        dangerous_input = "<script>alert('xss')</script>"
        sanitized = security_validator.sanitize_input(dangerous_input)
        assert "<script>" not in sanitized

class TestPerformance:
    """Test performance monitoring"""
    
    def test_performance_monitor(self):
        """Test performance monitoring"""
        # Record some metrics
        performance_monitor.record_request("/test", 0.5, True)
        performance_monitor.record_request("/test", 1.5, True)
        performance_monitor.record_request("/test", 3.0, False)  # Slow request
        
        stats = performance_monitor.get_stats()
        assert stats["total_requests"] == 3
        assert stats["error_rate"] > 0
        assert stats["slow_request_rate"] > 0
    
    async def test_async_cache(self):
        """Test async cache functionality"""
        # Test cache miss
        value = await async_cache.get("nonexistent")
        assert value is None
        
        # Test cache set and hit
        await async_cache.set("test_key", {"data": "test_value"})
        value = await async_cache.get("test_key")
        assert value == {"data": "test_value"}
        
        # Test cache stats
        stats = async_cache.get_stats()
        assert stats["hit_count"] > 0
        assert stats["miss_count"] > 0

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    async def test_invalid_endpoint(self, client):
        """Test invalid endpoint"""
        response = await client.get("/nonexistent/endpoint")
        assert response.status_code == 404
    
    async def test_invalid_json_payload(self, client):
        """Test invalid JSON payload"""
        response = await client.post(
            "/api/optimize/squad",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    async def test_large_request_parameters(self, client):
        """Test large request parameters"""
        response = await client.get("/api/players/predictions?top_n=10000")
        assert response.status_code == 200
        # Should be limited by actual data size
    
    @patch('api_production.fpl_manager.get_bootstrap_data')
    async def test_fpl_api_failure(self, mock_get_data, client):
        """Test handling of FPL API failures"""
        mock_get_data.side_effect = Exception("FPL API unavailable")
        
        response = await client.get("/api/players/predictions")
        # Should return mock data gracefully
        assert response.status_code == 200

class TestDataValidation:
    """Test data validation"""
    
    async def test_prediction_data_validation(self, client):
        """Test that prediction data is properly validated"""
        response = await client.get("/api/players/predictions?top_n=1")
        assert response.status_code == 200
        
        data = response.json()
        prediction = data["predictions"][0]
        
        # Check required fields
        required_fields = ["id", "name", "predicted_points", "confidence", "price"]
        for field in required_fields:
            assert field in prediction
        
        # Check data types and ranges
        assert isinstance(prediction["predicted_points"], (int, float))
        assert 0 <= prediction["confidence"] <= 1
        assert prediction["price"] > 0

# Integration test that runs a full workflow
class TestIntegration:
    """Integration tests"""
    
    async def test_full_prediction_workflow(self, client):
        """Test complete prediction workflow"""
        # 1. Get available models
        models_response = await client.get("/api/models/available")
        assert models_response.status_code == 200
        
        # 2. Get predictions
        pred_response = await client.get("/api/players/predictions?use_ai=true&top_n=5")
        assert pred_response.status_code == 200
        
        predictions = pred_response.json()["predictions"]
        assert len(predictions) > 0
        
        # 3. Get detailed analysis for top player
        top_player_id = predictions[0]["id"]
        analysis_response = await client.get(f"/api/players/{top_player_id}/ai-analysis")
        assert analysis_response.status_code == 200
        
        # 4. Optimize squad
        squad_response = await client.post("/api/optimize/squad", json={"budget": 100.0})
        assert squad_response.status_code == 200

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
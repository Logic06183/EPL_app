"""
Pytest configuration and fixtures for backend tests
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings():
    """Get application settings"""
    return get_settings()


@pytest.fixture
def sample_player_data():
    """Sample player data for testing"""
    return {
        "id": 123,
        "name": "Test Player",
        "full_name": "Test Player Full",
        "team_name": "Test Team",
        "position": 3,
        "position_name": "MID",
        "price": 10.5,
        "form": 7.5,
        "ownership": 25.3,
        "total_points": 150,
        "points_per_game": 6.5,
        "predicted_points": 8.2,
        "confidence": 75.0,
        "model_used": "random_forest"
    }


@pytest.fixture
def mock_fpl_bootstrap_data():
    """Mock FPL bootstrap-static data"""
    return {
        "elements": [
            {
                "id": 1,
                "web_name": "Salah",
                "first_name": "Mohamed",
                "second_name": "Salah",
                "now_cost": 130,
                "element_type": 3,
                "team": 1,
                "total_points": 200,
                "form": "8.5",
                "selected_by_percent": "45.2",
                "minutes": 2000,
                "goals_scored": 15,
                "assists": 10,
                "clean_sheets": 5,
                "goals_conceded": 25,
                "influence": "800.5",
                "creativity": "900.2",
                "threat": "950.8",
                "ict_index": "250.5",
                "expected_goals": "18.5",
                "expected_assists": "12.3",
                "expected_goal_involvements": "30.8",
                "points_per_game": "7.5",
                "bps": 450,
                "bonus": 15
            }
        ],
        "teams": [
            {
                "id": 1,
                "name": "Liverpool",
                "short_name": "LIV"
            }
        ],
        "events": [
            {
                "id": 1,
                "is_current": True,
                "is_next": False,
                "name": "Gameweek 1"
            }
        ]
    }

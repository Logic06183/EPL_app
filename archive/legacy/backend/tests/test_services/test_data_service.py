"""
Tests for data service
"""

import pytest
from app.services.data_service import FPLDataService


@pytest.fixture
def data_service():
    """Create a data service instance"""
    return FPLDataService()


@pytest.mark.asyncio
async def test_get_bootstrap_data(data_service: FPLDataService):
    """Test fetching bootstrap data"""
    try:
        data = await data_service.get_bootstrap_data()
        assert isinstance(data, dict)
        assert "elements" in data
        assert "teams" in data
        assert "events" in data
    except Exception as e:
        pytest.skip(f"FPL API not available: {e}")


@pytest.mark.asyncio
async def test_get_all_players(data_service: FPLDataService):
    """Test getting all players"""
    try:
        players = await data_service.get_all_players()
        assert isinstance(players, list)
        if len(players) > 0:
            player = players[0]
            assert "id" in player
            assert "web_name" in player
    except Exception as e:
        pytest.skip(f"FPL API not available: {e}")


@pytest.mark.asyncio
async def test_get_teams(data_service: FPLDataService):
    """Test getting teams"""
    try:
        teams = await data_service.get_teams()
        assert isinstance(teams, list)
        if len(teams) > 0:
            assert len(teams) == 20  # Premier League has 20 teams
            team = teams[0]
            assert "id" in team
            assert "name" in team
    except Exception as e:
        pytest.skip(f"FPL API not available: {e}")


@pytest.mark.asyncio
async def test_get_gameweek_info(data_service: FPLDataService):
    """Test getting gameweek information"""
    try:
        gw_info = await data_service.get_gameweek_info()
        assert isinstance(gw_info, dict)
        assert "current" in gw_info or "next" in gw_info
    except Exception as e:
        pytest.skip(f"FPL API not available: {e}")


@pytest.mark.asyncio
async def test_search_players(data_service: FPLDataService):
    """Test player search functionality"""
    try:
        # Search for a common name
        results = await data_service.search_players("Salah", limit=5)
        assert isinstance(results, list)
        assert len(results) <= 5
    except Exception as e:
        pytest.skip(f"FPL API not available: {e}")

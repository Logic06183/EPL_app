#!/usr/bin/env python3
"""
SportMonks API Integration for Enhanced EPL Data
Provides real-time match data, detailed statistics, and live scores
"""

import os
import httpx
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from cachetools import TTLCache
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SportMonksAPI:
    """SportMonks Football API v3.0 Integration"""
    
    def __init__(self):
        self.api_key = os.getenv("SPORTMONKS_API_KEY")
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.cache = TTLCache(maxsize=500, ttl=300)  # 5 minute cache
        self.premier_league_id = 8  # Premier League ID in SportMonks
        self.current_season_id = 23614  # 2024/25 Season
        
        if not self.api_key:
            logger.warning("SportMonks API key not found in environment")
            
    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make async request to SportMonks API"""
        if not self.api_key:
            logger.error("SportMonks API key not configured")
            return None
            
        # Check cache first
        cache_key = f"{endpoint}:{json.dumps(params or {})}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for {endpoint}")
            return self.cache[cache_key]
            
        url = f"{self.base_url}{endpoint}"
        
        # Add API token to params
        if params is None:
            params = {}
        params["api_token"] = self.api_key
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Cache successful response
                self.cache[cache_key] = data
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"SportMonks API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"SportMonks request failed: {str(e)}")
            return None
    
    async def get_live_matches(self) -> List[Dict]:
        """Get live Premier League matches with real-time scores"""
        endpoint = "/livescores/inplay"
        params = {
            "include": "scores,teams,stats,lineups,events",
            "filters": f"leagueIds:{self.premier_league_id}"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    async def get_fixtures(self, date: Optional[str] = None) -> List[Dict]:
        """Get Premier League fixtures for a specific date"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        endpoint = "/fixtures/date/" + date
        params = {
            "include": "teams,venue,odds,predictions",
            "filters": f"leagueIds:{self.premier_league_id}"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    async def get_team_stats(self, team_id: int) -> Dict:
        """Get detailed team statistics"""
        endpoint = f"/teams/{team_id}"
        params = {
            "include": "stats,latest,upcoming,squad,transfers,sidelined"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return {}
    
    async def get_player_stats(self, player_id: int) -> Dict:
        """Get detailed player statistics"""
        endpoint = f"/players/{player_id}"
        params = {
            "include": "stats,position,team,transfers,sidelined,trophies"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return {}
    
    async def get_standings(self) -> List[Dict]:
        """Get current Premier League standings"""
        endpoint = f"/standings/seasons/{self.current_season_id}"
        params = {
            "include": "team,details,form"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    async def get_top_scorers(self, limit: int = 20) -> List[Dict]:
        """Get Premier League top scorers"""
        endpoint = f"/topscorers/seasons/{self.current_season_id}"
        params = {
            "include": "player,team",
            "per_page": limit
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    async def get_predictions(self, fixture_id: int) -> Dict:
        """Get match predictions and probabilities"""
        endpoint = f"/predictions/probabilities/fixtures/{fixture_id}"
        
        data = await self._make_request(endpoint)
        if data and "data" in data:
            return data["data"]
        return {}
    
    async def get_h2h(self, team1_id: int, team2_id: int) -> List[Dict]:
        """Get head-to-head statistics between two teams"""
        endpoint = f"/fixtures/head-to-head/{team1_id}/{team2_id}"
        params = {
            "include": "scores,teams,stats"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    async def get_team_form(self, team_id: int, matches: int = 5) -> List[Dict]:
        """Get recent team form (last N matches)"""
        endpoint = f"/teams/{team_id}/latest"
        params = {
            "include": "scores,teams,stats",
            "per_page": matches
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    async def get_injuries(self) -> List[Dict]:
        """Get current injuries and suspensions in Premier League"""
        endpoint = f"/sidelined/leagues/{self.premier_league_id}"
        params = {
            "include": "player,team,type"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    async def search_player(self, name: str) -> List[Dict]:
        """Search for a player by name"""
        endpoint = "/players/search/" + name
        params = {
            "include": "team,position,stats",
            "filters": f"leagueIds:{self.premier_league_id}"
        }
        
        data = await self._make_request(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []
    
    def map_to_fpl_format(self, sportmonks_player: Dict) -> Dict:
        """Map SportMonks player data to FPL format"""
        return {
            "id": sportmonks_player.get("id"),
            "name": sportmonks_player.get("display_name", ""),
            "full_name": sportmonks_player.get("fullname", ""),
            "team": sportmonks_player.get("team", {}).get("name", ""),
            "position": sportmonks_player.get("position", {}).get("name", ""),
            "price": 0,  # Would need separate pricing logic
            "form": sportmonks_player.get("stats", {}).get("rating", 0),
            "goals": sportmonks_player.get("stats", {}).get("goals", 0),
            "assists": sportmonks_player.get("stats", {}).get("assists", 0),
            "clean_sheets": sportmonks_player.get("stats", {}).get("cleansheets", 0),
            "minutes": sportmonks_player.get("stats", {}).get("minutes", 0),
            "yellow_cards": sportmonks_player.get("stats", {}).get("yellowcards", 0),
            "red_cards": sportmonks_player.get("stats", {}).get("redcards", 0),
            "saves": sportmonks_player.get("stats", {}).get("saves", 0),
            "injury_status": sportmonks_player.get("sidelined", {}).get("type", None),
            "sportmonks_id": sportmonks_player.get("id")
        }


# FastAPI endpoints for SportMonks integration
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class LiveMatchResponse(BaseModel):
    matches: List[Dict]
    timestamp: str

class FixtureResponse(BaseModel):
    fixtures: List[Dict]
    date: str

class StandingsResponse(BaseModel):
    standings: List[Dict]
    season: str

def add_sportmonks_routes(app: FastAPI):
    """Add SportMonks API routes to existing FastAPI app"""
    
    sportmonks = SportMonksAPI()
    
    @app.get("/api/sportmonks/live", response_model=LiveMatchResponse)
    async def get_live_matches():
        """Get live Premier League matches with real-time scores"""
        try:
            matches = await sportmonks.get_live_matches()
            return LiveMatchResponse(
                matches=matches,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error fetching live matches: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch live matches")
    
    @app.get("/api/sportmonks/fixtures")
    async def get_fixtures(date: Optional[str] = None):
        """Get Premier League fixtures for a specific date"""
        try:
            fixtures = await sportmonks.get_fixtures(date)
            return FixtureResponse(
                fixtures=fixtures,
                date=date or datetime.now().strftime("%Y-%m-%d")
            )
        except Exception as e:
            logger.error(f"Error fetching fixtures: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch fixtures")
    
    @app.get("/api/sportmonks/standings")
    async def get_standings():
        """Get current Premier League standings"""
        try:
            standings = await sportmonks.get_standings()
            return StandingsResponse(
                standings=standings,
                season="2024/25"
            )
        except Exception as e:
            logger.error(f"Error fetching standings: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch standings")
    
    @app.get("/api/sportmonks/top-scorers")
    async def get_top_scorers(limit: int = 20):
        """Get Premier League top scorers"""
        try:
            scorers = await sportmonks.get_top_scorers(limit)
            return {
                "scorers": scorers,
                "total": len(scorers)
            }
        except Exception as e:
            logger.error(f"Error fetching top scorers: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch top scorers")
    
    @app.get("/api/sportmonks/injuries")
    async def get_injuries():
        """Get current injuries and suspensions"""
        try:
            injuries = await sportmonks.get_injuries()
            return {
                "injuries": injuries,
                "total": len(injuries),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching injuries: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch injuries")
    
    @app.get("/api/sportmonks/player/search")
    async def search_player(name: str):
        """Search for a player by name"""
        try:
            players = await sportmonks.search_player(name)
            fpl_format = [sportmonks.map_to_fpl_format(p) for p in players]
            return {
                "players": fpl_format,
                "total": len(fpl_format)
            }
        except Exception as e:
            logger.error(f"Error searching player: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to search player")
    
    @app.get("/api/sportmonks/team/{team_id}/stats")
    async def get_team_stats(team_id: int):
        """Get detailed team statistics"""
        try:
            stats = await sportmonks.get_team_stats(team_id)
            return stats
        except Exception as e:
            logger.error(f"Error fetching team stats: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch team stats")
    
    @app.get("/api/sportmonks/team/{team_id}/form")
    async def get_team_form(team_id: int, matches: int = 5):
        """Get recent team form"""
        try:
            form = await sportmonks.get_team_form(team_id, matches)
            return {
                "form": form,
                "matches": len(form)
            }
        except Exception as e:
            logger.error(f"Error fetching team form: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch team form")


# Example usage
async def test_sportmonks():
    """Test SportMonks API integration"""
    api = SportMonksAPI()
    
    # Test live matches
    print("Testing live matches...")
    live = await api.get_live_matches()
    print(f"Found {len(live)} live matches")
    
    # Test fixtures
    print("\nTesting fixtures...")
    fixtures = await api.get_fixtures()
    print(f"Found {len(fixtures)} fixtures today")
    
    # Test standings
    print("\nTesting standings...")
    standings = await api.get_standings()
    print(f"Found {len(standings)} teams in standings")
    
    # Test top scorers
    print("\nTesting top scorers...")
    scorers = await api.get_top_scorers(10)
    print(f"Top 10 scorers retrieved")
    
    return True


if __name__ == "__main__":
    # Run test
    asyncio.run(test_sportmonks())
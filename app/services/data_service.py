"""
FPL Data Service
Handles fetching and caching data from the official FPL API
"""

import logging
from typing import List, Dict, Optional, Any
import httpx
from functools import lru_cache

from ..config import settings
from ..utils.cache import get_cache_manager

logger = logging.getLogger(__name__)

# Browser-like headers required by the FPL API
# Without these, requests from cloud providers (GCP, AWS, etc.) get blocked
FPL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://fantasy.premierleague.com/",
    "Origin": "https://fantasy.premierleague.com",
}


class FPLDataService:
    """Service for fetching FPL data"""

    def __init__(self):
        self.base_url = settings.FPL_API_BASE
        self.cache = get_cache_manager()
        self._bootstrap_data: Optional[Dict] = None
        # Reusable client with proper headers and timeouts
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a reusable httpx client with proper headers"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=FPL_HEADERS,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def get_bootstrap_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get bootstrap-static data from FPL API

        This contains all players, teams, and gameweek information.
        Cached for 5 minutes by default.
        """
        if not force_refresh and self._bootstrap_data:
            return self._bootstrap_data

        cache_key = "bootstrap_static"
        cached = self.cache.get(cache_key)

        if cached and not force_refresh:
            self._bootstrap_data = cached
            return cached

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/bootstrap-static/")
            response.raise_for_status()
            data = response.json()

            # Validate we got real data
            elements = data.get("elements", [])
            if len(elements) == 0:
                logger.warning("FPL API returned 0 players - response may be invalid")
            else:
                logger.info(f"FPL API returned {len(elements)} players")

            self._bootstrap_data = data
            self.cache.set(cache_key, data, ttl=600)  # 10 minutes

            logger.info("Bootstrap data fetched and cached")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"FPL API HTTP error: {e.response.status_code} - {e}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"FPL API timeout: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching bootstrap data: {e}")
            raise

    async def get_all_players(self) -> List[Dict[str, Any]]:
        """Get all players from bootstrap data"""
        bootstrap = await self.get_bootstrap_data()
        return bootstrap.get("elements", [])

    async def get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed player information"""
        players = await self.get_all_players()

        # Find player in bootstrap data
        player = next((p for p in players if p["id"] == player_id), None)

        if not player:
            return None

        # Fetch detailed data
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/element-summary/{player_id}/"
            )
            response.raise_for_status()
            details = response.json()

            # Combine bootstrap and detailed data
            player_data = {
                **player,
                "history": details.get("history", []),
                "history_past": details.get("history_past", []),
                "fixtures": details.get("fixtures", []),
            }

            return player_data

        except Exception as e:
            logger.error(f"Error fetching player {player_id} details: {e}")
            return player

    async def search_players(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search players by name"""
        players = await self.get_all_players()
        query_lower = query.lower()

        # Search in web_name and full name
        results = [
            p for p in players
            if query_lower in p.get("web_name", "").lower()
            or query_lower in p.get("first_name", "").lower()
            or query_lower in p.get("second_name", "").lower()
        ]

        return results[:limit]

    async def get_player_history(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player historical performance"""
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/element-summary/{player_id}/"
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error fetching player {player_id} history: {e}")
            return None

    async def get_teams(self) -> List[Dict[str, Any]]:
        """Get all teams"""
        bootstrap = await self.get_bootstrap_data()
        return bootstrap.get("teams", [])

    async def get_fixtures(self, filter_type: str = "upcoming") -> List[Dict[str, Any]]:
        """Get fixtures from FPL API with filtering"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/fixtures/")
            response.raise_for_status()
            fixtures = response.json()

            filtered = []
            for fixture in fixtures:
                if filter_type == "upcoming" and not fixture.get("finished"):
                    filtered.append(fixture)
                elif filter_type == "recent" and fixture.get("finished"):
                    filtered.append(fixture)
                elif filter_type == "live" and fixture.get("started") and not fixture.get("finished"):
                    filtered.append(fixture)

            # For recent, return latest first; for upcoming, soonest first
            if filter_type == "recent":
                filtered = filtered[-10:]
            else:
                filtered = filtered[:10]

            return filtered

        except Exception as e:
            logger.error(f"Error fetching fixtures: {e}")
            return []

    async def get_gameweek_info(self) -> Dict[str, Any]:
        """Get current gameweek information"""
        bootstrap = await self.get_bootstrap_data()
        events = bootstrap.get("events", [])

        # Find current gameweek
        current = next((e for e in events if e.get("is_current")), None)
        next_gw = next((e for e in events if e.get("is_next")), None)

        return {
            "current": current,
            "next": next_gw,
            "all_events": events,
        }


# Dependency injection
@lru_cache()
def get_data_service() -> FPLDataService:
    """Get cached FPL data service instance"""
    return FPLDataService()

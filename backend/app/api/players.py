"""
Player API endpoints
Handles player data retrieval, search, and details
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging

from ..schemas.player import PlayerPrediction, PlayerDetail, PlayerSearchResponse
from ..services.data_service import get_data_service, FPLDataService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", summary="Get all players")
async def get_players(
    position: Optional[int] = Query(None, description="Filter by position (1=GK, 2=DEF, 3=MID, 4=FWD)"),
    team: Optional[int] = Query(None, description="Filter by team ID"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    data_service: FPLDataService = Depends(get_data_service),
):
    """
    Get all players with optional filters

    Returns list of players with basic information
    """
    try:
        players = await data_service.get_all_players()

        # Apply filters
        if position:
            players = [p for p in players if p.get("element_type") == position]

        if team:
            players = [p for p in players if p.get("team") == team]

        if max_price:
            players = [p for p in players if (p.get("now_cost", 0) / 10) <= max_price]

        if min_price:
            players = [p for p in players if (p.get("now_cost", 0) / 10) >= min_price]

        return {
            "players": players,
            "count": len(players),
            "filters_applied": {
                "position": position,
                "team": team,
                "max_price": max_price,
                "min_price": min_price,
            },
        }

    except Exception as e:
        logger.error(f"Error fetching players: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch players")


@router.get("/{player_id}", response_model=PlayerDetail, summary="Get player details")
async def get_player_details(
    player_id: int,
    data_service: FPLDataService = Depends(get_data_service),
):
    """
    Get detailed information for a specific player

    Includes:
    - Basic player info
    - Current season statistics
    - Advanced analytics (xG, xA, ICT)
    - Upcoming fixtures
    """
    try:
        player = await data_service.get_player_by_id(player_id)

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        return player

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch player details")


@router.get("/search/{query}", response_model=PlayerSearchResponse, summary="Search players")
async def search_players(
    query: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    data_service: FPLDataService = Depends(get_data_service),
):
    """
    Search for players by name

    Returns players matching the search query
    """
    try:
        results = await data_service.search_players(query, limit=limit)

        return PlayerSearchResponse(
            query=query,
            results=results,
            total_results=len(results),
        )

    except Exception as e:
        logger.error(f"Error searching players with query '{query}': {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/{player_id}/history", summary="Get player history")
async def get_player_history(
    player_id: int,
    data_service: FPLDataService = Depends(get_data_service),
):
    """
    Get historical performance data for a player

    Returns:
    - Past seasons summary
    - Current season gameweek-by-gameweek data
    - Fixtures and results
    """
    try:
        history = await data_service.get_player_history(player_id)

        if not history:
            raise HTTPException(
                status_code=404, detail=f"History for player {player_id} not found"
            )

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history for player {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch player history")

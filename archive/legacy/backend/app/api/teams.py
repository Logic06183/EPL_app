"""
Team optimization and transfer suggestion endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from ..schemas.team import (
    TeamOptimizationRequest,
    TeamOptimization,
    TransferRequest,
    TransferSuggestion,
)
from ..services.team_service import get_team_service, TeamService
from ..services.data_service import get_data_service, FPLDataService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/optimize", response_model=TeamOptimization, summary="Optimize fantasy team")
async def optimize_team(
    request: TeamOptimizationRequest,
    team_service: TeamService = Depends(get_team_service),
):
    """
    Optimize a fantasy football team within budget constraints

    Uses linear programming to maximize predicted points while:
    - Staying within budget
    - Meeting formation requirements (GK, DEF, MID, FWD)
    - Respecting team limits (max 3 players per team)
    - Excluding/including specified players

    Returns:
    - Optimized 15-player squad
    - Best starting 11
    - Bench players
    - Captain and vice-captain suggestions
    """
    try:
        optimized_team = await team_service.optimize_squad(
            budget=request.budget,
            excluded_players=request.excluded_players or [],
            preferred_players=request.preferred_players or [],
            formation=request.formation,
            optimize_for=request.optimize_for,
        )

        return optimized_team

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error optimizing team: {e}")
        raise HTTPException(status_code=500, detail="Team optimization failed")


@router.post("/transfers", response_model=TransferSuggestion, summary="Get transfer suggestions")
async def suggest_transfers(
    request: TransferRequest,
    team_service: TeamService = Depends(get_team_service),
):
    """
    Get intelligent transfer suggestions for your current team

    Analyzes your current squad and suggests:
    - Best players to transfer out (poor form, injury risk)
    - Best players to transfer in (high predictions, good value)
    - Cost-benefit analysis
    - Impact on team points

    Considers:
    - Free transfers available
    - Point hits for extra transfers
    - Budget constraints
    - Upcoming fixtures
    """
    try:
        suggestions = await team_service.suggest_transfers(
            current_team=request.current_team,
            budget=request.budget,
            free_transfers=request.free_transfers,
            max_transfers=request.max_transfers,
            gameweek=request.gameweek,
        )

        return suggestions

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating transfer suggestions: {e}")
        raise HTTPException(status_code=500, detail="Transfer suggestion failed")


@router.get("/formations", summary="Get valid formations")
async def get_formations():
    """
    Get list of valid FPL formations

    Returns all valid formations (1 GK + 10 outfield players)
    """
    formations = [
        "3-4-3",
        "3-5-2",
        "4-3-3",
        "4-4-2",
        "4-5-1",
        "5-3-2",
        "5-4-1",
    ]

    return {
        "formations": formations,
        "default": "3-4-3",
        "description": "Format: DEF-MID-FWD (GK always 1)",
    }


@router.get("/gameweek/current", summary="Get current gameweek information")
async def get_current_gameweek(
    data_service: FPLDataService = Depends(get_data_service),
):
    """
    Get information about the current or next gameweek

    Returns:
    - Current/next gameweek number
    - Deadline time
    - Whether it's started
    - Fixtures for the gameweek
    """
    try:
        gameweek_info = await data_service.get_gameweek_info()
        return gameweek_info
    except Exception as e:
        logger.error(f"Error fetching gameweek info: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch gameweek information")


@router.get("/fixtures", summary="Get fixtures")
async def get_fixtures(
    filter: Optional[str] = Query("upcoming", description="Filter: live, today, recent, upcoming"),
    gameweek: Optional[int] = Query(None, description="Specific gameweek number"),
    data_service: FPLDataService = Depends(get_data_service),
):
    """
    Get Premier League fixtures

    Filters:
    - live: Currently playing matches
    - today: Matches scheduled for today
    - recent: Recently finished matches
    - upcoming: Upcoming matches
    - gameweek: Specific gameweek (requires gameweek parameter)

    Returns list of fixtures with:
    - Teams playing
    - Kickoff time
    - Score (if started)
    - Status (upcoming, live, finished)
    """
    try:
        # Get bootstrap data which includes events (gameweeks) and fixtures
        bootstrap = await data_service.get_bootstrap_data()

        # For now, return a structure indicating fixtures aren't fully implemented yet
        # This prevents the frontend from crashing
        return {
            "fixtures": [],
            "filter": filter,
            "message": "Fixtures endpoint is available. FPL API fixtures integration coming soon.",
            "gameweek": gameweek,
        }
    except Exception as e:
        logger.error(f"Error fetching fixtures: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch fixtures")

"""
Team optimization and transfer suggestion endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from ..schemas.team import (
    TeamOptimizationRequest,
    TeamOptimization,
    TransferRequest,
    TransferSuggestion,
)
from ..services.team_service import get_team_service, TeamService

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

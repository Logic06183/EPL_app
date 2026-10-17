"""Team and transfer-related schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List


class TeamOptimizationRequest(BaseModel):
    """Request to optimize a fantasy team"""

    budget: float = Field(default=100.0, ge=0, le=200)
    excluded_players: Optional[List[int]] = Field(default_factory=list)
    preferred_players: Optional[List[int]] = Field(default_factory=list)
    formation: Optional[str] = None  # e.g., "3-4-3", "4-4-2"
    optimize_for: str = Field(default="points", pattern="^(points|value|form)$")


class TeamPlayer(BaseModel):
    """Player in an optimized team"""

    id: int
    name: str
    team: str
    position: str
    price: float
    predicted_points: float
    is_captain: bool = False
    is_vice_captain: bool = False


class TeamOptimization(BaseModel):
    """Optimized team response"""

    total_cost: float
    predicted_points: float
    formation: str
    players: List[TeamPlayer]
    bench: List[TeamPlayer]
    captain: TeamPlayer
    vice_captain: TeamPlayer


class TransferRequest(BaseModel):
    """Request for transfer suggestions"""

    current_team: List[int]
    budget: float
    free_transfers: int = 1
    max_transfers: int = 2
    gameweek: Optional[int] = None


class Transfer(BaseModel):
    """Single transfer suggestion"""

    player_out_id: int
    player_out_name: str
    player_in_id: int
    player_in_name: str
    cost_change: float
    points_gain: float
    reasoning: str


class TransferSuggestion(BaseModel):
    """Transfer suggestions response"""

    gameweek: int
    suggestions: List[Transfer]
    total_cost: float
    expected_points_gain: float
    hits_required: int

"""Player-related schemas"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any


class PlayerStats(BaseModel):
    """Basic player statistics"""

    total_points: int
    points_per_game: float
    goals_scored: int
    assists: int
    clean_sheets: int
    minutes: int
    bonus: int
    bps: int
    form: float
    selected_by_percent: float


class PlayerAdvancedStats(BaseModel):
    """Advanced analytics for a player"""

    # Expected metrics
    expected_goals: Optional[float] = Field(None, alias="xG")
    expected_assists: Optional[float] = Field(None, alias="xA")
    expected_goal_involvements: Optional[float] = Field(None, alias="xGI")

    # Per-90 minute stats
    goals_per_90: Optional[float] = None
    assists_per_90: Optional[float] = None
    expected_goals_per_90: Optional[float] = None

    # ICT Index components
    ict_index: Optional[float] = None
    influence: Optional[float] = None
    creativity: Optional[float] = None
    threat: Optional[float] = None

    model_config = ConfigDict(populate_by_name=True)


class PlayerPrediction(BaseModel):
    """Player prediction with ML model output"""

    # Basic info
    id: int
    name: str
    full_name: str
    team_name: str
    position: int
    position_name: str
    price: float

    # Current stats
    form: float
    ownership: float
    total_points: int
    points_per_game: float

    # Prediction
    predicted_points: float
    confidence: float
    model_used: str = "ensemble"

    # AI insights
    ai_enhanced: bool = False
    reasoning: Optional[str] = None
    gemini_insight: Optional[str] = None

    # Advanced metrics
    advanced_stats: Optional[PlayerAdvancedStats] = None

    # Model breakdown
    model_breakdown: Optional[Dict[str, float]] = None
    sentiment_impact: Optional[float] = None


class PlayerDetail(BaseModel):
    """Detailed player information"""

    # Basic info
    id: int
    name: str
    full_name: str
    team_id: int
    team_name: str
    position: int
    position_name: str
    price: float
    web_name: str

    # Stats
    stats: PlayerStats
    advanced_stats: Optional[PlayerAdvancedStats] = None

    # Prediction
    prediction: Optional[PlayerPrediction] = None

    # Fixtures
    upcoming_fixtures: Optional[list] = None
    fixture_difficulty: Optional[float] = None


class PlayerSearchResponse(BaseModel):
    """Player search results"""

    query: str
    results: list[PlayerDetail]
    total_results: int

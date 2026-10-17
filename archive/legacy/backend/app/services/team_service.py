"""
Team Service
Handles team optimization and transfer suggestions
"""

import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache

from ..schemas.team import (
    TeamOptimization,
    TeamPlayer,
    TransferSuggestion,
    Transfer,
)
from .data_service import get_data_service
from .prediction_service import get_prediction_service

logger = logging.getLogger(__name__)


class TeamService:
    """Service for team optimization and transfers"""

    def __init__(self):
        self.data_service = get_data_service()
        self.prediction_service = get_prediction_service()

    async def optimize_squad(
        self,
        budget: float = 100.0,
        excluded_players: List[int] = None,
        preferred_players: List[int] = None,
        formation: Optional[str] = None,
        optimize_for: str = "points",
    ) -> TeamOptimization:
        """
        Optimize fantasy team using greedy algorithm

        Note: Full linear programming optimization requires PuLP library.
        This is a simplified greedy approach for demonstration.
        """
        excluded_players = excluded_players or []
        preferred_players = preferred_players or []

        # Get predictions
        all_predictions = await self.prediction_service.get_predictions(
            top_n=500,
            model="ensemble",
        )

        # Filter out excluded players
        predictions = [
            p for p in all_predictions
            if p.id not in excluded_players
        ]

        # Group by position
        goalkeepers = [p for p in predictions if p.position == 1]
        defenders = [p for p in predictions if p.position == 2]
        midfielders = [p for p in predictions if p.position == 3]
        forwards = [p for p in predictions if p.position == 4]

        # Greedy selection
        selected = []
        remaining_budget = budget

        # Select formation (default 3-4-3)
        formation_map = {
            "3-4-3": {"gk": 2, "def": 5, "mid": 5, "fwd": 3},
            "4-3-3": {"gk": 2, "def": 5, "mid": 5, "fwd": 3},
            "4-4-2": {"gk": 2, "def": 5, "mid": 5, "fwd": 3},
            "3-5-2": {"gk": 2, "def": 5, "mid": 5, "fwd": 3},
        }

        # Select 2 GK, 5 DEF, 5 MID, 3 FWD
        positions_needed = {"gk": 2, "def": 5, "mid": 5, "fwd": 3}

        # Select goalkeepers
        for gk in goalkeepers[:positions_needed["gk"]]:
            if gk.price <= remaining_budget:
                selected.append(gk)
                remaining_budget -= gk.price

        # Select defenders
        for df in defenders[:positions_needed["def"]]:
            if df.price <= remaining_budget:
                selected.append(df)
                remaining_budget -= df.price

        # Select midfielders
        for mf in midfielders[:positions_needed["mid"]]:
            if mf.price <= remaining_budget:
                selected.append(mf)
                remaining_budget -= mf.price

        # Select forwards
        for fw in forwards[:positions_needed["fwd"]]:
            if fw.price <= remaining_budget:
                selected.append(fw)
                remaining_budget -= fw.price

        # Sort by predicted points for starting 11
        selected.sort(key=lambda x: x.predicted_points, reverse=True)

        # Select captain (highest predicted points)
        captain = selected[0] if selected else None
        vice_captain = selected[1] if len(selected) > 1 else None

        # Starting 11 (1 GK + top 10 outfield)
        starting_11 = []
        bench = []

        # Add 1 GK to starting
        gk_in_squad = [p for p in selected if p.position == 1]
        if gk_in_squad:
            starting_11.append(gk_in_squad[0])
            if len(gk_in_squad) > 1:
                bench.append(gk_in_squad[1])

        # Add best outfield players
        outfield = [p for p in selected if p.position != 1]
        outfield.sort(key=lambda x: x.predicted_points, reverse=True)
        starting_11.extend(outfield[:10])
        bench.extend(outfield[10:])

        # Convert to TeamPlayer objects
        def to_team_player(p, is_captain=False, is_vice=False):
            return TeamPlayer(
                id=p.id,
                name=p.name,
                team=p.team_name,
                position=self._position_name(p.position),
                price=p.price,
                predicted_points=p.predicted_points,
                is_captain=is_captain,
                is_vice_captain=is_vice,
            )

        team_players = [
            to_team_player(
                p,
                is_captain=(p.id == captain.id if captain else False),
                is_vice=(p.id == vice_captain.id if vice_captain else False),
            )
            for p in starting_11
        ]

        bench_players = [to_team_player(p) for p in bench]

        total_cost = sum(p.price for p in selected)
        total_predicted = sum(p.predicted_points for p in starting_11)

        return TeamOptimization(
            total_cost=round(total_cost, 1),
            predicted_points=round(total_predicted, 1),
            formation=formation or "3-4-3",
            players=team_players,
            bench=bench_players,
            captain=to_team_player(captain, is_captain=True) if captain else None,
            vice_captain=to_team_player(vice_captain, is_vice=True) if vice_captain else None,
        )

    async def suggest_transfers(
        self,
        current_team: List[int],
        budget: float,
        free_transfers: int = 1,
        max_transfers: int = 2,
        gameweek: Optional[int] = None,
    ) -> TransferSuggestion:
        """
        Suggest optimal transfers for current team

        Analyzes current squad and suggests best transfers
        """
        # Get all predictions
        predictions = await self.prediction_service.get_predictions(top_n=500)

        # Get current team predictions
        current_predictions = {
            p.id: p for p in predictions if p.id in current_team
        }

        # Find underperforming players in current team
        current_sorted = sorted(
            current_predictions.values(),
            key=lambda x: x.predicted_points
        )

        # Find best available players not in team
        available = [p for p in predictions if p.id not in current_team]
        available_sorted = sorted(
            available,
            key=lambda x: x.predicted_points,
            reverse=True
        )

        # Generate transfer suggestions
        suggestions = []
        total_cost = 0.0
        expected_gain = 0.0

        for i in range(min(max_transfers, len(current_sorted))):
            player_out = current_sorted[i]

            # Find replacement in same position
            same_position = [
                p for p in available_sorted
                if p.position == player_out.position
                and p.price <= (budget + player_out.price)
            ]

            if same_position:
                player_in = same_position[0]
                cost_change = player_in.price - player_out.price
                points_gain = player_in.predicted_points - player_out.predicted_points

                if points_gain > 0:  # Only suggest if improvement
                    suggestions.append(Transfer(
                        player_out_id=player_out.id,
                        player_out_name=player_out.name,
                        player_in_id=player_in.id,
                        player_in_name=player_in.name,
                        cost_change=round(cost_change, 1),
                        points_gain=round(points_gain, 1),
                        reasoning=self._generate_transfer_reasoning(
                            player_out, player_in
                        ),
                    ))

                    total_cost += cost_change
                    expected_gain += points_gain

        # Calculate hits required
        hits_required = max(0, len(suggestions) - free_transfers)

        return TransferSuggestion(
            gameweek=gameweek or 1,
            suggestions=suggestions[:max_transfers],
            total_cost=round(total_cost, 1),
            expected_points_gain=round(expected_gain, 1),
            hits_required=hits_required,
        )

    def _position_name(self, position: int) -> str:
        """Convert position number to name"""
        position_map = {
            1: "GK",
            2: "DEF",
            3: "MID",
            4: "FWD",
        }
        return position_map.get(position, "Unknown")

    def _generate_transfer_reasoning(self, player_out, player_in) -> str:
        """Generate reasoning for transfer suggestion"""
        reasons = []

        # Points difference
        if player_in.predicted_points > player_out.predicted_points:
            diff = player_in.predicted_points - player_out.predicted_points
            reasons.append(f"+{diff:.1f} predicted points")

        # Form
        if player_in.form > player_out.form:
            reasons.append(f"Better form ({player_in.form:.1f} vs {player_out.form:.1f})")

        # Price
        if player_in.price < player_out.price:
            saving = player_out.price - player_in.price
            reasons.append(f"Saves £{saving:.1f}m")

        # Ownership
        if player_in.ownership < 15 and player_in.predicted_points > 6:
            reasons.append("Hidden gem (low ownership)")

        return "; ".join(reasons) if reasons else "Upgrade recommended"


@lru_cache()
def get_team_service() -> TeamService:
    """Get cached team service instance"""
    return TeamService()

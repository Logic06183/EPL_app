"""
Prediction Service — the interface the API routes use for predicted points.

"xp" is the trained expected-points model (app/services/xp_service.py),
backtested on held-out seasons (app/ml/backtest.json). "basic" is a
transparent form/points-per-game blend, also used as the fallback while the
model's inputs can't be fetched.

The old model names ("random_forest", "deep_learning", "ensemble") are kept as
aliases for "xp" so existing clients keep working.
"""

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .xp_service import XPService, get_xp_service

logger = logging.getLogger(__name__)

LEGACY_ALIASES = {"random_forest", "deep_learning", "ensemble"}


def _basic(player: Dict[str, Any]) -> float:
    form = float(player.get("form", 0) or 0)
    ppg = float(player.get("points_per_game", 0) or 0)
    ict = float(player.get("ict_index", 0) or 0) / 10
    return round(form * 0.5 + ppg * 0.4 + ict * 0.1, 2)


class PredictionService:
    def __init__(self, xp: Optional[XPService] = None):
        self.xp = xp or get_xp_service()

    @property
    def _trained(self) -> bool:
        return self.xp.ready

    async def ensure_ready(self, data_service) -> None:
        """Refresh the model's inputs if they're more than an hour old."""
        await self.xp.ensure_fresh(data_service)

    def predict_batch(self, players: List[Dict[str, Any]], model_type: str = "xp") -> List[float]:
        if model_type == "basic" or not self.xp.ready:
            return [max(0.0, _basic(p)) for p in players]
        out = []
        for p in players:
            v = self.xp.next_xp(p["id"])
            out.append(round(v, 2) if v is not None else 0.0)
        return out

    def predict(self, player: Dict[str, Any], model_type: str = "xp") -> float:
        return self.predict_batch([player], model_type)[0]

    def gw_xp(self, player_id: int, gw: int) -> Optional[float]:
        """xP for one upcoming gameweek (all fixtures in it), or None if unknown."""
        by_gw = self.xp.xp.get(player_id)
        return None if by_gw is None else by_gw.get(gw)

    def captain_score(self, player_id: int, gw: Optional[int] = None) -> float:
        """Ranking score for captaincy (xP shrunk toward season rate); falls back to xP."""
        if self._trained:
            return self.xp.captain_score(player_id, gw)
        return (self.gw_xp(player_id, gw) or 0.0) if gw is not None else 0.0

    def captain_rate(self, player_id: int, gw: Optional[int] = None) -> Optional[float]:
        return self.xp.captain_rate(player_id, gw) if self._trained else None

    def captain_horizon(self, player_id: int) -> List[float]:
        return self.xp.captain_horizon(player_id) if self._trained else []

    def horizon(self, player_id: int) -> List[float]:
        """xP for each of the next few gameweeks (empty if the model isn't ready)."""
        return self.xp.horizon_xp(player_id)

    async def get_model_info(self) -> Dict[str, Any]:
        bt = self.xp.backtest or {}
        seasons = bt.get("seasons", {})
        track_record = {
            season: {
                "model": v["metrics"].get("model"),
                "season_average_baseline": v["metrics"].get("season_avg"),
                "trained_on": v.get("trained_on"),
            }
            for season, v in seasons.items()
        }
        return {
            "models": {
                "xp": {
                    "name": "Expected points",
                    "description": (
                        "Gradient-boosted model of next-gameweek points from recent form, "
                        "minutes, xG/xA, team and opponent strength, home/away and last "
                        "season's output, scaled by FPL's chance of playing."
                    ),
                    "available": True,
                    "trained": self.xp.ready,
                    "gameweek": self.xp.next_gw,
                    "updated_at": self.xp.updated_at.isoformat() if self.xp.updated_at else None,
                },
                "basic": {
                    "name": "Form-based",
                    "description": "Weighted blend of current form, points-per-game and ICT index. No ML.",
                    "available": True,
                    "trained": True,
                },
            },
            "recommendation": "xp",
            "aliases": {alias: "xp" for alias in sorted(LEGACY_ALIASES)},
            "track_record": track_record,
            "track_record_note": (
                "Walk-forward backtest: each season is predicted by a model trained only on "
                "earlier seasons. Metrics are averaged per gameweek over players averaging "
                "30+ minutes. Spearman = rank correlation with actual points; captain_pts = "
                "actual points of the top-ranked player; top11_pts = average actual points "
                "of the top 11."
            ),
        }


@lru_cache()
def get_prediction_service() -> PredictionService:
    """Singleton prediction service — shared across requests."""
    return PredictionService()

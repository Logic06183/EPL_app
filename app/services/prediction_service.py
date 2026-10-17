"""
Prediction Service

Two layers:
  * Season-snapshot models (RF / GB / MLP) on 12 bootstrap features. Their
    target is season points-per-game, so they mostly describe the season so far.
  * Next-gameweek model (app/ml/next_gw.py) trained on per-fixture histories
    and walk-forward backtested at refresh time. With PREDICTION_MODEL=auto it
    replaces the snapshot models only when it beats the naive baselines on the
    most recent rounds; PREDICTION_MODEL=next_gw forces it, =legacy disables it.
"""

import asyncio
import logging
import time
from functools import lru_cache
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from ..config import settings
from ..ml import next_gw

logger = logging.getLogger(__name__)

# Weights for the ensemble blend
_W_RF   = 0.35
_W_GB   = 0.35
_W_MLP  = 0.30


class PredictionService:
    """Multi-model ML prediction service for FPL player points."""

    def __init__(self):
        self._rf:    RandomForestRegressor | None   = None
        self._gb:    GradientBoostingRegressor | None = None
        self._mlp:   MLPRegressor | None            = None
        self._scaler = StandardScaler()
        self._trained = False
        self._train_lock: asyncio.Lock | None = None
        # Next-gameweek model state
        self._next_gw_preds: dict[int, float] = {}
        self._next_gw_round: int | None = None
        self._next_gw_report: dict[str, Any] | None = None
        self._next_gw_refreshed_at: float = 0.0
        self._next_gw_lock: asyncio.Lock | None = None

    @property
    def next_gw_active(self) -> bool:
        return bool(self._next_gw_preds)

    async def refresh_next_gw(self, data_service, concurrency: int = 8) -> None:
        """Fetch per-player histories, backtest, and (if it earns it) activate the next-GW model."""
        if settings.PREDICTION_MODEL == "legacy":
            return
        if self._next_gw_lock is None:
            self._next_gw_lock = asyncio.Lock()
        async with self._next_gw_lock:
            try:
                await self._refresh_next_gw(data_service, concurrency)
                self._next_gw_refreshed_at = time.monotonic()
            except Exception as e:
                logger.warning(f"Next-GW model refresh failed, keeping previous state: {e}")
                # Retry in ~30 min rather than waiting the full 6h.
                self._next_gw_refreshed_at = time.monotonic() - (6 * 3600 - 1800)

    async def _refresh_next_gw(self, data_service, concurrency: int) -> None:
        bootstrap = await data_service.get_bootstrap_data()
        events = bootstrap.get("events", [])
        nxt = next((e for e in events if e.get("is_next")), None)
        finished = [e["id"] for e in events if e.get("finished")]
        if nxt is None or len(finished) < 5:
            logger.info("Next-GW model: not enough completed rounds yet — using snapshot models")
            return
        elements = [p for p in bootstrap.get("elements", []) if float(p.get("minutes", 0)) > 0]
        positions = {p["id"]: int(p.get("element_type", 3)) for p in elements}
        prices = {p["id"]: float(p.get("now_cost", 50)) / 10 for p in elements}

        fixtures = await data_service.get_all_fixtures()
        difficulty = {}
        for f in fixtures:
            difficulty[(f["id"], True)] = float(f.get("team_h_difficulty", 3))
            difficulty[(f["id"], False)] = float(f.get("team_a_difficulty", 3))

        sem = asyncio.Semaphore(concurrency)

        async def fetch(pid: int):
            async with sem:
                return pid, await data_service.get_player_history(pid)

        results = await asyncio.gather(*(fetch(pid) for pid in positions))
        histories = {pid: (r or {}).get("history", []) for pid, r in results}
        upcoming = {pid: (r or {}).get("fixtures", []) for pid, r in results}
        fetched = sum(1 for _, r in results if r)
        if fetched < 0.8 * len(results):
            raise RuntimeError(f"only fetched {fetched}/{len(results)} player histories")

        def fit():
            # OpenMP sizes itself to the host, not the container; in a worker thread that
            # oversubscribes badly (~10× slower). Cloud Run gives us 2 vCPUs.
            with threadpool_limits(limits=2):
                return _fit()

        def _fit():
            ds = next_gw.build_dataset(histories, positions, difficulty)
            report = next_gw.walk_forward_backtest(ds)
            model = next_gw.new_model().fit(ds.X, ds.y)
            preds = next_gw.predict_next_round(model, histories, upcoming, positions, prices, nxt["id"])
            return report, preds

        report, preds = await asyncio.to_thread(fit)
        self._next_gw_report = {**report.as_dict(), "beats_baselines": report.beats_baselines(),
                                "next_round": nxt["id"], "players": len(preds)}
        use = settings.PREDICTION_MODEL == "next_gw" or report.beats_baselines()
        self._next_gw_preds = preds if use else {}
        self._next_gw_round = nxt["id"] if use else None
        logger.info(f"Next-GW model {'ACTIVE' if use else 'not used'}: {self._next_gw_report}")

    def next_gw_stale(self, max_age_s: float = 6 * 3600) -> bool:
        return time.monotonic() - self._next_gw_refreshed_at > max_age_s

    async def ensure_trained(self, players: list[dict[str, Any]]) -> None:
        """Train once, off the event loop. Concurrent cold requests wait for one training run."""
        if self._trained:
            return
        if self._train_lock is None:
            self._train_lock = asyncio.Lock()
        async with self._train_lock:
            if not self._trained:
                await asyncio.to_thread(self.train, players)

    # ── Feature engineering ────────────────────────────────────────────────────

    def _features(self, player: dict[str, Any]) -> list[float]:
        """12-feature vector from FPL bootstrap player element."""
        pos = int(player.get("element_type", 2))  # 1=GK 2=DEF 3=MID 4=FWD
        return [
            float(player.get("now_cost", 0)) / 10,          # price (£m)
            float(player.get("total_points", 0)),            # season total pts
            float(player.get("form", 0)),                    # rolling 30-day form
            float(player.get("selected_by_percent", 0)),     # ownership %
            float(player.get("minutes", 0)) / 90,            # 90s played (normalised)
            float(player.get("goals_scored", 0)),
            float(player.get("assists", 0)),
            float(player.get("ict_index", 0)),               # composite threat index
            float(player.get("bonus", 0)),                   # bonus pts
            float(player.get("bps", 0)) / 10,               # bonus pts system score
            float(player.get("clean_sheets", 0)),            # useful for GK/DEF
            float(pos),                                      # position code
        ]

    # ── Training ───────────────────────────────────────────────────────────────

    def train(self, players: list[dict[str, Any]]) -> None:
        """Train all three models on the full player dataset."""
        # Filter out players with zero minutes (never played — no signal)
        active = [p for p in players if float(p.get("minutes", 0)) > 0]
        if len(active) < 30:
            logger.warning("Too few active players to train — skipping")
            return

        X = np.array([self._features(p) for p in active])
        y = np.array([float(p.get("points_per_game", 0)) for p in active])

        try:
            X_scaled = self._scaler.fit_transform(X)

            # Random Forest — good baseline, robust to noise
            self._rf = RandomForestRegressor(
                n_estimators=200, max_depth=12,
                min_samples_leaf=2, random_state=42, n_jobs=-1
            )
            self._rf.fit(X_scaled, y)

            # Gradient Boosting — captures non-linear interactions better than RF
            self._gb = GradientBoostingRegressor(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                subsample=0.8, random_state=42
            )
            self._gb.fit(X_scaled, y)

            # Neural Network — learns complex feature combinations
            self._mlp = MLPRegressor(
                hidden_layer_sizes=(64, 32), activation="relu",
                max_iter=500, random_state=42, early_stopping=True,
                validation_fraction=0.1
            )
            self._mlp.fit(X_scaled, y)

            self._trained = True
            logger.info(
                f"All 3 models trained on {len(active)} players "
                f"({len(players) - len(active)} excluded — never played)"
            )
        except Exception as e:
            logger.error(f"Training failed: {e}")

    # ── Prediction ─────────────────────────────────────────────────────────────

    def _raw_predict(self, player: dict[str, Any]) -> dict[str, float]:
        """Return per-model raw predictions. Falls back to form if not trained."""
        form = float(player.get("form", 0))

        if not self._trained:
            return {"rf": form, "gb": form, "mlp": form}

        try:
            X = np.array([self._features(player)])
            Xs = self._scaler.transform(X)
            rf_pred  = float(self._rf.predict(Xs)[0])
            gb_pred  = float(self._gb.predict(Xs)[0])
            mlp_pred = float(self._mlp.predict(Xs)[0])
            return {"rf": rf_pred, "gb": gb_pred, "mlp": mlp_pred}
        except Exception as e:
            logger.debug(f"Prediction error for {player.get('web_name')}: {e}")
            return {"rf": form, "gb": form, "mlp": form}

    def predict_batch(
        self, players: list[dict[str, Any]], model_type: str = "random_forest"
    ) -> list[float]:
        """
        Vectorised inference for many players in one shot.
        ~50-100x faster than calling predict() per player because each sklearn
        .predict() call has fixed Python overhead regardless of batch size.
        """
        if not players:
            return []

        if model_type == "basic":
            out = []
            for p in players:
                form = float(p.get("form", 0))
                ppg  = float(p.get("points_per_game", 0))
                ict  = float(p.get("ict_index", 0)) / 10
                out.append(round((form * 0.5 + ppg * 0.4 + ict * 0.1), 2))
            return out

        if self._next_gw_preds:
            return [round(self._next_gw_preds.get(p.get("id"), 0.0), 2) for p in players]

        forms = np.array([float(p.get("form", 0)) for p in players])

        if not self._trained:
            return [max(0.0, f) for f in forms]

        try:
            X = np.array([self._features(p) for p in players])
            Xs = self._scaler.transform(X)
            rf  = self._rf.predict(Xs)
            gb  = self._gb.predict(Xs)
            mlp = self._mlp.predict(Xs)
        except Exception as e:
            logger.debug(f"Batch prediction error, falling back to form: {e}")
            return [max(0.0, f) for f in forms]

        if model_type == "random_forest":
            return [max(0.0, float(v)) for v in rf]
        if model_type == "deep_learning":
            blended = gb * 0.55 + mlp * 0.45
            return [max(0.0, float(v)) for v in blended]
        if model_type == "ensemble":
            blended = _W_RF * rf + _W_GB * gb + _W_MLP * mlp + forms * 0.05
            return [max(0.0, float(v)) for v in blended]
        return [max(0.0, float(v)) for v in rf]

    def predict(self, player: dict[str, Any], model_type: str = "random_forest") -> float:
        """
        Return a single predicted points value for the given model_type.
        model_type: "basic" | "random_forest" | "deep_learning" | "ensemble"
        """
        form = float(player.get("form", 0))

        if model_type == "basic":
            # Pure form score — no ML
            ppg  = float(player.get("points_per_game", 0))
            ict  = float(player.get("ict_index", 0)) / 10
            return round((form * 0.5 + ppg * 0.4 + ict * 0.1), 2)

        if self._next_gw_preds:
            return round(self._next_gw_preds.get(player.get("id"), 0.0), 2)

        preds = self._raw_predict(player)

        if model_type == "random_forest":
            return max(0.0, preds["rf"])

        if model_type == "deep_learning":
            # GradientBoosting + MLP blend — stronger non-linear model
            return max(0.0, preds["gb"] * 0.55 + preds["mlp"] * 0.45)

        if model_type == "ensemble":
            # Weighted blend of all three models
            blended = (
                _W_RF  * preds["rf"]  +
                _W_GB  * preds["gb"]  +
                _W_MLP * preds["mlp"]
            )
            # Small form recency boost (+5% form signal keeps hot streaks visible)
            recency = form * 0.05
            return max(0.0, blended + recency)

        # Unknown type — fall back to RF
        return max(0.0, preds["rf"])

    # ── Metadata ───────────────────────────────────────────────────────────────

    async def get_model_info(self) -> dict[str, Any]:
        snapshot_note = "Fits season points-per-game from season totals — describes form so far, not a backtested forecast."
        return {
            "active": "next_gw" if self.next_gw_active else "snapshot",
            "models": {
                "basic": {
                    "name": "Form + PPG (no ML)",
                    "description": "0.5×form + 0.4×points-per-game + 0.1×ICT/10. Fast and transparent.",
                    "available": True,
                    "trained": True,
                },
                "next_gw": {
                    "name": "Next-gameweek model",
                    "description": "Gradient boosting on per-fixture history (recent points, minutes, xG, xA, ICT, "
                                   "price, home/away, fixture difficulty). Predicts expected points for the next "
                                   "gameweek; doubles summed, blanks zero. Used for all ML model types when active.",
                    "available": self.next_gw_active,
                    "next_round": self._next_gw_round,
                    "backtest": self._next_gw_report,
                },
                "random_forest": {"name": "Random Forest (season snapshot)", "description": snapshot_note,
                                  "available": True, "trained": self._trained},
                "deep_learning": {"name": "Gradient Boost + MLP (season snapshot)", "description": snapshot_note,
                                  "available": True, "trained": self._trained},
                "ensemble": {"name": "Snapshot ensemble", "description": snapshot_note,
                             "available": True, "trained": self._trained},
            },
            "recommendation": "ensemble",
            "backtest_note": "MAE in FPL points per player-fixture on the most recent completed rounds, "
                             "versus rolling 4-round mean and points-per-round-to-date baselines.",
        }


@lru_cache
def get_prediction_service() -> PredictionService:
    """Singleton prediction service — shared across requests."""
    return PredictionService()

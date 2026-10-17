"""
Next-gameweek points model trained on per-fixture player histories.

Why this exists: the original models regress season points-per-game on
season totals (incl. total_points and minutes), which reconstructs PPG
in-sample rather than forecasting. Here every training row is one fixture a
player featured in, the features use only rounds *strictly before* that
fixture's round, and the target is the points actually scored in it.

Data comes from FPL's element-summary endpoint:
  history  — one entry per past fixture (round, total_points, minutes, xG, …)
  fixtures — upcoming fixtures (event, is_home, difficulty)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

WINDOW = 4  # rounds of recent form

FEATURES = [
    "mean_points", "mean_minutes", "mean_xg", "mean_xa", "mean_ict", "mean_bonus",
    "starts_rate", "mean_xgc", "ppg_to_date", "minutes_share_to_date", "n_prior_rounds",
    "price", "is_home", "difficulty", "pos_gk", "pos_def", "pos_mid", "pos_fwd",
]


def _f(entry: dict[str, Any], key: str) -> float:
    try:
        return float(entry.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def _round_aggregates(history: list[dict[str, Any]]) -> dict[int, dict[str, float]]:
    """Sum stats per round (double gameweeks have two history entries)."""
    by_round: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for h in history:
        r = by_round[int(h["round"])]
        r["points"]  += _f(h, "total_points")
        r["minutes"] += _f(h, "minutes")
        r["xg"]      += _f(h, "expected_goals")
        r["xa"]      += _f(h, "expected_assists")
        r["ict"]     += _f(h, "ict_index")
        r["bonus"]   += _f(h, "bonus")
        r["starts"]  += _f(h, "starts")
        r["xgc"]     += _f(h, "expected_goals_conceded")
    return by_round


def _features(
    rounds: dict[int, dict[str, float]],
    before_round: int,
    position: int,
    price: float,
    is_home: bool,
    difficulty: float,
    first_round: int,
) -> list[float]:
    prior = [rounds[r] for r in sorted(rounds) if r < before_round]
    recent = prior[-WINDOW:]
    n_recent = max(len(recent), 1)
    rounds_elapsed = max(before_round - first_round, 1)

    def mean(key: str) -> float:
        return sum(r[key] for r in recent) / n_recent

    total_points = sum(r["points"] for r in prior)
    total_minutes = sum(r["minutes"] for r in prior)
    return [
        mean("points"), mean("minutes"), mean("xg"), mean("xa"), mean("ict"), mean("bonus"),
        sum(1 for r in recent if r["starts"] > 0) / n_recent, mean("xgc"),
        total_points / rounds_elapsed, total_minutes / (90 * rounds_elapsed), float(len(prior)),
        price, float(is_home), difficulty,
        float(position == 1), float(position == 2), float(position == 3), float(position == 4),
    ]


@dataclass
class Dataset:
    X: np.ndarray
    y: np.ndarray
    rounds: np.ndarray
    player_ids: np.ndarray
    baseline_rolling: np.ndarray  # mean points over last WINDOW rounds
    baseline_ppg: np.ndarray      # points per round to date


def build_dataset(
    histories: dict[int, list[dict[str, Any]]],
    positions: dict[int, int],
    fixture_difficulty: dict[tuple[int, bool], float],
    first_round: int = 1,
    min_prior_rounds: int = 2,
) -> Dataset:
    """One row per (player, past fixture). Features use rounds < that fixture's round only."""
    X, y, rounds_col, pids, b_roll, b_ppg = [], [], [], [], [], []
    for pid, history in histories.items():
        if not history:
            continue
        agg = _round_aggregates(history)
        for h in history:
            rnd = int(h["round"])
            if rnd - first_round < min_prior_rounds:
                continue
            is_home = bool(h.get("was_home"))
            diff = fixture_difficulty.get((int(h.get("fixture", 0)), is_home), 3.0)
            feats = _features(agg, rnd, positions.get(pid, 3), _f(h, "value") / 10, is_home, diff, first_round)
            X.append(feats)
            y.append(_f(h, "total_points"))
            rounds_col.append(rnd)
            pids.append(pid)
            b_roll.append(feats[0])
            b_ppg.append(feats[8])
    return Dataset(
        np.array(X, dtype=float).reshape(-1, len(FEATURES)), np.array(y, dtype=float), np.array(rounds_col),
        np.array(pids), np.array(b_roll), np.array(b_ppg),
    )


def new_model() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40,
        l2_regularization=1.0, random_state=42,
    )


@dataclass
class Backtest:
    test_rounds: list[int]
    n_rows: int
    mae: dict[str, float] = field(default_factory=dict)
    top50_mean_points: dict[str, float] = field(default_factory=dict)  # avg actual pts of each method's top 50 per round

    def beats_baselines(self) -> bool:
        return bool(self.mae) and self.mae["model"] < min(self.mae["rolling_4"], self.mae["ppg_to_date"])

    def as_dict(self) -> dict[str, Any]:
        return {"test_rounds": self.test_rounds, "n_rows": self.n_rows,
                "mae": {k: round(v, 3) for k, v in self.mae.items()},
                "top50_mean_points": {k: round(v, 3) for k, v in self.top50_mean_points.items()}}


def walk_forward_backtest(ds: Dataset, n_test_rounds: int = 3, min_train_rounds: int = 3) -> Backtest:
    """Expanding window: for each of the last n rounds, train on earlier rounds and predict it."""
    all_rounds = sorted(set(ds.rounds.tolist()))
    test_rounds = [r for r in all_rounds[-n_test_rounds:] if sum(1 for x in all_rounds if x < r) >= min_train_rounds]
    errs: dict[str, list[float]] = defaultdict(list)
    tops: dict[str, list[float]] = defaultdict(list)
    for r in test_rounds:
        train, test = ds.rounds < r, ds.rounds == r
        model = new_model().fit(ds.X[train], ds.y[train])
        preds = {"model": model.predict(ds.X[test]), "rolling_4": ds.baseline_rolling[test], "ppg_to_date": ds.baseline_ppg[test]}
        actual = ds.y[test]
        for name, p in preds.items():
            errs[name].extend(np.abs(p - actual).tolist())
            top = np.argsort(-p)[:50]
            tops[name].append(float(actual[top].mean()))
    return Backtest(
        test_rounds=test_rounds, n_rows=int(sum((ds.rounds == r).sum() for r in test_rounds)),
        mae={k: float(np.mean(v)) for k, v in errs.items()},
        top50_mean_points={k: float(np.mean(v)) for k, v in tops.items()},
    )


def predict_next_round(
    model: HistGradientBoostingRegressor,
    histories: dict[int, list[dict[str, Any]]],
    upcoming: dict[int, list[dict[str, Any]]],
    positions: dict[int, int],
    prices: dict[int, float],
    next_round: int,
    first_round: int = 1,
) -> dict[int, float]:
    """Expected points for `next_round`: summed over a double GW, 0 for a blank."""
    rows, owners = [], []
    for pid, fixtures in upcoming.items():
        agg = _round_aggregates(histories.get(pid, []))
        for fx in fixtures:
            if fx.get("event") != next_round:
                continue
            rows.append(_features(agg, next_round, positions.get(pid, 3), prices.get(pid, 5.0),
                                  bool(fx.get("is_home")), float(fx.get("difficulty", 3)), first_round))
            owners.append(pid)
    out = {pid: 0.0 for pid in upcoming}
    if rows:
        for pid, p in zip(owners, model.predict(np.array(rows)), strict=True):
            out[pid] += max(float(p), 0.0)
    return out

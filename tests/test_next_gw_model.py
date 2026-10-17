"""Leakage, backtest and prediction behaviour of the next-gameweek model (synthetic histories)."""

import copy
import random

import numpy as np

from app.ml.next_gw import FEATURES, build_dataset, new_model, predict_next_round, walk_forward_backtest

N_ROUNDS = 12


def _synthetic(seed=0, n_players=300):
    """Latent quality + fixture difficulty drive points; minutes vary. Returns histories, positions, difficulty map."""
    rng = random.Random(seed)
    histories, positions, diff_map = {}, {}, {}
    for pid in range(1, n_players + 1):
        quality = rng.uniform(0.5, 6.0)
        positions[pid] = rng.choice([1, 2, 2, 3, 3, 3, 4])
        hist = []
        for rnd in range(1, N_ROUNDS + 1):
            fixture = rnd * 1000 + pid
            is_home = rng.random() < 0.5
            diff = rng.choice([2, 2, 3, 3, 4, 5])
            diff_map[(fixture, is_home)] = diff
            plays = rng.random() < 0.85
            mean_pts = quality * (1.6 - 0.25 * diff) * (1.1 if is_home else 0.9) if plays else 0
            pts = max(-1, round(rng.gauss(mean_pts, 1.5))) if plays else 0
            hist.append({"round": rnd, "fixture": fixture, "was_home": is_home, "total_points": pts,
                         "minutes": 90 if plays else 0, "starts": int(plays), "value": 50 + int(quality * 10),
                         "expected_goals": str(quality * 0.05), "expected_assists": "0.1", "ict_index": str(quality * 2),
                         "bonus": int(pts > 8), "expected_goals_conceded": "1.0"})
        histories[pid] = hist
    return histories, positions, diff_map


def test_features_never_see_the_target_round_or_later():
    histories, positions, diff = _synthetic(n_players=40)
    ds = build_dataset(histories, positions, diff)
    tampered = copy.deepcopy(histories)
    for hist in tampered.values():
        for h in hist:
            if h["round"] >= 8:
                h["total_points"] += 50
                h["minutes"] = 0
    ds2 = build_dataset(tampered, positions, diff)
    mask = ds.rounds == 8
    np.testing.assert_array_equal(ds.X[mask], ds2.X[mask])        # features for round 8 unchanged
    assert not np.array_equal(ds.y[mask], ds2.y[mask])              # …while the target did change


def test_dataset_shape_and_baselines():
    histories, positions, diff = _synthetic(n_players=20)
    ds = build_dataset(histories, positions, diff, min_prior_rounds=2)
    assert ds.X.shape == (20 * (N_ROUNDS - 2), len(FEATURES))
    assert ds.rounds.min() == 3
    np.testing.assert_array_equal(ds.baseline_rolling, ds.X[:, FEATURES.index("mean_points")])


def test_backtest_model_beats_naive_baselines_when_fixtures_matter():
    histories, positions, diff = _synthetic()
    bt = walk_forward_backtest(build_dataset(histories, positions, diff), n_test_rounds=3)
    assert bt.test_rounds == [10, 11, 12]
    assert bt.beats_baselines(), bt.as_dict()
    assert bt.top50_mean_points["model"] >= bt.top50_mean_points["ppg_to_date"] - 0.25


def test_predict_next_round_sums_doubles_and_zeroes_blanks():
    histories, positions, diff = _synthetic(n_players=60)
    ds = build_dataset(histories, positions, diff)
    model = new_model().fit(ds.X, ds.y)
    nxt = N_ROUNDS + 1
    single = {"event": nxt, "is_home": True, "difficulty": 2}
    upcoming = {1: [single], 2: [single, {"event": nxt, "is_home": False, "difficulty": 2}], 3: [{"event": nxt + 1, "is_home": True, "difficulty": 2}]}
    histories[2] = histories[1]  # identical form so the double is directly comparable
    preds = predict_next_round(model, histories, upcoming, positions | {2: positions[1]}, {1: 6.0, 2: 6.0, 3: 6.0}, nxt)
    assert preds[3] == 0.0
    assert preds[2] > preds[1] > 0


# ── Service integration ───────────────────────────────────────────────────────

import asyncio  # noqa: E402

import pytest  # noqa: E402

from app.config import settings  # noqa: E402
from app.services.prediction_service import PredictionService  # noqa: E402


class _FakeData:
    def __init__(self):
        self.histories, self.positions, diff = _synthetic(n_players=200)
        self.fixtures = [{"id": fx, "team_h_difficulty": d if home else 3, "team_a_difficulty": d if not home else 3}
                         for (fx, home), d in diff.items()]

    async def get_bootstrap_data(self):
        events = [{"id": r, "finished": r <= N_ROUNDS, "is_next": r == N_ROUNDS + 1} for r in range(1, 39)]
        elements = [{"id": pid, "element_type": pos, "now_cost": 60, "minutes": 900} for pid, pos in self.positions.items()]
        return {"events": events, "elements": elements}

    async def get_all_fixtures(self):
        return self.fixtures

    async def get_player_history(self, pid):
        return {"history": self.histories[pid],
                "fixtures": [{"event": N_ROUNDS + 1, "is_home": pid % 2 == 0, "difficulty": 2 + pid % 3}]}


def test_refresh_activates_model_and_predictions_use_it(monkeypatch):
    monkeypatch.setattr(settings, "PREDICTION_MODEL", "auto")
    svc = PredictionService()
    asyncio.run(svc.refresh_next_gw(_FakeData()))
    assert svc.next_gw_active
    info = asyncio.run(svc.get_model_info())
    assert info["active"] == "next_gw"
    assert info["models"]["next_gw"]["backtest"]["beats_baselines"]
    assert "accuracy" not in str(info)  # no invented accuracy figures
    preds = svc.predict_batch([{"id": 1, "form": "0"}, {"id": 99999, "form": "9"}], "ensemble")
    assert preds[0] == round(svc._next_gw_preds[1], 2) and preds[1] == 0.0
    assert svc.predict_batch([{"id": 1, "form": "4", "points_per_game": "4", "ict_index": "10"}], "basic") == [3.7]


@pytest.mark.parametrize("mode", ["legacy"])
def test_legacy_mode_never_fetches(monkeypatch, mode):
    monkeypatch.setattr(settings, "PREDICTION_MODEL", mode)
    svc = PredictionService()

    class _Boom:
        async def get_bootstrap_data(self):
            raise AssertionError("should not fetch in legacy mode")

    asyncio.run(svc.refresh_next_gw(_Boom()))
    assert not svc.next_gw_active


def test_failed_refresh_keeps_snapshot_and_retries_soon(monkeypatch):
    monkeypatch.setattr(settings, "PREDICTION_MODEL", "auto")
    svc = PredictionService()

    class _Down:
        async def get_bootstrap_data(self):
            raise RuntimeError("FPL down")

    asyncio.run(svc.refresh_next_gw(_Down()))
    assert not svc.next_gw_active
    assert not svc.next_gw_stale()                 # not immediately…
    assert svc.next_gw_stale(max_age_s=1700)       # …but well before 6h

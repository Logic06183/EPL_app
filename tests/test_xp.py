"""
Expected-points model: the serving path (FPL API shapes) must produce the
same predictions as the training path, on a synthetic season.
"""

import itertools

import joblib
import numpy as np
import pandas as pd
import pytest

from app.ml.features import CORE_STATS, EXTRA_STATS, FEATURES, predict_points, prior_season
from app.services.prediction_service import PredictionService
from app.services.xp_service import (
    ML_DIR, XPService, availability, fixtures_frame, player_gw_frame, predict_gameweeks,
)
from ml.train import load_season

SEASON, PRIOR = "2025-26", "2024-25"
TEAMS = {1: "Ares", 2: "Bolts", 3: "Comets", 4: "Dynamo"}
POS = ["GK", "DEF", "MID", "FWD"]
N_GW = 8


@pytest.fixture(scope="module")
def bundle():
    return joblib.load(ML_DIR / "model.joblib")


@pytest.fixture(scope="module")
def season(tmp_path_factory):
    """Writes a small vaastav-format season: 4 teams, 8 gameweeks, 4 players each."""
    rng = np.random.default_rng(0)
    d = tmp_path_factory.mktemp("data")
    pairs = list(itertools.combinations(TEAMS, 2))
    fixtures, rows, fid = [], [], 0
    for gw in range(1, N_GW + 1):
        a, b = pairs[(gw - 1) % len(pairs)]
        others = [t for t in TEAMS if t not in (a, b)]
        for h, aw in ((a, b), tuple(others)):
            fid += 1
            fixtures.append({"id": fid, "event": gw, "team_h": h, "team_a": aw,
                             "team_h_score": int(rng.integers(0, 4)), "team_a_score": int(rng.integers(0, 4)),
                             "finished": True})
    players = [{"id": t * 10 + i, "code": 1000 + t * 10 + i, "team": t, "pos": POS[i]}
               for t in TEAMS for i in range(4)]
    for f in fixtures:
        for p in players:
            if p["team"] not in (f["team_h"], f["team_a"]):
                continue
            home = p["team"] == f["team_h"]
            mins = int(rng.choice([0, 30, 90]))
            rows.append({
                "name": f"P{p['id']}", "position": p["pos"], "team": TEAMS[p["team"]], "xP": 0.0,
                "element": p["id"], "GW": f["event"], "fixture": f["id"],
                "opponent_team": f["team_a"] if home else f["team_h"], "was_home": home,
                "value": 50 + p["id"] % 7, "minutes": mins, "starts": int(mins == 90),
                "total_points": int(rng.integers(0, 10)) if mins else 0,
                "goals_scored": 0, "assists": 0, "bps": int(rng.integers(0, 30)),
                "expected_goals": round(float(rng.random()) / 2, 2),
                "expected_assists": round(float(rng.random()) / 3, 2),
                "bonus": int(rng.integers(0, 4)), "threat": float(rng.integers(0, 60)),
                "creativity": float(rng.integers(0, 60)), "influence": float(rng.integers(0, 60)),
                "defensive_contribution": int(rng.integers(0, 3)), "saves": int(rng.integers(0, 5)),
                "expected_goals_conceded": round(float(rng.random()) * 2, 2),
                # Ownership and net transfers for this gameweek (pre-deadline numbers)
                "selected": 1000 * (p["id"] % 9 + 1) + f["event"],
                "transfers_in": (p["id"] * 7 + f["event"]) % 500, "transfers_out": (p["id"] * 3 + f["event"]) % 400,
                "team_h_score": f["team_h_score"], "team_a_score": f["team_a_score"],
            })
    pd.DataFrame(rows).to_csv(d / f"merged_{SEASON}.csv", index=False)
    pd.DataFrame({"id": list(TEAMS), "name": list(TEAMS.values())}).to_csv(d / f"teams_{SEASON}.csv", index=False)
    raw = pd.DataFrame({"id": [p["id"] for p in players], "code": [p["code"] for p in players],
                        "minutes": 2000, "total_points": 100, "expected_goal_involvements": 5.0})
    raw.to_csv(d / f"players_raw_{SEASON}.csv", index=False)
    raw.to_csv(d / f"players_raw_{PRIOR}.csv", index=False)
    return d, fixtures, players


def _live(rows: pd.DataFrame, gw: int) -> dict:
    g = rows[rows["GW"] == gw].groupby("element").sum(numeric_only=True)
    return {"elements": [{"id": int(el), "stats": {c: float(r[c]) for c in CORE_STATS + list(EXTRA_STATS)}}
                         for el, r in g.iterrows()]}


def test_model_bundle_matches_feature_list(bundle):
    assert bundle["features"] == FEATURES


def test_serving_matches_training(season, bundle):
    d, fixtures, players = season
    target = 6
    rows, _, _ = load_season(d, SEASON)
    t = rows[rows["gw"] == target].copy()
    t["pred"] = predict_points(bundle, t[FEATURES])
    expected = t.groupby("element")["pred"].sum().clip(lower=0)

    raw = pd.read_csv(d / f"merged_{SEASON}.csv")
    api_fixtures = [{**f, "finished": f["event"] < target,
                     "team_h_score": f["team_h_score"] if f["event"] < target else None,
                     "team_a_score": f["team_a_score"] if f["event"] < target else None}
                    for f in fixtures]
    fx = fixtures_frame(api_fixtures)
    # The bootstrap carries ownership as a percentage and net transfers as two counts;
    # the ranks the model sees must match the training rows for the target gameweek.
    tgt = raw[raw["GW"] == target].drop_duplicates("element").set_index("element")
    elements = [{"id": p["id"], "code": p["code"], "team": p["team"],
                 "element_type": POS.index(p["pos"]) + 1, "now_cost": 50 + p["id"] % 7,
                 "selected_by_percent": str(tgt.loc[p["id"], "selected"] / 1000),
                 "transfers_in_event": int(tgt.loc[p["id"], "transfers_in"]),
                 "transfers_out_event": int(tgt.loc[p["id"], "transfers_out"]),
                 # value is constant per player in the synthetic season, so no price change
                 "cost_change_event": 0}
                for p in players]
    live = {gw: _live(raw, gw) for gw in range(1, target)}
    pgw = player_gw_frame(elements, live, fx)
    prior = prior_season(pd.read_csv(d / f"players_raw_{PRIOR}.csv"))

    got = predict_gameweeks(bundle, elements, pgw, fx, target, prior, horizon=2)
    for el, v in expected.items():
        assert got[el][target] == pytest.approx(v, abs=1e-9)
    assert set(got[players[0]["id"]]) == {target, target + 1}


def test_blank_gameweek_predicts_zero(season, bundle):
    _, fixtures, players = season
    fx = fixtures_frame([{**f, "finished": False} for f in fixtures if f["event"] != 3])
    elements = [{"id": p["id"], "code": p["code"], "team": p["team"],
                 "element_type": POS.index(p["pos"]) + 1, "now_cost": 50} for p in players]
    got = predict_gameweeks(bundle, elements, player_gw_frame(elements, {}, fx), fx, 3, None, horizon=2)
    assert all(v[3] == 0.0 for v in got.values())
    assert any(v[4] > 0 for v in got.values())


def test_availability():
    assert availability({"chance_of_playing_next_round": None, "status": "a"}) == 1.0
    assert availability({"chance_of_playing_next_round": 25, "status": "d"}) == 0.25
    assert availability({"chance_of_playing_next_round": None, "status": "u"}) == 0.0


def test_prediction_service_falls_back_to_form_until_ready():
    svc = PredictionService(xp=XPService())
    player = {"id": 1, "form": "6.0", "points_per_game": "5.0", "ict_index": "100"}
    assert svc.predict(player, "xp") == pytest.approx(6 * 0.5 + 5 * 0.4 + 10 * 0.1)


def test_prediction_service_uses_model_when_ready():
    xp = XPService()
    xp.xp, xp.next_gw = {1: {9: 4.2, 10: 3.1}}, 9
    svc = PredictionService(xp=xp)
    assert svc.predict({"id": 1}, "ensemble") == 4.2   # legacy alias
    assert svc.predict({"id": 2}, "xp") == 0.0          # unknown player / no fixture
    assert svc.horizon(1) == [4.2, 3.1]


def test_refresh_after_season_end_marks_fresh():
    import asyncio

    class Fake:
        calls = 0

        async def get_bootstrap_data(self):
            Fake.calls += 1
            return {"events": [{"id": 38, "finished": True, "is_next": False}], "elements": []}

    svc = XPService()
    asyncio.run(svc.ensure_fresh(Fake()))
    asyncio.run(svc.ensure_fresh(Fake()))
    assert Fake.calls == 1 and svc.updated_at is not None


def test_captain_score_shrinks_toward_season_rate():
    from app.services.xp_service import CAPTAIN_SHRINK
    xp = XPService()
    xp.xp, xp.next_gw = {1: {9: 8.0, 10: 7.0}, 2: {9: 7.5, 10: 7.0}}, 9
    xp.team_of = {1: 10, 2: 11}
    xp.fixture_counts = {(10, 9): 1, (11, 9): 1, (10, 10): 2, (11, 10): 1}
    xp.season_rate = {1: 4.0, 2: 9.0}      # player 2 has been the better scorer all season
    assert xp.captain_score(1) == pytest.approx(CAPTAIN_SHRINK * 8.0 + (1 - CAPTAIN_SHRINK) * 4.0)
    assert xp.captain_score(2) > xp.captain_score(1)        # shrinkage flips the pick
    assert xp.captain_horizon(1)[1] == pytest.approx(CAPTAIN_SHRINK * 7.0 + (1 - CAPTAIN_SHRINK) * 4.0 * 2)
    svc = PredictionService(xp=xp)
    assert svc.captain_score(2) == xp.captain_score(2)

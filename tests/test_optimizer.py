from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pytest

from app.services.optimizer import Candidate, optimise


def _pool(seed=0, n_teams=20, per_team=8):
    rng = np.random.default_rng(seed)
    cands, pid = [], 0
    positions = [1, 2, 2, 2, 3, 3, 3, 4]
    for team in range(1, n_teams + 1):
        for pos in positions[:per_team]:
            pid += 1
            price = round(float(rng.uniform(4.0, 13.0)), 1)
            base = price * 0.5 + float(rng.normal(0, 0.8))
            cands.append(Candidate(pid, pos, team, price, [max(0.0, base + float(rng.normal(0, 0.5))) for _ in range(3)]))
    return cands


def _valid(plan, cands, budget):
    by_id = {c.id: c for c in cands}
    squad = [by_id[i] for i in plan.squad]
    assert len(squad) == 15
    assert Counter(c.position for c in squad) == {1: 2, 2: 5, 3: 5, 4: 3}
    assert max(Counter(c.team for c in squad).values()) <= 3
    assert sum(c.price for c in squad) <= budget + 1e-6
    for xi, cap in zip(plan.lineups, plan.captains):
        assert len(xi) == 11 and set(xi) <= set(plan.squad) and cap in xi
        pos = Counter(by_id[i].position for i in xi)
        assert pos[1] == 1 and pos[2] >= 3 and pos[3] >= 2 and pos[4] >= 1


def test_builds_valid_squad_within_budget():
    cands = _pool()
    plan = optimise(cands, budget=100.0)
    _valid(plan, cands, 100.0)
    assert plan.hits == 0 and plan.transfers_in == []


def test_holding_is_chosen_when_no_transfer_beats_the_hit():
    cands = _pool(1)
    start = optimise(cands, budget=100.0)
    # Already optimal squad, no free transfers: any move costs 4 and can't pay back
    plan = optimise(cands, budget=start.cost, current=start.squad, free_transfers=0)
    assert plan.transfers_in == [] and plan.hits == 0


def test_transfers_out_an_injured_player():
    cands = _pool(2)
    start = optimise(cands, budget=100.0)
    star = max(start.squad, key=lambda i: sum(next(c for c in cands if c.id == i).xp))
    injured = [Candidate(c.id, c.position, c.team, c.price, [0.0, 0.0, 0.0]) if c.id == star else c
               for c in cands]
    plan = optimise(injured, budget=start.cost + 0.5, current=start.squad, free_transfers=1)
    _valid(plan, injured, start.cost + 0.5)
    assert star in plan.transfers_out
    assert len(plan.transfers_in) == len(plan.transfers_out) >= 1
    assert plan.hits == max(0, len(plan.transfers_in) - 1)


def test_hits_are_charged_in_expected_points():
    cands = _pool(3)
    start = optimise(cands, budget=100.0)
    zeroed = [Candidate(c.id, c.position, c.team, c.price, [0.0] * 3) if c.id in start.squad[:4] else c
              for c in cands]
    plan = optimise(zeroed, budget=start.cost + 2, current=start.squad, free_transfers=1, max_transfers=4)
    assert plan.expected_points == pytest.approx(sum(plan.per_gw_points) - 4 * plan.hits, abs=0.01)


def test_optimize_endpoint_returns_valid_squad():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.data_service import get_data_service
    from app.services.prediction_service import PredictionService, get_prediction_service
    from app.services.xp_service import XPService

    cands = _pool(4)
    elements = [{"id": c.id, "web_name": f"P{c.id}", "element_type": c.position, "team": c.team,
                 "now_cost": int(round(c.price * 10)), "status": "a", "form": "1.0",
                 "selected_by_percent": "1.0"} for c in cands]

    class FakeData:
        async def get_bootstrap_data(self):
            return {"elements": elements, "teams": [{"id": t, "name": f"T{t}"} for t in range(1, 21)]}

    xp = XPService()
    xp.xp, xp.next_gw = {c.id: {10 + g: v for g, v in enumerate(c.xp)} for c in cands}, 10
    xp.updated_at = datetime.now(timezone.utc)

    app.dependency_overrides[get_data_service] = lambda: FakeData()
    app.dependency_overrides[get_prediction_service] = lambda: PredictionService(xp=xp)
    try:
        r = TestClient(app).post("/api/teams/optimize", json={"budget": 100})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["squad"]) == 15
    assert sum(p["is_starting"] for p in body["squad"]) == 11
    assert sum(p["is_captain"] for p in body["squad"]) == 1
    assert body["total_cost"] <= 100


def test_estimate_free_transfers():
    from app.services.optimizer import estimate_free_transfers

    def hist(transfers, chips=()):
        return {"current": [{"event": i + 1, "event_transfers": t} for i, t in enumerate(transfers)],
                "chips": [{"event": e, "name": n} for e, n in chips]}

    assert estimate_free_transfers(hist([0])) == 1               # after GW1
    assert estimate_free_transfers(hist([0, 0, 0])) == 3         # banked two
    assert estimate_free_transfers(hist([0] * 10)) == 5          # capped at 5
    assert estimate_free_transfers(hist([0, 0, 2])) == 1         # used both, +1
    assert estimate_free_transfers(hist([0, 3])) == 1            # took a hit
    assert estimate_free_transfers(hist([0, 0, 9], [(3, "wildcard")])) == 3  # wildcard keeps bank
    assert estimate_free_transfers({}) == 1

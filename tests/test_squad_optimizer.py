"""FPL rule compliance for the squad optimiser and /api/teams/optimize."""

import random
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_service import get_data_service
from app.services.prediction_service import get_prediction_service
from app.services.squad_optimizer import Candidate, InfeasibleSquad, optimise_squad

PRICE_RANGE = {1: (4.0, 6.0), 2: (4.0, 7.5), 3: (4.5, 13.5), 4: (4.5, 15.0)}
PER_CLUB = {1: 3, 2: 8, 3: 8, 4: 4}


def _league(seed=0):
    """20 clubs, realistic price bands, points loosely correlated with price."""
    rng = random.Random(seed)
    players, pid = [], 1
    for club in range(1, 21):
        for pos, count in PER_CLUB.items():
            for _ in range(count):
                lo, hi = PRICE_RANGE[pos]
                price = round(rng.uniform(lo, hi) * 2) / 2
                players.append(Candidate(pid, pos, club, price, max(0.0, price * 0.6 + rng.gauss(0, 1.5))))
                pid += 1
    return players


def _check_rules(result, candidates, budget):
    by_id = {c.id: c for c in candidates}
    squad = [by_id[i] for i in result.squad_ids]
    xi = [by_id[i] for i in result.starting_ids]
    assert len(squad) == 15
    assert Counter(c.position for c in squad) == {1: 2, 2: 5, 3: 5, 4: 3}
    assert max(Counter(c.club for c in squad).values()) <= 3
    assert sum(c.price for c in squad) <= budget + 1e-6
    assert len(xi) == 11 and set(result.starting_ids) <= set(result.squad_ids)
    xi_pos = Counter(c.position for c in xi)
    assert xi_pos[1] == 1 and 3 <= xi_pos[2] <= 5 and 2 <= xi_pos[3] <= 5 and 1 <= xi_pos[4] <= 3
    assert result.captain_id in result.starting_ids


@pytest.mark.parametrize("budget", [83.0, 100.0, 110.0])
def test_squad_obeys_fpl_rules(budget):
    league = _league()
    _check_rules(optimise_squad(league, budget), league, budget)


def test_club_limit_binds_when_one_club_dominates():
    league = _league(seed=1)
    # Make club 1 absurdly good — a naive picker would take all of them.
    league = [Candidate(c.id, c.position, c.club, c.price, c.predicted + (20 if c.club == 1 else 0)) for c in league]
    result = optimise_squad(league, 100.0)
    by_id = {c.id: c for c in league}
    assert sum(1 for i in result.squad_ids if by_id[i].club == 1) == 3


def test_captain_is_best_starter():
    league = _league(seed=2)
    result = optimise_squad(league, 100.0)
    by_id = {c.id: c for c in league}
    assert by_id[result.captain_id].predicted == max(by_id[i].predicted for i in result.starting_ids)


def test_beats_value_greedy_baseline():
    """The old endpoint sorted by points-per-£ and filled greedily; the MILP must do at least as well."""
    league = _league(seed=3)
    result = optimise_squad(league, 100.0)
    by_id = {c.id: c for c in league}
    xi_points = sum(by_id[i].predicted for i in result.starting_ids)

    slots, picked, remaining = {1: 2, 2: 5, 3: 5, 4: 3}, [], 100.0
    for c in sorted(league, key=lambda c: c.predicted / c.price, reverse=True):
        if slots[c.position] and c.price <= remaining:
            picked.append(c)
            slots[c.position] -= 1
            remaining -= c.price
    greedy_xi = sorted(picked, key=lambda c: -c.predicted)[:11]
    assert xi_points >= sum(c.predicted for c in greedy_xi)


def test_infeasible_budget_raises():
    with pytest.raises(InfeasibleSquad):
        optimise_squad(_league(), 30.0)


# ── Endpoint ──────────────────────────────────────────────────────────────────

class _FakeData:
    def __init__(self, league):
        self._league = league

    async def get_bootstrap_data(self):
        elements = [
            {"id": c.id, "web_name": f"P{c.id}", "team": c.club, "element_type": c.position,
             "now_cost": int(c.price * 10), "form": str(c.predicted), "status": "a",
             "chance_of_playing_next_round": None, "selected_by_percent": "1.0"}
            for c in self._league
        ]
        elements[0]["status"] = "i"  # injured — must never be picked
        return {"elements": elements, "teams": [{"id": i, "name": f"Club {i}"} for i in range(1, 21)]}


class _FakePredictions:
    _trained = False

    async def ensure_trained(self, players):
        pass

    def predict_batch(self, players, model_type):
        return [float(p["form"]) for p in players]


@pytest.fixture
def client():
    league = _league(seed=4)
    app.dependency_overrides[get_data_service] = lambda: _FakeData(league)
    app.dependency_overrides[get_prediction_service] = lambda: _FakePredictions()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_optimize_endpoint_returns_legal_squad(client):
    r = client.post("/api/teams/optimize", json={"budget": 100})
    assert r.status_code == 200
    d = r.json()
    squad = d["squad"]
    assert len(squad) == 15
    assert 1 not in {p["id"] for p in squad}
    assert max(Counter(p["team"] for p in squad).values()) <= 3
    assert sum(p["is_starting"] for p in squad) == 11
    assert sum(p["is_captain"] for p in squad) == 1
    d_, m_, f_ = map(int, d["formation"].split("-"))
    assert d_ + m_ + f_ == 10
    assert d["total_cost"] <= 100 and d["remaining_budget"] >= 0


def test_optimize_endpoint_rejects_silly_budget(client):
    assert client.post("/api/teams/optimize", json={"budget": 5}).status_code == 422

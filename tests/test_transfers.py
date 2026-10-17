"""Transfer suggestions must respect FPL rules (club limit, availability, budget)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_service import get_data_service
from app.services.prediction_service import get_prediction_service

# Squad: 11 starters + 4 bench. Club 1 already has 3 players (ids 1, 2, 3).
SQUAD = [
    # id, club, pos, price(£m), form
    (1, 1, 3, 6.0, 2.0),   # MID, club 1 — weak, prime sell candidate
    (2, 1, 2, 5.0, 4.0),
    (3, 1, 4, 7.0, 5.0),
    (4, 2, 1, 4.5, 4.0),
    (5, 3, 2, 4.5, 4.0), (6, 4, 2, 4.5, 4.0), (7, 5, 2, 4.5, 4.0),
    (8, 6, 3, 6.0, 1.0),   # MID, club 6 — weakest, sell candidate
    (9, 7, 3, 6.0, 5.0), (10, 8, 3, 6.0, 5.0),
    (11, 9, 4, 7.0, 5.0),
    (12, 10, 1, 4.0, 1.0), (13, 11, 2, 4.0, 1.0), (14, 12, 3, 4.5, 1.0), (15, 13, 4, 4.5, 1.0),
]
CANDIDATES = [
    (100, 1, 3, 6.0, 9.0, "a"),   # club 1 star — only legal if selling a club-1 player (id 1)
    (101, 14, 3, 6.0, 8.0, "i"),  # injured — never suggest
    (102, 15, 3, 6.0, 7.0, "a"),  # legal
    (103, 16, 3, 15.0, 9.5, "a"), # unaffordable
]


def _element(pid, club, pos, price, form, status="a"):
    return {"id": pid, "web_name": f"P{pid}", "team": club, "element_type": pos, "now_cost": int(price * 10),
            "form": str(form), "status": status, "chance_of_playing_next_round": 0 if status == "i" else None,
            "selected_by_percent": "1.0", "total_points": 10}


class _FakeData:
    def __init__(self):
        self.elements = [_element(*s) for s in SQUAD] + [_element(*c) for c in CANDIDATES]

    async def get_gameweek_info(self):
        return {"current": {"id": 5}}

    async def get_bootstrap_data(self):
        return {"elements": self.elements,
                "teams": [{"id": i, "name": f"Club {i}"} for i in range(1, 17)],
                "element_types": [{"id": i, "singular_name_short": n} for i, n in enumerate(["GK", "DEF", "MID", "FWD"], 1)]}

    async def _get_client(self):
        def handler(request):
            if request.url.path.endswith("/picks/"):
                return httpx.Response(200, json={"picks": [{"element": s[0], "position": i + 1} for i, s in enumerate(SQUAD)]})
            return httpx.Response(200, json={"name": "Test XI", "last_deadline_bank": 5})  # £0.5m in the bank
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class _FormPredictions:
    _trained = True

    async def ensure_trained(self, players):
        pass

    def predict_batch(self, players, model_type):
        return [float(p["form"]) for p in players]


@pytest.fixture
def client():
    app.dependency_overrides[get_data_service] = lambda: _FakeData()
    app.dependency_overrides[get_prediction_service] = lambda: _FormPredictions()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_transfers_respect_club_limit_availability_and_budget(client):
    r = client.get("/api/fpl-team/42/transfers")
    assert r.status_code == 200, r.text
    pairs = {(s["sell"]["id"], s["buy"]["id"]) for s in r.json()["suggestions"]}
    buys = {b for _, b in pairs}

    assert 101 not in buys, "injured player suggested"
    assert 103 not in buys, "unaffordable player suggested"
    assert 102 in buys
    # Club-1 star may only come in for a club-1 player.
    assert all(sell == 1 for sell, buy in pairs if buy == 100)
    assert (1, 100) in pairs


def test_team_import_reports_bank_in_pounds(client):
    d = client.get("/api/fpl-team/42").json()
    assert d["bank"] == 0.5
    assert len(d["picks"]) == 15 and sum(p["is_starting"] for p in d["picks"]) == 11

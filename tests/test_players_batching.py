"""List endpoints must use one vectorised predict, never per-player predict() (was 42s → 0.07s)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_service import get_data_service
from app.services.prediction_service import get_prediction_service


class _Data:
    async def get_bootstrap_data(self):
        elements = [{"id": i, "web_name": f"P{i}", "team": 1 + i % 20, "element_type": 1 + i % 4, "now_cost": 50 + i % 60,
                     "form": "3.0", "points_per_game": "3.0", "selected_by_percent": "4.0", "minutes": 500,
                     "total_points": 30, "status": "a", "chance_of_playing_next_round": None,
                     "transfers_in_event": i, "transfers_out_event": 0} for i in range(1, 401)]
        return {"elements": elements, "teams": [{"id": t, "name": f"C{t}", "short_name": f"C{t}"} for t in range(1, 21)],
                "element_types": [{"id": i, "singular_name_short": n} for i, n in enumerate(["GKP", "DEF", "MID", "FWD"], 1)],
                "events": [{"id": 9, "is_next": True, "finished": False}, {"id": 10, "finished": False}, {"id": 11, "finished": False}]}

    async def get_fixtures(self, filter_type="upcoming", gameweek=None, limit=10):
        return [{"event": gw, "team_h": 2 * k + 1, "team_a": 2 * k + 2, "team_h_difficulty": 3, "team_a_difficulty": 3}
                for gw in (9, 10, 11) for k in range(10)]


class _Preds:
    _trained = True
    batch_calls = 0

    async def ensure_trained(self, players):
        pass

    def predict_batch(self, players, model_type="random_forest"):
        _Preds.batch_calls += 1
        return [float(p["id"] % 7) for p in players]

    def predict(self, player, model_type="random_forest"):
        raise AssertionError("per-player predict() called from a list endpoint")


@pytest.fixture
def client():
    app.dependency_overrides[get_data_service] = lambda: _Data()
    app.dependency_overrides[get_prediction_service] = lambda: _Preds()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("path", ["/api/players/captain", "/api/players/three-gw", "/api/players/value",
                                  "/api/players/differentials", "/api/players/predictions?model_type=ensemble"])
def test_list_endpoints_predict_in_one_batch(client, path):
    _Preds.batch_calls = 0
    r = client.get(path)
    assert r.status_code == 200, r.text
    assert _Preds.batch_calls == 1

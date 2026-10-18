import pytest

from app.services.league import league_ownership, league_view


def picks(*pairs):
    return [{"element": el, "multiplier": m} for el, m in pairs]


def test_effective_ownership_counts_captaincy():
    eo = league_ownership([picks((1, 2), (2, 1)), picks((1, 1), (3, 0))])
    assert eo == {1: 1.5, 2: 0.5, 3: 0.0}


def test_threats_and_differentials():
    rivals = [picks((10, 2), (20, 1)), picks((10, 2), (20, 1))]   # both captain 10, own 20
    mine = picks((10, 1), (30, 1))                                # I own 10 uncaptained, 30 nobody has
    xp = {10: 8.0, 20: 5.0, 30: 4.0}
    v = league_view(mine, rivals, xp)
    assert [t["id"] for t in v["threats"]] == [20]
    assert v["threats"][0]["swing"] == pytest.approx(-5.0)
    assert [u["id"] for u in v["undercovered"]] == [10]          # captained by everyone else
    assert v["undercovered"][0]["swing"] == pytest.approx(-8.0)
    assert [d["id"] for d in v["differentials"]] == [30]
    assert v["net_swing"] == pytest.approx(-9.0)


def test_mini_league_endpoint():
    from datetime import datetime, timezone

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.data_service import get_data_service
    from app.services.prediction_service import PredictionService, get_prediction_service
    from app.services.xp_service import XPService

    class Resp:
        def __init__(self, body, status=200):
            self._b, self.status_code = body, status

        def json(self):
            return self._b

        def raise_for_status(self):
            pass

    team_picks = {
        1: picks((10, 1), (30, 1)),          # me
        2: picks((10, 2), (20, 1)),
        3: picks((10, 2), (20, 1)),
    }

    class Client:
        async def get(self, url):
            if "leagues-classic" in url:
                return Resp({"league": {"name": "Office"}, "standings": {"results": [
                    {"entry": 2, "entry_name": "Rival A", "player_name": "A", "rank": 1, "total": 520},
                    {"entry": 1, "entry_name": "Me", "player_name": "Me", "rank": 2, "total": 500},
                    {"entry": 3, "entry_name": "Rival B", "player_name": "B", "rank": 3, "total": 490}]}})
            entry = int(url.split("/entry/")[1].split("/")[0])
            return Resp({"picks": team_picks[entry]})

    class FakeData:
        async def get_gameweek_info(self):
            return {"current": {"id": 8}}

        async def _get_client(self):
            return Client()

        async def get_bootstrap_data(self):
            return {"elements": [{"id": i, "web_name": f"P{i}", "team": 1} for i in (10, 20, 30)],
                    "teams": [{"id": 1, "short_name": "ARS"}]}

    xp = XPService()
    xp.xp, xp.next_gw, xp.updated_at = {10: {9: 8.0}, 20: {9: 5.0}, 30: {9: 4.0}}, 9, datetime.now(timezone.utc)
    app.dependency_overrides[get_data_service] = lambda: FakeData()
    app.dependency_overrides[get_prediction_service] = lambda: PredictionService(xp=xp)
    try:
        r = TestClient(app).get("/api/fpl-team/1/league/77")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["league"]["name"] == "Office" and body["you"]["rank"] == 2
    assert [x["name"] for x in body["threats"]] == ["P20"]
    assert body["rivals"][0]["gap"] == 20

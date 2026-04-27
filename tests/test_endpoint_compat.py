from fastapi.testclient import TestClient

from app.main import app
from app.services.data_service import get_data_service


class FakeDataService:
    async def get_bootstrap_data(self):
        return {
            "elements": [
                {
                    "id": 1,
                    "web_name": "Salah",
                    "first_name": "Mohamed",
                    "second_name": "Salah",
                    "team": 1,
                    "element_type": 3,
                    "now_cost": 130,
                    "form": "8.0",
                    "selected_by_percent": "45.0",
                    "total_points": 220,
                    "points_per_game": "7.0",
                    "ict_index": "300.0",
                    "minutes": 2500,
                    "transfers_in_event": 100000,
                    "transfers_out_event": 1000,
                    "cost_change_event": 1,
                    "news": "",
                },
                {
                    "id": 2,
                    "web_name": "Palmer",
                    "first_name": "Cole",
                    "second_name": "Palmer",
                    "team": 2,
                    "element_type": 3,
                    "now_cost": 105,
                    "form": "7.0",
                    "selected_by_percent": "35.0",
                    "total_points": 200,
                    "points_per_game": "6.5",
                    "ict_index": "250.0",
                    "minutes": 2400,
                    "transfers_in_event": 80000,
                    "transfers_out_event": 2000,
                    "cost_change_event": 0,
                    "news": "Knock - 75% chance of playing",
                    "chance_of_playing_next_round": 75,
                },
            ],
            "teams": [
                {"id": 1, "name": "Liverpool", "short_name": "LIV"},
                {"id": 2, "name": "Chelsea", "short_name": "CHE"},
            ],
            "element_types": [{"id": 3, "singular_name_short": "MID"}],
            "events": [
                {
                    "id": 34,
                    "name": "Gameweek 34",
                    "deadline_time": "2026-04-24T17:30:00Z",
                    "is_current": True,
                    "is_next": False,
                    "finished": False,
                }
            ],
        }

    async def get_fixtures(self, filter_type="upcoming", gameweek=None):
        return [
            {
                "id": 10,
                "event": 34,
                "kickoff_time": "2026-04-27T19:00:00Z",
                "finished": False,
                "started": False,
                "team_h": 1,
                "team_a": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 4,
            }
        ]

    async def get_gameweek_info(self):
        data = await self.get_bootstrap_data()
        current = data["events"][0]
        return {"current": current, "next": None, "all_events": data["events"]}

    async def get_player_by_id(self, player_id):
        data = await self.get_bootstrap_data()
        return next((player for player in data["elements"] if player["id"] == player_id), None)


def test_frontend_compatibility_endpoints_are_registered():
    app.dependency_overrides[get_data_service] = lambda: FakeDataService()
    client = TestClient(app)

    checks = [
        (client.get, "/api/players/predictions/enhanced?top_n=2"),
        (client.get, "/api/players/trending?top_n=2"),
        (client.get, "/api/players/injuries"),
        (client.get, "/api/players/search?q=salah"),
        (client.get, "/api/players/search/salah"),
        (client.get, "/api/users/me"),
        (client.get, "/api/gameweek/current"),
        (client.get, "/api/fixtures?filter=upcoming"),
    ]

    for method, path in checks:
        response = method(path)
        assert response.status_code == 200, path

    assert client.get("/api/players/captain?top_n=2").status_code == 403
    assert client.get("/api/players/price-movers").status_code == 403
    assert client.get("/api/players/value?top_n=5").status_code == 403
    assert client.get("/api/fpl-team/1234567").status_code == 403

    app.dependency_overrides.clear()


def test_gameweek_and_fixture_shapes_match_frontend():
    app.dependency_overrides[get_data_service] = lambda: FakeDataService()
    client = TestClient(app)

    gameweek = client.get("/api/gameweek/current").json()
    assert gameweek["gameweek"] == 34
    assert gameweek["deadline"] == "2026-04-24T17:30:00Z"
    assert gameweek["is_current"] is True

    fixture = client.get("/api/fixtures?filter=upcoming").json()["fixtures"][0]
    assert fixture["team_h_name"] == "Liverpool"
    assert fixture["team_a_name"] == "Chelsea"
    assert fixture["kickoff_time"] == "2026-04-27T19:00:00Z"
    assert fixture["event"] == 34

    app.dependency_overrides.clear()

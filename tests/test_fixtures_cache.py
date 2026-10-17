"""Fixture list completeness (FDR / 3-GW planner) and per-key cache expiry."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_service import FPLDataService, get_data_service
from app.utils.cache import CacheManager

# 20 clubs × 6 upcoming gameweeks = 60 fixtures (10 per GW)
FIXTURES = [
    {"id": gw * 100 + i, "event": gw, "team_h": 2 * i + 1, "team_a": 2 * i + 2, "finished": False,
     "kickoff_time": f"2026-11-{gw:02d}T15:00:00Z", "team_h_difficulty": 2, "team_a_difficulty": 4}
    for gw in range(10, 16) for i in range(10)
]


def test_get_fixtures_limit_none_returns_every_match():
    svc = FPLDataService()

    async def fake_all():
        return FIXTURES

    with patch.object(svc, "get_all_fixtures", fake_all):
        assert len(asyncio.run(svc.get_fixtures("upcoming"))) == 10            # default stays small for the UI list
        assert len(asyncio.run(svc.get_fixtures("upcoming", limit=None))) == 60


class _FakeData:
    async def get_bootstrap_data(self):
        return {
            "teams": [{"id": i, "name": f"Club {i:02d}", "short_name": f"C{i:02d}"} for i in range(1, 21)],
            "events": [{"id": gw, "is_current": gw == 10, "finished": False} for gw in range(10, 39)],
        }

    async def get_fixtures(self, filter_type="upcoming", gameweek=None, limit=10):
        return FIXTURES if limit is None else FIXTURES[:limit]


@pytest.fixture
def client():
    app.dependency_overrides[get_data_service] = lambda: _FakeData()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_fdr_covers_requested_gameweeks(client):
    d = client.get("/api/teams/fdr?gameweeks=6").json()
    assert d["gameweeks"] == [10, 11, 12, 13, 14, 15]
    for team in d["fdr"]:
        assert [f["gw"] for f in team["fixtures"]] == [10, 11, 12, 13, 14, 15]


def test_cache_respects_per_key_ttl():
    cache = CacheManager(ttl=300)
    with patch("app.utils.cache.time.monotonic", return_value=1000.0):
        cache.set("short", "a", ttl=10)
        cache.set("default", "b")
    with patch("app.utils.cache.time.monotonic", return_value=1011.0):
        assert cache.get("short") is None
        assert cache.get("default") == "b"
    with patch("app.utils.cache.time.monotonic", return_value=1301.0):
        assert cache.get("default") is None

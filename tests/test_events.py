from fastapi.testclient import TestClient

from app.api import events
from app.auth.firebase_auth import get_current_user
from app.main import app


def test_known_events_accepted_unknown_ignored(monkeypatch):
    written = []
    monkeypatch.setattr(events, "_increment", lambda name, day: written.append(name))
    c = TestClient(app)
    assert c.post("/api/events", json={"name": "visit"}).json() == {"ok": True}
    assert c.post("/api/events", json={"name": "<script>"}).json() == {"ok": False}
    assert c.post("/api/events", content=b"not json").json() == {"ok": False}
    assert written == ["visit"]


def test_rate_limited_per_ip(monkeypatch):
    monkeypatch.setattr(events, "_increment", lambda *a: None)
    events._recent.clear()
    c = TestClient(app)
    oks = [c.post("/api/events", json={"name": "visit"}, headers={"x-forwarded-for": "9.9.9.9"}).json()["ok"]
           for _ in range(events._RATE_MAX + 5)]
    assert oks.count(True) == events._RATE_MAX


def test_funnel_is_admin_only(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com")
    app.dependency_overrides[get_current_user] = lambda: {"uid": "u", "email": "fan@example.com", "plan": "free"}
    try:
        assert TestClient(app).get("/api/admin/funnel").status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_summarise_funnel_conversion():
    out = events.summarise_funnel({
        "2026-10-16": {"visit": 100, "team_import": 30},
        "2026-10-17": {"visit": 100, "team_import": 10, "sign_in": 5},
    })
    steps = {s["step"]: s for s in out["funnel"]}
    assert steps["visit"]["count"] == 200
    assert steps["team_import"]["from_previous"] == 0.2
    assert steps["briefing_view"]["count"] == 0
    assert steps["sign_in"]["from_previous"] is None   # previous step had zero


def test_global_cap_bounds_spoofed_forwarded_for(monkeypatch):
    monkeypatch.setattr(events, "_increment", lambda *a: None)
    monkeypatch.setattr(events, "_GLOBAL_MAX", 50)
    events._recent.clear()
    events._global.clear()
    c = TestClient(app)
    oks = [c.post("/api/events", json={"name": "visit"}, headers={"x-forwarded-for": f"10.0.0.{i}"}).json()["ok"]
           for i in range(80)]
    assert oks.count(True) == 50
    events._global.clear()

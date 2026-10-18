from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.calendar import build_ics
from app.main import app
from app.services.data_service import get_data_service

EVENTS = [
    {"id": 7, "name": "Gameweek 7", "deadline_time": "2026-10-03T10:00:00Z", "finished": True},
    {"id": 8, "name": "Gameweek 8", "deadline_time": "2026-10-18T10:00:00Z", "finished": False},
    {"id": 9, "name": "Gameweek 9", "deadline_time": "2026-10-25T17:30:00Z", "finished": False},
]


def test_ics_has_upcoming_deadlines_with_reminders():
    ics = build_ics(EVENTS, team=123, now=datetime(2026, 10, 17, tzinfo=timezone.utc))
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert ics.count("BEGIN:VEVENT") == 2                 # finished GW7 skipped
    assert "DTSTART:20261025T173000Z" in ics
    assert ics.count("BEGIN:VALARM") == 4
    assert "URL:https://epl-prediction-app.web.app/?team=123" in ics


def test_calendar_endpoint():
    class Fake:
        async def get_bootstrap_data(self):
            return {"events": EVENTS}

    app.dependency_overrides[get_data_service] = lambda: Fake()
    try:
        r = TestClient(app).get("/api/calendar/deadlines.ics?team=5")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "Gameweek 9 deadline" in r.text


def test_ics_text_escaping():
    from app.api.calendar import _escape

    assert _escape("a;b,c\\d\ne") == "a\;b\\,c\\\\d\\ne"

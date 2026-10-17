"""Plan gating, launch grace period, briefing meter and the Gemini cost guard."""

import asyncio
import time

import pytest
from fastapi import HTTPException

from app.api import fpl_team
from app.auth import firebase_auth
from app.services import gemini_service

ANON = {"uid": None, "email": None, "plan": "free"}
FREE = {"uid": "u-free", "email": "f@x.z", "plan": "free"}
PRO = {"uid": "u-pro", "email": "p@x.z", "plan": "pro"}
FOUNDER = {"uid": "u-f", "email": "o@x.z", "plan": "founder"}


@pytest.fixture
def grace_over(monkeypatch):
    monkeypatch.setattr(firebase_auth, "_LAUNCH_FREE_UNTIL_RAW", "2000-01-01")


@pytest.fixture
def grace_on(monkeypatch):
    monkeypatch.setattr(firebase_auth, "_LAUNCH_FREE_UNTIL_RAW", "2099-01-01")


def test_everyone_is_pro_during_grace(grace_on):
    for user in (ANON, FREE, PRO, FOUNDER):
        assert firebase_auth.get_effective_plan(user) in ("pro", "founder")
        firebase_auth.require_pro(user)  # must not raise


def test_paywall_after_grace(grace_over):
    for user in (ANON, FREE):
        with pytest.raises(HTTPException) as e:
            firebase_auth.require_pro(user)
        assert e.value.status_code == 403
    firebase_auth.require_pro(PRO)
    firebase_auth.require_pro(FOUNDER)


def test_invalid_grace_date_fails_open(monkeypatch):
    monkeypatch.setattr(firebase_auth, "_LAUNCH_FREE_UNTIL_RAW", "not-a-date")
    assert firebase_auth._in_grace_period()


# ── Briefing meter ────────────────────────────────────────────────────────────

class _Doc:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def get(self):
        data = self.store.get(self.key)
        return type("Snap", (), {"exists": data is not None, "to_dict": lambda _self: dict(data or {})})()

    def set(self, data, merge=False):
        self.store[self.key] = {**(self.store.get(self.key) or {}), **data} if merge else data


class _FakeDb:
    def __init__(self):
        self.store = {}

    def collection(self, _name):
        return type("Col", (), {"document": lambda _self, key: _Doc(self.store, key)})()


@pytest.fixture
def fake_db(monkeypatch):
    db = _FakeDb()
    monkeypatch.setattr(fpl_team, "get_db", lambda: db)
    monkeypatch.setattr(fpl_team, "_FREE_BRIEFINGS_PER_GW", 1)
    return db


def test_meter_free_user_gets_one_per_gameweek(grace_over, fake_db):
    assert fpl_team._briefing_meter_check_and_increment(FREE, 7) == (True, 1)
    assert fpl_team._briefing_meter_check_and_increment(FREE, 7) == (False, 1)
    assert fpl_team._briefing_meter_check_and_increment(FREE, 8) == (True, 1)  # resets next GW


def test_meter_anon_blocked_after_grace(grace_over, fake_db):
    assert fpl_team._briefing_meter_check_and_increment(ANON, 7) == (False, 0)


def test_meter_unlimited_for_paid_and_during_grace(grace_over, fake_db):
    for _ in range(5):
        assert fpl_team._briefing_meter_check_and_increment(PRO, 7)[0]
        assert fpl_team._briefing_meter_check_and_increment(FOUNDER, 7)[0]
    assert fake_db.store == {}  # paid users never touch the counter


def test_meter_fails_open_without_firestore(grace_over, monkeypatch):
    monkeypatch.setattr(fpl_team, "get_db", lambda: None)
    assert fpl_team._briefing_meter_check_and_increment(FREE, 7)[0]


# ── Gemini guard ──────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_gemini_window(monkeypatch):
    monkeypatch.setattr(gemini_service, "_call_times", gemini_service.deque())
    monkeypatch.setattr(gemini_service, "_MAX_CALLS_PER_MINUTE", 3)


def test_gemini_cap_per_minute(fresh_gemini_window):
    t0 = 1000.0
    assert all(gemini_service._take_call_slot(t0 + i) for i in range(3))
    assert not gemini_service._take_call_slot(t0 + 10)
    assert gemini_service._take_call_slot(t0 + 61)  # oldest call aged out


def test_gemini_timeout_returns_empty_reasons(fresh_gemini_window, monkeypatch):
    monkeypatch.setattr(gemini_service, "_client", lambda: object())
    monkeypatch.setattr(gemini_service, "_TIMEOUT_S", 0.05)
    monkeypatch.setattr(gemini_service, "generate_briefing_reasons", lambda **_: time.sleep(1) or {"summary": "late"})
    out = asyncio.run(gemini_service.generate_briefing_reasons_async(team_name="x", alerts=[], captain=None, transfer=None))
    assert out["summary"] == ""


def test_gemini_disabled_without_key(monkeypatch):
    monkeypatch.setattr(gemini_service, "_client", lambda: None)
    out = asyncio.run(gemini_service.generate_briefing_reasons_async(team_name="x", alerts=[], captain=None, transfer=None))
    assert out == {"summary": "", "captain_reason": "", "transfer_reason": "", "alert_reasons": {}}


def test_users_me_reports_effective_plan_for_anonymous(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    monkeypatch.setattr(firebase_auth, "_LAUNCH_FREE_UNTIL_RAW", "2099-01-01")
    d = client.get("/api/users/me").json()
    assert d["plan"] == "free" and d["effective_plan"] == "pro"
    monkeypatch.setattr(firebase_auth, "_LAUNCH_FREE_UNTIL_RAW", "2000-01-01")
    assert client.get("/api/users/me").json()["effective_plan"] == "free"

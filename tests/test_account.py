"""DELETE /api/users/me — account erasure."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import payments, users
from app.auth.firebase_auth import get_current_user
from app.main import app

USER = {"uid": "u-1", "email": "fan@example.com", "plan": "pro"}


class _Doc:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def get(self):
        data = self.store.get(self.key)
        return type("Snap", (), {"exists": data is not None, "to_dict": lambda _s: dict(data or {})})()

    def delete(self):
        self.store.pop(self.key, None)


class _Db:
    def __init__(self, store):
        self.store = store

    def collection(self, _name):
        return type("Col", (), {"document": lambda _s, key: _Doc(self.store, key)})()


@pytest.fixture
def setup(monkeypatch):
    store = {}
    monkeypatch.setattr(users, "get_db", lambda: _Db(store))
    deleted_auth = []
    import firebase_admin.auth
    monkeypatch.setattr(firebase_admin.auth, "delete_user", deleted_auth.append)
    cancel = AsyncMock()
    monkeypatch.setattr(payments, "cancel_payfast_subscription", cancel)
    app.dependency_overrides[get_current_user] = lambda: USER
    yield TestClient(app), store, deleted_auth, cancel
    app.dependency_overrides.clear()


def test_requires_sign_in(setup):
    client, *_ = setup
    app.dependency_overrides[get_current_user] = lambda: {"uid": None, "email": None, "plan": "free"}
    assert client.delete("/api/users/me").status_code == 401


def test_deletes_record_and_auth_user(setup):
    client, store, deleted_auth, cancel = setup
    store["u-1"] = {"plan": "founder"}
    r = client.delete("/api/users/me")
    assert r.status_code == 200 and r.json() == {"deleted": True}
    assert "u-1" not in store
    assert deleted_auth == ["u-1"]
    cancel.assert_not_called()


def test_cancels_live_subscription_first(setup):
    client, store, _, cancel = setup
    store["u-1"] = {"plan": "pro", "payfast_token": "tok", "subscription_cancelled": False}
    assert client.delete("/api/users/me").status_code == 200
    cancel.assert_awaited_once_with("tok")


def test_keeps_account_if_payfast_cancel_fails(setup):
    client, store, deleted_auth, cancel = setup
    store["u-1"] = {"plan": "pro", "payfast_token": "tok"}
    cancel.side_effect = HTTPException(status_code=502, detail="PayFast down")
    assert client.delete("/api/users/me").status_code == 502
    assert "u-1" in store and deleted_auth == []

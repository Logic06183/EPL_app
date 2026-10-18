"""Users API: desktop custom-token minting."""

from fastapi.testclient import TestClient

from app.main import app
from app.auth.firebase_auth import get_current_user


def test_desktop_token_requires_sign_in():
    app.dependency_overrides[get_current_user] = lambda: {"uid": None, "email": None, "plan": "free"}
    try:
        r = TestClient(app).post("/api/users/desktop-token")
        assert r.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_desktop_token_mints_for_uid(monkeypatch):
    import firebase_admin.auth as fb_auth
    seen = {}

    def fake_create(uid):
        seen["uid"] = uid
        return b"custom.jwt.token"

    monkeypatch.setattr(fb_auth, "create_custom_token", fake_create)
    app.dependency_overrides[get_current_user] = lambda: {"uid": "u123", "email": "x@y.com", "plan": "free"}
    try:
        r = TestClient(app).post("/api/users/desktop-token")
        assert r.status_code == 200
        assert r.json() == {"custom_token": "custom.jwt.token"}
        assert seen["uid"] == "u123"
    finally:
        app.dependency_overrides.clear()


def test_desktop_token_503_when_admin_sdk_fails(monkeypatch):
    import firebase_admin.auth as fb_auth

    def boom(uid):
        raise RuntimeError("no signer")

    monkeypatch.setattr(fb_auth, "create_custom_token", boom)
    app.dependency_overrides[get_current_user] = lambda: {"uid": "u123", "email": "x@y.com", "plan": "free"}
    try:
        r = TestClient(app).post("/api/users/desktop-token")
        assert r.status_code == 503
    finally:
        app.dependency_overrides.clear()

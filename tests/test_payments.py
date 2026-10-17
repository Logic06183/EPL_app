"""Security tests for the PayFast checkout + ITN webhook."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api import payments
from app.auth.firebase_auth import get_current_user
from app.main import app

SIGNED_IN = {"uid": "user-123", "email": "fan@example.com", "plan": "free"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(payments, "PAYFAST_MERCHANT_ID", "10000100")
    monkeypatch.setattr(payments, "PAYFAST_MERCHANT_KEY", "key")
    monkeypatch.setattr(payments, "PAYFAST_PASSPHRASE", "secret-pass")
    monkeypatch.setattr(payments, "PAYFAST_VALIDATE_ITN", False)
    yield TestClient(app)
    app.dependency_overrides.clear()


def _itn(**overrides):
    data = {
        "m_payment_id": "",
        "pf_payment_id": "12345",
        "payment_status": "COMPLETE",
        "item_name": "FPL AI Pro",
        "amount_gross": "199.00",
        "custom_str1": "pro",
        "custom_str2": "fan@example.com",
        "custom_str3": "user-123",
        "merchant_id": "10000100",
        "token": "sub-token",
    }
    data.update(overrides)
    data["signature"] = payments._payfast_signature(data, "secret-pass")
    return data


def test_itn_rejected_when_passphrase_not_configured(client, monkeypatch):
    monkeypatch.setattr(payments, "PAYFAST_PASSPHRASE", "")
    upgrade = AsyncMock()
    monkeypatch.setattr(payments, "_upgrade_user", upgrade)
    r = client.post("/api/payments/webhook", data={"payment_status": "COMPLETE", "custom_str2": "x@y.z"})
    assert r.status_code == 503
    upgrade.assert_not_called()


def test_itn_with_forged_signature_is_rejected(client, monkeypatch):
    upgrade = AsyncMock()
    monkeypatch.setattr(payments, "_upgrade_user", upgrade)
    data = _itn()
    data["signature"] = "0" * 32
    r = client.post("/api/payments/webhook", data=data)
    assert r.status_code == 400
    upgrade.assert_not_called()


def test_itn_with_wrong_amount_is_rejected(client, monkeypatch):
    upgrade = AsyncMock()
    monkeypatch.setattr(payments, "_upgrade_user", upgrade)
    r = client.post("/api/payments/webhook", data=_itn(amount_gross="1.00"))
    assert r.status_code == 400
    upgrade.assert_not_called()


def test_itn_with_wrong_merchant_is_rejected(client, monkeypatch):
    upgrade = AsyncMock()
    monkeypatch.setattr(payments, "_upgrade_user", upgrade)
    r = client.post("/api/payments/webhook", data=_itn(merchant_id="999"))
    assert r.status_code == 400
    upgrade.assert_not_called()


def test_itn_not_confirmed_by_payfast_is_rejected(client, monkeypatch):
    monkeypatch.setattr(payments, "PAYFAST_VALIDATE_ITN", True)
    monkeypatch.setattr(payments, "_confirm_itn_with_payfast", AsyncMock(return_value=False))
    upgrade = AsyncMock()
    monkeypatch.setattr(payments, "_upgrade_user", upgrade)
    r = client.post("/api/payments/webhook", data=_itn())
    assert r.status_code == 400
    upgrade.assert_not_called()


def test_valid_itn_upgrades_user_by_uid(client, monkeypatch):
    upgrade = AsyncMock()
    monkeypatch.setattr(payments, "_upgrade_user", upgrade)
    r = client.post("/api/payments/webhook", data=_itn())
    assert r.status_code == 200
    upgrade.assert_awaited_once()
    assert upgrade.await_args.kwargs["uid"] == "user-123"
    assert upgrade.await_args.kwargs["plan"] == "pro"


def test_initialize_requires_sign_in(client):
    r = client.post("/api/payments/initialize", json={"plan_id": "pro", "return_url": "https://epl-prediction-app.web.app/"})
    assert r.status_code == 401


def test_initialize_rejects_foreign_return_url(client):
    app.dependency_overrides[get_current_user] = lambda: SIGNED_IN
    r = client.post("/api/payments/initialize", json={"plan_id": "pro", "return_url": "https://evil.example/"})
    assert r.status_code == 400


def test_initialize_uses_signed_in_identity(client):
    app.dependency_overrides[get_current_user] = lambda: SIGNED_IN
    r = client.post(
        "/api/payments/initialize",
        json={"plan_id": "pro", "email": "someone-else@example.com", "return_url": "https://epl-prediction-app.web.app/?upgraded=1"},
    )
    assert r.status_code == 200
    url = r.json()["authorization_url"]
    assert "custom_str3=user-123" in url
    assert "fan%40example.com" in url
    assert "someone-else" not in url


def test_manual_upgrade_endpoint_is_gone(client):
    app.dependency_overrides[get_current_user] = lambda: SIGNED_IN
    r = client.post("/api/users/upgrade-manual", json={"plan": "pro"})
    assert r.status_code in (404, 405)

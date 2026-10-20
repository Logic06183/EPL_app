import hashlib
from urllib.parse import parse_qs, quote_plus, urlparse

import pytest
from fastapi.testclient import TestClient

from app.api import payments
from app.auth.firebase_auth import get_current_user
from app.main import app

SIGNED_IN = {"uid": "uid-123", "email": "fan@example.com", "plan": "free"}
ANON = {"uid": None, "email": None, "plan": "free"}


class FakeDoc:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def set(self, data, merge=False):
        self.store.setdefault(self.key, {}).update(data)

    def get(self):
        return self

    @property
    def exists(self):
        return self.key in self.store

    def to_dict(self):
        return dict(self.store.get(self.key, {}))


class FakeDB:
    def __init__(self):
        self.docs = {}

    def collection(self, _name):
        return self

    def document(self, key):
        return FakeDoc(self.docs, key)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(payments, "PAYFAST_MERCHANT_ID", "10000100")
    monkeypatch.setattr(payments, "PAYFAST_MERCHANT_KEY", "key")
    monkeypatch.setattr(payments, "PAYFAST_PASSPHRASE", "secret phrase")
    db = FakeDB()
    monkeypatch.setattr(payments, "get_db", lambda: db)

    async def confirm(_data):
        return True

    monkeypatch.setattr(payments, "_confirm_itn_with_payfast", confirm)
    c = TestClient(app)
    c.db = db
    yield c
    app.dependency_overrides.clear()


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _signed_itn(**overrides):
    data = {
        "m_payment_id": "uid-123-1",
        "pf_payment_id": "999",
        "payment_status": "COMPLETE",
        "item_name": "FPL AI Pro",
        "item_description": "",
        "amount_gross": "79.00",
        "custom_str1": "pro",
        "custom_str2": "uid-123",
        "custom_str3": "",
        "merchant_id": "10000100",
        "token": "tok",
    }
    data.update(overrides)
    s = "&".join(f"{k}={quote_plus(v)}" for k, v in data.items())
    s += "&passphrase=" + quote_plus("secret phrase")
    data["signature"] = hashlib.md5(s.encode()).hexdigest()
    return data


def test_manual_upgrade_endpoint_is_gone(client):
    _as(SIGNED_IN)
    r = client.post("/api/users/upgrade-manual", json={"plan": "founder"})
    assert r.status_code in (404, 405)


def test_initialize_requires_sign_in(client):
    _as(ANON)
    r = client.post("/api/payments/initialize",
                    json={"plan_id": "pro", "return_url": "https://epl-prediction-app.web.app/"})
    assert r.status_code == 401


def test_initialize_uses_token_identity_and_safe_return_url(client):
    _as(SIGNED_IN)
    r = client.post("/api/payments/initialize", json={
        "plan_id": "pro", "email": "victim@example.com",
        "return_url": "https://evil.example/phish",
    })
    assert r.status_code == 200
    q = parse_qs(urlparse(r.json()["authorization_url"]).query)
    assert q["custom_str2"] == ["uid-123"]
    assert q["email_address"] == ["fan@example.com"]
    assert q["return_url"][0].startswith("https://epl-prediction-app.web.app/")
    assert "signature" in q


def test_initialize_field_order_puts_custom_before_subscription(client):
    _as(SIGNED_IN)
    r = client.post("/api/payments/initialize",
                    json={"plan_id": "pro", "return_url": "https://epl-prediction-app.web.app/"})
    keys = list(parse_qs(urlparse(r.json()["authorization_url"]).query).keys())
    assert keys.index("custom_str2") < keys.index("subscription_type")


def test_valid_itn_upgrades_user_by_uid(client):
    r = client.post("/api/payments/webhook", data=_signed_itn())
    assert r.status_code == 200, r.text
    assert client.db.docs["uid-123"]["plan"] == "pro"
    assert client.db.docs["uid-123"]["payfast_token"] == "tok"


def test_itn_with_bad_signature_is_rejected(client):
    data = _signed_itn()
    data["signature"] = "0" * 32
    assert client.post("/api/payments/webhook", data=data).status_code == 400
    assert client.db.docs == {}


def test_itn_cannot_grant_founder(client):
    r = client.post("/api/payments/webhook", data=_signed_itn(custom_str1="founder"))
    assert r.status_code == 400
    assert client.db.docs == {}


def test_itn_amount_must_match_plan(client):
    r = client.post("/api/payments/webhook", data=_signed_itn(amount_gross="1.00"))
    assert r.status_code == 400
    assert client.db.docs == {}


def test_itn_rejected_when_payfast_does_not_confirm(client, monkeypatch):
    async def deny(_data):
        return False

    monkeypatch.setattr(payments, "_confirm_itn_with_payfast", deny)
    assert client.post("/api/payments/webhook", data=_signed_itn()).status_code == 400


def test_itn_refused_without_passphrase(client, monkeypatch):
    monkeypatch.setattr(payments, "PAYFAST_PASSPHRASE", "")
    assert client.post("/api/payments/webhook", data=_signed_itn()).status_code == 503


def test_cancelled_itn_marks_subscription(client):
    r = client.post("/api/payments/webhook", data=_signed_itn(payment_status="CANCELLED"))
    assert r.status_code == 200
    assert client.db.docs["uid-123"]["subscription_cancelled"] is True


def test_season_pass_is_once_off(client):
    _as(SIGNED_IN)
    r = client.post("/api/payments/initialize",
                    json={"plan_id": "season", "return_url": "https://epl-prediction-app.web.app/"})
    q = parse_qs(urlparse(r.json()["authorization_url"]).query)
    assert q["amount"] == ["449.00"]
    assert "subscription_type" not in q


def test_season_pass_itn_grants_pro_until_end_of_may(client):
    r = client.post("/api/payments/webhook",
                    data=_signed_itn(custom_str1="season", amount_gross="449.00", token=""))
    assert r.status_code == 200, r.text
    doc = client.db.docs["uid-123"]
    assert doc["plan"] == "pro"
    assert doc["plan_expires_at"][5:10] == "05-31"


def test_founder_is_charged_half_price(client):
    client.db.docs["uid-123"] = {"founder_granted_at": "2026-10-20T00:00:00"}
    _as(SIGNED_IN)
    r = client.post("/api/payments/initialize",
                    json={"plan_id": "season", "return_url": "https://epl-prediction-app.web.app/"})
    q = parse_qs(urlparse(r.json()["authorization_url"]).query)
    assert q["amount"] == ["225.00"] and q["custom_str1"] == ["season_founder"]


def test_founder_price_refused_for_non_founder(client):
    _as(SIGNED_IN)
    r = client.post("/api/payments/initialize",
                    json={"plan_id": "pro_founder", "return_url": "https://epl-prediction-app.web.app/"})
    assert r.status_code == 403


def test_founder_pays_after_paywall(monkeypatch):
    from app.auth import firebase_auth as fa
    monkeypatch.setattr(fa, "_in_grace_period", lambda now=None: False)
    assert fa.get_effective_plan({"plan": "founder"}) == "free"
    assert fa.get_effective_plan({"plan": "pro"}) == "pro"
    monkeypatch.setattr(fa, "_in_grace_period", lambda now=None: True)
    assert fa.get_effective_plan({"plan": "founder"}) == "founder"
    assert fa.get_effective_plan({"plan": "free"}) == "pro"

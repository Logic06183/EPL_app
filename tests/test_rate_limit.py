from fastapi.testclient import TestClient

from app.main import app
from app.utils.rate_limit import RateLimiter


def test_sliding_window():
    rl = RateLimiter()
    assert all(rl.check("1.2.3.4", "b", 3, now=100 + i) == 0 for i in range(3))
    assert rl.check("1.2.3.4", "b", 3, now=110) > 0
    assert rl.check("5.6.7.8", "b", 3, now=110) == 0     # other clients unaffected
    assert rl.check("1.2.3.4", "b", 3, now=161) == 0     # first hit aged out


def test_expensive_endpoint_returns_429_with_retry_after():
    client = TestClient(app)
    headers = {"X-Forwarded-For": "9.9.9.9"}
    codes = [client.get("/api/payments/plans", headers=headers).status_code for _ in range(21)]
    assert codes[:20] == [200] * 20
    assert codes[20] == 429
    r = client.get("/api/payments/plans", headers=headers)
    assert int(r.headers["Retry-After"]) >= 1
    # A different client is still served; health probes are never limited
    assert client.get("/api/payments/plans", headers={"X-Forwarded-For": "8.8.8.8"}).status_code == 200
    assert all(client.get("/ping", headers=headers).status_code == 200 for _ in range(300))

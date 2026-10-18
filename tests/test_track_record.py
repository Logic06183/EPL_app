from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services import track_record as tr


class Snap:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data)


class Doc:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def get(self):
        return Snap(self.store.get(self.key))

    def set(self, data):
        self.store[self.key] = data


class Coll:
    def __init__(self, store):
        self.store = store

    def document(self, key):
        return Doc(self.store, key)

    def where(self, field, _op, value):
        matches = [Snap(v) for v in self.store.values() if v.get(field) == value]
        return type("Q", (), {"stream": lambda self: iter(matches)})()


class FakeDB:
    def __init__(self):
        self.data = {}

    def collection(self, name):
        return Coll(self.data.setdefault(name, {}))


def _future(hours):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def _snapshot(deadline):
    xp = {1: 6.0, 2: 4.0, 3: 2.0, 4: 1.0}
    baseline = {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}
    names = {1: "Haaland", 2: "Saka", 3: "Gabriel", 4: "Pickford"}
    fpl = {1: 5.0, 2: 5.5, 3: 2.5, 4: 1.0}   # FPL's own ep_next, captured pre-deadline
    return tr.build_snapshot(9, xp, baseline, [1, 2, 3, 4], names, deadline, fpl=fpl)


def test_season_label():
    assert tr.season_label([{"deadline_time": "2026-08-14T17:30:00Z"}]) == "2026-27"


def test_score_snapshot_compares_model_with_baseline():
    result = tr.score_snapshot(_snapshot(_future(1)), {1: 13.0, 2: 6.0, 3: 2.0, 4: 1.0})
    assert result["model"]["spearman"] == 1.0
    assert result["season_avg"]["spearman"] == -1.0
    assert result["model"]["captain_pts"] == 13.0
    assert result["captain"] == {"id": 1, "name": "Haaland", "xp": 6.0, "actual": 13.0}
    assert result["model"]["mae"] < result["season_avg"]["mae"]


def test_snapshot_not_overwritten_after_deadline():
    db = FakeDB()
    tr.save_snapshot(db, "2026-27", _snapshot(_future(1)))
    assert "2026-27-gw9" in db.data[tr.SNAPSHOTS]
    late = _snapshot(_future(-1))
    late["xp"]["1"] = 99.0
    tr.save_snapshot(db, "2026-27", late)
    assert db.data[tr.SNAPSHOTS]["2026-27-gw9"]["xp"]["1"] == 6.0


def test_score_pending_writes_each_gameweek_once():
    db = FakeDB()
    tr.save_snapshot(db, "2026-27", _snapshot(_future(1)))
    actual = {9: {1: 13.0, 2: 6.0, 3: 2.0, 4: 1.0}}
    assert tr.score_pending(db, "2026-27", [8, 9], actual) == 1
    assert tr.score_pending(db, "2026-27", [8, 9], actual) == 0
    results = tr.load_results(db, "2026-27")
    assert [r["gw"] for r in results] == [9]
    assert tr.summarise(results)["model"]["captain_pts"] == 13.0


def test_track_record_endpoint_serves_backtest():
    r = TestClient(app).get("/api/models/track-record")
    assert r.status_code == 200
    body = r.json()
    assert set(body["backtest"]["seasons"]) == {"2024-25", "2025-26"}
    assert "live" in body and "method" in body


def test_scheduled_refresh_requires_secret(monkeypatch):
    c = TestClient(app)
    monkeypatch.delenv("CRON_SECRET", raising=False)
    assert c.post("/api/predictions/refresh", headers={"X-Cron-Secret": "x"}).status_code == 403
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    assert c.post("/api/predictions/refresh", headers={"X-Cron-Secret": "wrong"}).status_code == 403
    assert c.post("/api/predictions/refresh").status_code == 403


def test_score_snapshot_scores_fpl_benchmark_when_present():
    snap = _snapshot(_future(1))
    actual = {1: 10.0, 2: 6.0, 3: 2.0, 4: 1.0}
    res = tr.score_snapshot(snap, actual)
    assert res["fpl"]["captain_pts"] == 6.0          # FPL ranked Saka first
    assert res["model"]["captain_pts"] == 10.0       # the model ranked Haaland first
    summary = tr.summarise([res, res])
    assert summary["fpl"]["gameweeks"] == 2 and summary["fpl"]["captain_pts"] == 6.0
    # Snapshots taken before the benchmark existed still summarise
    old = {k: v for k, v in res.items() if k != "fpl"}
    assert "fpl" not in tr.summarise([old])

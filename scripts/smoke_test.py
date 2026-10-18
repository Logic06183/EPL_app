"""
Post-deploy smoke test against a live site.

    python scripts/smoke_test.py https://epl-prediction-app.web.app

Checks the parts that can't be exercised offline: the xP model actually
built from live FPL data (not the form-only fallback), predictions look
sane, the optimiser solves, and the calendar and track record are served.
Exits non-zero on the first failure.
"""

import sys
import time

import httpx


def main(base: str) -> int:
    base = base.rstrip("/")
    client = httpx.Client(timeout=90, follow_redirects=True)
    failures = []

    def check(name, ok, detail=""):
        print(f"{'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
        if not ok:
            failures.append(name)

    r = client.get(f"{base}/health")
    check("health", r.status_code == 200, str(r.status_code))

    # The model builds on startup; give a cold instance a moment
    info = {}
    for _ in range(6):
        info = client.get(f"{base}/api/models/info").json()
        if info.get("models", {}).get("xp", {}).get("trained"):
            break
        time.sleep(10)
    xp = info.get("models", {}).get("xp", {})
    check("xP model built from live data", bool(xp.get("trained")), f"gameweek={xp.get('gameweek')}")

    preds = client.get(f"{base}/api/players/predictions", params={"top_n": 20, "model_type": "xp"}).json()
    rows = preds.get("predictions", [])
    top = [p.get("predicted_points") or 0 for p in rows]
    check("predictions returned", len(rows) == 20, f"{len(rows)} rows")
    check("top predictions plausible (2-15 pts)", bool(top) and 2 <= top[0] <= 15, f"top={top[:3]}")
    check("next-3 horizon present", bool(rows) and all(len(p.get("predicted_next_3") or []) == 3 for p in rows[:5]))

    opt = client.post(f"{base}/api/teams/optimize", json={"budget": 100})
    body = opt.json() if opt.status_code == 200 else {}
    check("optimiser solves", opt.status_code == 200 and len(body.get("squad", [])) == 15,
          f"{opt.status_code}, cost={body.get('total_cost')}")

    tr = client.get(f"{base}/api/models/track-record").json()
    check("track record served", set(tr.get("backtest", {}).get("seasons", {})) >= {"2024-25", "2025-26"})

    ics = client.get(f"{base}/api/calendar/deadlines.ics")
    check("deadline calendar", ics.status_code == 200 and "BEGIN:VEVENT" in ics.text)

    print(f"\n{len(failures)} failure(s)" if failures else "\nAll checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "https://epl-prediction-app.web.app"))

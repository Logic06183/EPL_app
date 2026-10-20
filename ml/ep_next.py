"""
FPL's own pre-deadline expected points (ep_next), per player and gameweek.

The historical xP column in vaastav's data was recorded after kick-off (see
train.xp_leak), so it is not a fair benchmark. Randdalf/fplcache keeps a copy
of bootstrap-static every 6 hours; for each deadline we take the last copy
before it and read ep_next for the gameweek that is next.

    python -m ml.ep_next --data data --season 2024-25
"""

from __future__ import annotations

import argparse
import json
import lzma
import subprocess
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

RAW = "https://raw.githubusercontent.com/Randdalf/fplcache/main/cache"


def _list(path: str) -> list[str]:
    """Names in a cache directory (via the GitHub API, authenticated by gh)."""
    out = subprocess.run(["gh", "api", f"repos/Randdalf/fplcache/contents/cache/{path}", "--jq", ".[].name"],
                         capture_output=True, text=True)
    return out.stdout.split() if out.returncode == 0 else []


def _fetch(path: str) -> dict:
    with urllib.request.urlopen(f"{RAW}/{path}", timeout=60) as r:
        return json.loads(lzma.decompress(r.read()))


def _captures_before(deadline: datetime, days: int = 3) -> list[tuple[datetime, str]]:
    """Cache files in the `days` before a deadline, newest first."""
    found = []
    for back in range(days + 1):
        d = deadline - timedelta(days=back)
        for name in _list(f"{d.year}/{d.month}/{d.day}"):
            hh, mm = name.split(".")[0].split(":") if ":" in name else (name[:2], name[2:4])
            t = datetime(d.year, d.month, d.day, int(hh), int(mm), tzinfo=timezone.utc)
            if t < deadline:
                found.append((t, f"{d.year}/{d.month}/{d.day}/{name}"))
    return sorted(found, reverse=True)


def season_deadlines(season: str) -> list[tuple[int, datetime]]:
    """All (gw, deadline) of a season, read from a mid-season capture."""
    start = int(season[:4])
    for month, year in ((12, start), (1, start + 1), (11, start)):
        for day in (15, 16, 14, 17):
            names = _list(f"{year}/{month}/{day}")
            if names:
                data = _fetch(f"{year}/{month}/{day}/{names[0]}")
                return [(e["id"], datetime.fromisoformat(e["deadline_time"].replace("Z", "+00:00")))
                        for e in data["events"]]
    raise RuntimeError(f"no capture found for {season}")


def collect(season: str) -> pd.DataFrame:
    rows = []
    for gw, deadline in season_deadlines(season):
        for t, path in _captures_before(deadline):
            data = _fetch(path)
            nxt = next((e for e in data["events"] if e.get("is_next")), None)
            if nxt is None or nxt["id"] != gw:
                continue
            rows += [{"gw": gw, "element": e["id"], "ep_next": float(e.get("ep_next") or 0),
                      "hours_before": round((deadline - t).total_seconds() / 3600, 1)}
                     for e in data["elements"]]
            print(f"{season} GW{gw}: {path} ({rows[-1]['hours_before']}h before)", flush=True)
            break
        else:
            print(f"{season} GW{gw}: no pre-deadline capture", flush=True)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--season", required=True)
    args = ap.parse_args()
    df = collect(args.season)
    out = args.data / f"ep_next_{args.season}.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out}: {df['gw'].nunique() if len(df) else 0} gameweeks")


if __name__ == "__main__":
    main()

"""
Live track record: snapshot each gameweek's predictions before the deadline,
score them once the gameweek is finished, and serve the results.

Firestore:
  xp_snapshots/{season}-gw{gw}  predictions as last saved before the deadline
  xp_results/{season}-gw{gw}    scored results (written once)

Scoring matches the backtest in ml/train.py: players averaging 30+ minutes
over their last 6 gameweeks, model vs the season-average baseline.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

SNAPSHOTS = "xp_snapshots"
RESULTS = "xp_results"


def season_label(events: List[Dict[str, Any]]) -> str:
    """'2026-27' from the first gameweek's deadline."""
    first = events[0]["deadline_time"] if events else datetime.now(timezone.utc).isoformat()
    year = int(first[:4])
    return f"{year}-{str(year + 1)[2:]}"


def doc_id(season: str, gw: int) -> str:
    return f"{season}-gw{gw}"


def build_snapshot(
    gw: int, xp: Dict[int, float], baseline: Dict[int, float], pool: List[int],
    names: Dict[int, str], deadline: str,
) -> Dict[str, Any]:
    top = sorted(pool, key=lambda el: xp.get(el, 0.0), reverse=True)[:11]
    return {
        "gw": gw,
        "deadline": deadline,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Firestore map keys must be strings
        "xp": {str(el): round(v, 3) for el, v in xp.items()},
        "baseline": {str(el): round(v, 3) for el, v in baseline.items()},
        "pool": [int(el) for el in pool],
        "top11": [{"id": int(el), "name": names.get(el, ""), "xp": round(xp.get(el, 0.0), 2)} for el in top],
    }


def score_snapshot(snapshot: Dict[str, Any], actual: Dict[int, float]) -> Optional[Dict[str, Any]]:
    """Score a saved snapshot against actual gameweek points."""
    pool = snapshot.get("pool") or []
    if not pool:
        return None
    df = pd.DataFrame({
        "el": pool,
        "model": [snapshot["xp"].get(str(el), 0.0) for el in pool],
        "baseline": [snapshot["baseline"].get(str(el), 0.0) for el in pool],
        "actual": [actual.get(el, 0.0) for el in pool],
    })

    def metrics(col: str) -> Dict[str, float]:
        spearman = df[col].rank().corr(df["actual"].rank())
        return {
            "mae": round(float((df[col] - df["actual"]).abs().mean()), 3),
            "spearman": round(float(spearman), 3) if pd.notna(spearman) else None,
            "captain_pts": float(df.nlargest(1, col)["actual"].mean()),
            "top11_pts": round(float(df.nlargest(11, col)["actual"].mean()), 2),
        }

    captain = (snapshot.get("top11") or [{}])[0]
    return {
        "gw": snapshot["gw"],
        "players_scored": len(df),
        "model": metrics("model"),
        "season_avg": metrics("baseline"),
        "captain": {**captain, "actual": actual.get(captain.get("id"), 0.0)} if captain else None,
        "top11": [{**p, "actual": actual.get(p["id"], 0.0)} for p in snapshot.get("top11", [])],
        "snapshot_saved_at": snapshot.get("saved_at"),
        "scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def save_snapshot(db, season: str, snapshot: Dict[str, Any]) -> None:
    """Overwrite the gameweek's snapshot, but only before its deadline."""
    deadline = datetime.fromisoformat(snapshot["deadline"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) >= deadline:
        return
    db.collection(SNAPSHOTS).document(doc_id(season, snapshot["gw"])).set(snapshot)


def score_pending(db, season: str, finished_gws: List[int], actual_by_gw: Dict[int, Dict[int, float]]) -> int:
    """Score any finished gameweek that has a snapshot but no result yet."""
    written = 0
    for gw in finished_gws:
        rid = doc_id(season, gw)
        if db.collection(RESULTS).document(rid).get().exists:
            continue
        snap = db.collection(SNAPSHOTS).document(rid).get()
        if not snap.exists or gw not in actual_by_gw:
            continue
        result = score_snapshot(snap.to_dict(), actual_by_gw[gw])
        if result:
            db.collection(RESULTS).document(rid).set({**result, "season": season})
            written += 1
    return written


def load_results(db, season: str) -> List[Dict[str, Any]]:
    docs = db.collection(RESULTS).where("season", "==", season).stream()
    return sorted((d.to_dict() for d in docs), key=lambda r: r["gw"])


def summarise(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not results:
        return None
    out: Dict[str, Any] = {"gameweeks": len(results)}
    for who in ("model", "season_avg"):
        out[who] = {
            k: round(sum(r[who][k] for r in results if r[who].get(k) is not None) /
                     max(1, sum(1 for r in results if r[who].get(k) is not None)), 3)
            for k in ("mae", "spearman", "captain_pts", "top11_pts")
        }
    return out


async def live_record(data_service, db) -> Dict[str, Any]:
    """This season's scored gameweeks and their summary (shared by the API routes)."""
    import asyncio

    bootstrap = await data_service.get_bootstrap_data()
    season = season_label(bootstrap.get("events", []))
    results = await asyncio.to_thread(load_results, db, season)
    return {"season": season, "gameweeks": results, "summary": summarise(results)}

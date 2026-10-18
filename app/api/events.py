"""
Funnel analytics without third-party trackers: the frontend posts anonymous
event names, the backend keeps daily counts in Firestore
(analytics_daily/{YYYY-MM-DD}). No user ids, no cookies, no IP storage.

GET /api/admin/funnel is limited to emails listed in ADMIN_EMAILS.
"""

import logging
import os
import time
import asyncio
from collections import OrderedDict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from ..auth.firebase_auth import get_current_user, get_db

logger = logging.getLogger(__name__)
router = APIRouter()
admin_router = APIRouter()

COLLECTION = "analytics_daily"

# Ordered: the funnel reads top to bottom
FUNNEL = [
    "visit",
    "team_import",
    "briefing_view",
    "sign_in",
    "paywall_view",
    "upgrade_click",
    "checkout_start",
    "checkout_return",
]
OTHER = {
    "plan_view", "optimise", "track_record_view", "share", "share_visit",
    "calendar_subscribe", "checkout_cancel", "league_view", "hero_import",
}
ALLOWED = set(FUNNEL) | OTHER

# Per-instance rate limits so a script can't inflate counts cheaply. The
# per-client key comes from X-Forwarded-For, which a client can spoof, so a
# global cap per instance bounds the damage either way.
_RATE_WINDOW_S = 60
_RATE_MAX = 60
_GLOBAL_MAX = 1200
_MAX_KEYS = 10_000
_recent: "OrderedDict[str, Deque[float]]" = OrderedDict()
_global: Deque[float] = deque()


def _trim(q: Deque[float], now: float) -> None:
    while q and now - q[0] > _RATE_WINDOW_S:
        q.popleft()


def _allow(ip: str) -> bool:
    now = time.monotonic()
    _trim(_global, now)
    if len(_global) >= _GLOBAL_MAX:
        return False
    q = _recent.pop(ip, None) or deque()
    _trim(q, now)
    _recent[ip] = q                 # most recently used goes last
    if len(_recent) > _MAX_KEYS:    # evict the least recently used client
        _recent.popitem(last=False)
    if len(q) >= _RATE_MAX:
        return False
    q.append(now)
    _global.append(now)
    return True


def _increment(name: str, day: str) -> None:
    db = get_db()
    if db is None:
        return
    try:
        from google.cloud import firestore as gcf
        db.collection(COLLECTION).document(day).set({"counts": {name: gcf.Increment(1)}}, merge=True)
    except Exception as e:
        logger.warning(f"Analytics write failed: {e}")


@router.post("")
async def record_event(request: Request, background: BackgroundTasks):
    """Body: {"name": "<event>"}. Unknown names are ignored."""
    try:
        body = await request.json()
    except Exception:
        return {"ok": False}
    name = body.get("name") if isinstance(body, dict) else None
    if name not in ALLOWED:
        return {"ok": False}
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else ""))
    if not _allow(ip):
        return {"ok": False}
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    background.add_task(_increment, name, day)
    return {"ok": True}


def _require_admin(user: dict) -> None:
    admins = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
    if not user.get("email") or user["email"].lower() not in admins:
        raise HTTPException(status_code=403, detail="Admins only")


def summarise_funnel(days: Dict[str, Dict[str, int]]) -> Dict:
    totals = {name: sum(d.get(name, 0) for d in days.values()) for name in sorted(ALLOWED)}
    steps = []
    prev = None
    for name in FUNNEL:
        n = totals.get(name, 0)
        steps.append({
            "step": name,
            "count": n,
            "from_previous": round(n / prev, 3) if prev else None,
        })
        prev = n or None
    return {"totals": totals, "funnel": steps}


@admin_router.get("/funnel")
async def get_funnel(days: int = Query(30, ge=1, le=365), user: dict = Depends(get_current_user)):
    _require_admin(user)
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    start = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    day_ids = [(start + timedelta(days=i)).isoformat() for i in range(days)]

    def read_all() -> Dict[str, Dict[str, int]]:
        refs = [db.collection(COLLECTION).document(d) for d in day_ids]
        found = {snap.id: (snap.to_dict() or {}).get("counts", {}) for snap in db.get_all(refs) if snap.exists}
        return {d: found.get(d, {}) for d in day_ids}

    by_day = await asyncio.to_thread(read_all)
    return {"days": by_day, **summarise_funnel(by_day)}

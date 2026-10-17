"""
Funnel analytics without third-party trackers: the frontend posts anonymous
event names, the backend keeps daily counts in Firestore
(analytics_daily/{YYYY-MM-DD}). No user ids, no cookies, no IP storage.

GET /api/admin/funnel is limited to emails listed in ADMIN_EMAILS.
"""

import logging
import os
import time
from collections import defaultdict, deque
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
OTHER = {"plan_view", "optimise", "track_record_view", "share", "calendar_subscribe"}
ALLOWED = set(FUNNEL) | OTHER

# Per-instance rate limit so a script can't inflate counts cheaply
_RATE_WINDOW_S = 60
_RATE_MAX = 60
_recent: Dict[str, Deque[float]] = defaultdict(deque)


def _allow(ip: str) -> bool:
    now = time.monotonic()
    q = _recent[ip]
    while q and now - q[0] > _RATE_WINDOW_S:
        q.popleft()
    if len(q) >= _RATE_MAX:
        return False
    q.append(now)
    if len(_recent) > 10_000:   # keep memory bounded
        _recent.clear()
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
    by_day = {}
    for i in range(days):
        day = (start + timedelta(days=i)).isoformat()
        snap = db.collection(COLLECTION).document(day).get()
        by_day[day] = (snap.to_dict() or {}).get("counts", {}) if snap.exists else {}
    return {"days": by_day, **summarise_funnel(by_day)}

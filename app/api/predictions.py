"""
Predictions API Router
Prediction history (the live track record) and the scheduled refresh hook.
"""

import hmac
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ..auth.firebase_auth import get_db
from ..services import track_record
from ..services.data_service import FPLDataService, get_data_service
from ..services.xp_service import get_xp_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/history")
async def get_prediction_history(data_service: FPLDataService = Depends(get_data_service)):
    """This season's gameweeks: predictions saved before each deadline, scored after."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    live = await track_record.live_record(data_service, db)
    return {"season": live["season"], "history": live["gameweeks"], "summary": live["summary"]}


@router.post("/refresh")
async def scheduled_refresh(
    x_cron_secret: Optional[str] = Header(None),
    data_service: FPLDataService = Depends(get_data_service),
):
    """
    Recompute xP, snapshot the next gameweek and score finished ones.
    For Cloud Scheduler (hourly), so snapshots don't depend on site traffic.
    Requires the X-Cron-Secret header to match CRON_SECRET.
    """
    secret = os.getenv("CRON_SECRET", "")
    if not secret or not x_cron_secret or not hmac.compare_digest(secret, x_cron_secret):
        raise HTTPException(status_code=403, detail="Forbidden")
    xp = get_xp_service()
    await xp.refresh(data_service)
    return {"ok": xp.ready, "gameweek": xp.next_gw,
            "updated_at": xp.updated_at.isoformat() if xp.updated_at else None}

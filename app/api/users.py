"""
Users API — plan info, account management.
"""

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..auth.firebase_auth import get_current_user, get_db, PLANS

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user's plan, limits, and subscription status."""
    if not user["uid"]:
        return {
            "authenticated": False,
            "plan":          "free",
            "limits":        PLANS["free"],
        }

    # Pull subscription details from Firestore
    subscription = None
    db = get_db()
    if db:
        doc = db.collection("users").document(user["uid"]).get()
        if doc.exists:
            d = doc.to_dict()
            subscription = {
                "plan":                  d.get("plan", "free"),
                "plan_expires_at":       d.get("plan_expires_at"),
                "subscription_cancelled": d.get("subscription_cancelled", False),
                "has_token":             bool(d.get("payfast_token")),
            }

    return {
        "authenticated": True,
        "uid":           user["uid"],
        "email":         user["email"],
        "plan":          user["plan"],
        "limits":        PLANS.get(user["plan"], PLANS["free"]),
        "subscription":  subscription,
    }


@router.post("/upgrade-manual")
async def manual_upgrade(
    payload: dict,
    user: dict = Depends(get_current_user),
):
    """
    Internal endpoint — called by PayStack webhook after verifying payment.
    Can also be called manually for testing.
    """
    if not user["uid"]:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    plan = payload.get("plan", "pro")
    expires = datetime.now(timezone.utc) + timedelta(days=30)

    db.collection("users").document(user["uid"]).update({
        "plan":             plan,
        "plan_expires_at":  expires.isoformat(),
        "updated_at":       datetime.now(timezone.utc).isoformat(),
    })

    return {"success": True, "plan": plan, "expires": expires.isoformat()}

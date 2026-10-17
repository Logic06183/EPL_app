"""
Users API — plan info, account management.
"""

import logging
from fastapi import APIRouter, Depends

from ..auth.firebase_auth import (
    get_current_user, get_db, PLANS, _in_grace_period, _LAUNCH_FREE_UNTIL_RAW,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user's plan, limits, and subscription status."""
    grace_info = {
        "in_grace_period":     _in_grace_period(),
        "launch_free_until":   _LAUNCH_FREE_UNTIL_RAW,
    }

    if not user["uid"]:
        return {
            "authenticated": False,
            "plan":          "free",
            "limits":        PLANS["free"],
            "grace":         grace_info,
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
        "grace":         grace_info,
    }

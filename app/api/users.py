"""
Users API — plan info, account management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

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


@router.post("/desktop-token")
async def desktop_token(user: dict = Depends(get_current_user)):
    """
    Mint a Firebase custom token for the signed-in user.

    Google blocks OAuth inside embedded webviews, so the Mac app signs in via
    the system browser, which calls this with the browser session's ID token
    and hands the custom token back to the app through the fplai:// deep link.
    The app then calls signInWithCustomToken. Custom tokens expire in an hour
    and can only be redeemed by the Firebase project that issued them.
    """
    if not user["uid"]:
        raise HTTPException(status_code=401, detail="Sign in first")
    try:
        from firebase_admin import auth
        token = auth.create_custom_token(user["uid"])
    except Exception as e:
        logger.error(f"Custom token failed for {user['uid']}: {e}")
        raise HTTPException(status_code=503, detail="Could not create a desktop sign-in token")
    return {"custom_token": token.decode() if isinstance(token, bytes) else token}

"""
Users API — plan info, account management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth.firebase_auth import (
    _LAUNCH_FREE_UNTIL_RAW,
    PLANS,
    _in_grace_period,
    get_current_user,
    get_db,
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


@router.delete("/me")
async def delete_me(user: dict = Depends(get_current_user)):
    """
    Delete the signed-in user's account (POPIA / GDPR erasure).

    Cancels any live PayFast subscription first so they aren't billed again,
    then removes the Firestore record and the Firebase Auth user. PayFast keeps
    its own payment records.
    """
    if not user["uid"]:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    doc_ref = db.collection("users").document(user["uid"])
    doc = doc_ref.get()
    data = doc.to_dict() if doc.exists else {}

    if data.get("payfast_token") and not data.get("subscription_cancelled"):
        from .payments import cancel_payfast_subscription
        await cancel_payfast_subscription(data["payfast_token"])

    doc_ref.delete()
    try:
        from firebase_admin import auth as fb_auth
        fb_auth.delete_user(user["uid"])
    except Exception as e:
        # Firestore data is already gone; a lingering auth record holds only the email.
        logger.error(f"Firebase Auth delete failed for uid={user['uid']}: {e}")

    logger.info(f"Deleted account uid={user['uid']}")
    return {"deleted": True}

"""
Firebase Auth + Firestore integration.

Setup required (one-time):
1. Firebase Console → Authentication → Enable Google provider
2. Firebase Console → Firestore → Create database (Native mode)
3. GCP Console → IAM → find the Cloud Run service account
   (PROJECT_NUMBER-compute@developer.gserviceaccount.com)
   → Add role: "Firebase Admin SDK Administrator Service Agent"
4. No credential files needed on Cloud Run — uses Application Default Credentials.
   For local dev: run `gcloud auth application-default login`
"""

import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from fastapi import Header

logger = logging.getLogger(__name__)

# Lazy imports — only load firebase_admin when first used
_firebase_app = None
_db = None


def _init_firebase():
    global _firebase_app, _db
    if _firebase_app is not None:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred_json = os.getenv("FIREBASE_CREDENTIALS")
            if cred_json:
                cred = credentials.Certificate(json.loads(cred_json))
                _firebase_app = firebase_admin.initialize_app(cred)
            else:
                # Application Default Credentials (works on Cloud Run automatically)
                _firebase_app = firebase_admin.initialize_app()

        _db = firestore.client()
        logger.info("Firebase Admin initialised")
    except Exception as e:
        logger.warning(f"Firebase not available: {e}. Auth will be disabled.")


def get_db():
    _init_firebase()
    return _db


# ── Plan definitions ──────────────────────────────────

PLANS = {
    "free": {
        "label":             "Free",
        "predictions_limit": 10,
        "captain":           False,
        "fdr":               False,
        "team_import":       False,
        "price_movers":      False,
        "differentials":     False,
        "value":             False,
        "injuries_limit":    5,
    },
    "pro": {
        "label":             "Pro",
        "predictions_limit": 100,
        "captain":           True,
        "fdr":               True,
        "team_import":       True,
        "price_movers":      True,
        "differentials":     True,
        "value":             True,
        "injuries_limit":    999,
    },
}


def plan_limits(plan: str) -> dict:
    return PLANS.get(plan, PLANS["free"])


# ── Token verification ────────────────────────────────

async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> dict:
    """
    FastAPI dependency. Returns user dict with uid, email, plan.
    Anonymous users get plan='free'. Never raises — always returns something.
    """
    anon = {"uid": None, "email": None, "plan": "free"}

    if not authorization or not authorization.startswith("Bearer "):
        return anon

    token = authorization[7:]
    try:
        import firebase_admin
        from firebase_admin import auth

        _init_firebase()
        if not firebase_admin._apps:
            return anon

        decoded = auth.verify_id_token(token)
        uid   = decoded["uid"]
        email = decoded.get("email", "")

        db = get_db()
        if db is None:
            return {**anon, "uid": uid, "email": email}

        doc_ref  = db.collection("users").document(uid)
        doc      = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            plan = data.get("plan", "free")
            # Check expiry
            expires = data.get("plan_expires_at")
            if expires:
                exp_dt = expires if isinstance(expires, datetime) else datetime.fromisoformat(str(expires))
                if exp_dt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    plan = "free"
                    doc_ref.update({"plan": "free"})
        else:
            plan = "free"
            doc_ref.set({
                "email":      email,
                "plan":       "free",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        return {"uid": uid, "email": email, "plan": plan}

    except Exception as e:
        logger.debug(f"Token verification failed: {e}")
        return anon


def require_pro(user: dict):
    """Raise 403 if user is not on a paid plan."""
    from fastapi import HTTPException
    if plan_limits(user["plan"])["predictions_limit"] <= 10:
        raise HTTPException(
            status_code=403,
            detail={
                "error":   "upgrade_required",
                "message": "This feature requires FPL AI Pro. Upgrade at /pricing.",
                "plan":    user["plan"],
            }
        )

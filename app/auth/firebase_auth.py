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
    # Founder = same perks as Pro, granted free to anyone who signs in
    # before LAUNCH_FREE_UNTIL. Lifetime — never expires. The reward for
    # showing up early.
    "founder": {
        "label":             "Founder",
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


# ── Launch grace period ───────────────────────────────────────────────────────

# Until this date (UTC), every signed-in user is granted "founder" automatically.
# Anonymous (not-signed-in) users are *also* treated as Pro during grace via
# get_effective_plan(). Default of "2099-01-01" = grace forever until Craig
# explicitly sets the env var to flip the paywall on. Safe by default.
_LAUNCH_FREE_UNTIL_RAW = os.getenv("LAUNCH_FREE_UNTIL", "2099-01-01")


def _in_grace_period(now: Optional[datetime] = None) -> bool:
    try:
        cutoff = datetime.fromisoformat(_LAUNCH_FREE_UNTIL_RAW).replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning(f"Invalid LAUNCH_FREE_UNTIL='{_LAUNCH_FREE_UNTIL_RAW}', defaulting to in-grace")
        return True
    return (now or datetime.now(timezone.utc)) < cutoff


def get_effective_plan(user: dict) -> str:
    """
    Plan to use for gating decisions. During grace period anonymous and free
    users are treated as 'pro' so they experience the full app. After grace,
    the stored plan stands.
    """
    plan = user.get("plan", "free")
    if plan in ("pro", "founder"):
        return plan
    return "pro" if _in_grace_period() else plan


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

        in_grace = _in_grace_period()

        if doc.exists:
            data = doc.to_dict()
            plan = data.get("plan", "free")
            # Check expiry (founders never expire)
            expires = data.get("plan_expires_at")
            if expires and plan != "founder":
                exp_dt = expires if isinstance(expires, datetime) else datetime.fromisoformat(str(expires))
                if exp_dt.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    plan = "free"
                    doc_ref.update({"plan": "free"})
            # Founder upgrade: existing free user signs in during grace → reward
            if in_grace and plan == "free":
                plan = "founder"
                doc_ref.update({"plan": "founder", "founder_granted_at": datetime.now(timezone.utc).isoformat()})
        else:
            # Brand-new user. Founder during grace, free after.
            plan = "founder" if in_grace else "free"
            new_doc = {
                "email":      email,
                "plan":       plan,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if plan == "founder":
                new_doc["founder_granted_at"] = new_doc["created_at"]
            doc_ref.set(new_doc)

        return {"uid": uid, "email": email, "plan": plan}

    except Exception as e:
        logger.debug(f"Token verification failed: {e}")
        return anon


def require_pro(user: dict):
    """
    Raise 403 if the user can't access Pro features.
    During the launch grace period this is a no-op — anonymous and free users
    are treated as Pro. Founders/Pro always pass.
    """
    from fastapi import HTTPException
    effective = get_effective_plan(user)
    if effective in ("pro", "founder"):
        return
    raise HTTPException(
        status_code=403,
        detail={
            "error":   "upgrade_required",
            "message": "This feature requires FPL AI Pro. Upgrade at /pricing.",
            "plan":    user["plan"],
        }
    )

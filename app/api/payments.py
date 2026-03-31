"""
Payments API — PayFast integration (South Africa)
Handles subscription initialisation, ITN webhooks, and cancellation.
Subscriptions auto-renew monthly via PayFast recurring billing.
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import urlencode, quote_plus

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth.firebase_auth import get_current_user, get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ── PayFast config ─────────────────────────────────────────────────────────────
PAYFAST_MERCHANT_ID  = os.getenv("PAYFAST_MERCHANT_ID",  "")
PAYFAST_MERCHANT_KEY = os.getenv("PAYFAST_MERCHANT_KEY", "")
PAYFAST_PASSPHRASE   = os.getenv("PAYFAST_PASSPHRASE",   "")
PAYFAST_SANDBOX      = os.getenv("PAYFAST_SANDBOX", "false").lower() == "true"

PAYFAST_HOST = (
    "https://sandbox.payfast.co.za" if PAYFAST_SANDBOX
    else "https://www.payfast.co.za"
)
PAYFAST_API = (
    "https://api.sandbox.payfast.co.za" if PAYFAST_SANDBOX
    else "https://api.payfast.co.za"
)

PLANS = {
    "pro": {
        "name":     "FPL AI Pro",
        "amount":   "199.00",    # ZAR monthly
        "currency": "ZAR",
        "features": [
            "Captain recommendations",
            "FDR heatmap",
            "FPL team import & transfer suggestions",
            "Price movers & value picks",
            "Differentials radar",
            "Unlimited predictions (all models)",
            "3-GW fixture planner",
        ],
    },
}


# ── Signature helpers ──────────────────────────────────────────────────────────

def _payfast_signature(params: Dict[str, str], passphrase: str = "") -> str:
    """
    MD5 signature matching PayFast PHP SDK exactly:
      foreach($data as $key => $val) {
          if($val !== '') { $out .= $key.'='.urlencode(trim($val)).'&'; }
      }
    """
    parts = []
    for k, v in params.items():
        v_str = str(v).strip()
        if v_str != "":
            parts.append(f"{k}={quote_plus(v_str)}")
    param_string = "&".join(parts)
    if passphrase:
        param_string += f"&passphrase={quote_plus(passphrase.strip())}"
    return hashlib.md5(param_string.encode("utf-8")).hexdigest()


def _payfast_api_headers() -> Dict[str, str]:
    """
    Build headers for PayFast API calls (subscriptions management).
    Signature = MD5 of sorted headers + passphrase.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    headers_to_sign = {
        "merchant-id": PAYFAST_MERCHANT_ID,
        "passphrase":  PAYFAST_PASSPHRASE,
        "timestamp":   ts,
        "version":     "v1",
    }
    # Sort alphabetically, build query string
    param_string = "&".join(
        f"{k}={quote_plus(str(v))}"
        for k, v in sorted(headers_to_sign.items())
    )
    signature = hashlib.md5(param_string.encode("utf-8")).hexdigest()
    return {
        "merchant-id": PAYFAST_MERCHANT_ID,
        "version":     "v1",
        "timestamp":   ts,
        "signature":   signature,
    }


def _verify_itn(data: Dict[str, str]) -> bool:
    """Verify a PayFast ITN payload signature."""
    received_sig = data.get("signature", "")
    params = {k: v for k, v in data.items() if k != "signature"}
    expected = _payfast_signature(params, PAYFAST_PASSPHRASE)
    return received_sig == expected


# ── Models ─────────────────────────────────────────────────────────────────────

class PaymentInitRequest(BaseModel):
    plan_id:    str
    email:      str
    return_url: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans():
    """Return available subscription plans."""
    return {"plans": PLANS}


@router.post("/initialize")
async def initialize_payment(request: PaymentInitRequest):
    """
    Build a PayFast recurring-subscription payment URL.
    Returns { authorization_url, reference }.
    PayFast will auto-renew monthly and POST ITN on each renewal.
    """
    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not PAYFAST_MERCHANT_ID or not PAYFAST_MERCHANT_KEY:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Parameter order must match PayFast's expected order exactly
    params: Dict[str, str] = {
        "merchant_id":       PAYFAST_MERCHANT_ID,
        "merchant_key":      PAYFAST_MERCHANT_KEY,
        "return_url":        request.return_url,
        "cancel_url":        request.return_url + ("&" if "?" in request.return_url else "?") + "cancelled=1",
        "notify_url":        os.getenv(
            "PAYFAST_NOTIFY_URL",
            "https://epl-api-77913915885.us-central1.run.app/api/payments/webhook"
        ),
        "email_address":     request.email,
        "amount":            plan["amount"],
        "item_name":         plan["name"],
        # Recurring subscription — monthly, indefinite
        "subscription_type": "1",
        "billing_date":      today,       # must be explicit or PayFast adds its own
        "recurring_amount":  plan["amount"],
        "frequency":         "3",         # 3 = monthly
        "cycles":            "0",         # 0 = unlimited
        # Pass plan and email to webhook so it can upgrade the user
        "custom_str1":       request.plan_id,
        "custom_str2":       request.email,
    }

    sig = _payfast_signature(params, PAYFAST_PASSPHRASE)
    logger.info(f"PayFast sig params: {list(params.keys())} → {sig}")
    params["signature"] = sig
    payment_url = f"{PAYFAST_HOST}/eng/process?{urlencode(params)}"

    return {
        "authorization_url": payment_url,
        "reference":         params["signature"],
    }


@router.post("/webhook")
async def handle_itn(request: Request):
    """
    Handle PayFast ITN (Instant Transaction Notification).
    Fires on initial payment AND on each monthly renewal.
    """
    try:
        form = await request.form()
        data = dict(form)

        logger.info(
            f"PayFast ITN: status={data.get('payment_status')} "
            f"token={data.get('token','')} ref={data.get('pf_payment_id','')}"
        )

        if PAYFAST_PASSPHRASE and not _verify_itn(data):
            logger.warning("PayFast ITN signature mismatch — ignoring")
            raise HTTPException(status_code=400, detail="Invalid ITN signature")

        if data.get("payment_status") != "COMPLETE":
            return {"status": "ignored", "reason": data.get("payment_status")}

        email   = data.get("custom_str2") or data.get("email_address", "")
        plan_id = data.get("custom_str1", "pro")
        ref     = data.get("pf_payment_id", "")
        token   = data.get("token", "")   # subscription token for future cancellation

        if email:
            await _upgrade_user_by_email(email, plan_id, ref, token)

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ITN processing error: {e}")
        raise HTTPException(status_code=500, detail="ITN processing failed")


@router.post("/cancel")
async def cancel_subscription(user: dict = Depends(get_current_user)):
    """
    Cancel the current user's PayFast recurring subscription.
    They keep Pro access until plan_expires_at, then revert to Free.
    """
    if not user["uid"]:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    doc = db.collection("users").document(user["uid"]).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    data = doc.to_dict()
    token = data.get("payfast_token", "")

    if not token:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found. Contact support if you believe this is an error."
        )

    # Call PayFast API to cancel recurring subscription
    try:
        headers = _payfast_api_headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.put(
                f"{PAYFAST_API}/subscriptions/{token}/cancel",
                headers=headers,
            )
        if resp.status_code not in (200, 204):
            logger.error(f"PayFast cancel API returned {resp.status_code}: {resp.text}")
            raise HTTPException(
                status_code=502,
                detail="PayFast could not cancel subscription. Please try again or contact support."
            )
        logger.info(f"PayFast subscription {token} cancelled for {user['email']}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PayFast cancel error: {e}")
        raise HTTPException(status_code=502, detail="Could not reach PayFast to cancel")

    # Mark as cancelled in Firestore — keep plan active until expiry
    db.collection("users").document(user["uid"]).update({
        "subscription_cancelled": True,
        "subscription_cancelled_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    expires = data.get("plan_expires_at", "")
    return {
        "status":  "cancelled",
        "message": "Your subscription has been cancelled. You will keep Pro access until your current period ends.",
        "access_until": expires,
    }


# ── Firestore upgrade helper ───────────────────────────────────────────────────

async def _upgrade_user_by_email(email: str, plan: str, reference: str, token: str = ""):
    """Look up Firebase user by email and set their plan + subscription token in Firestore."""
    from datetime import timedelta

    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth

        if not firebase_admin._apps:
            logger.warning("Firebase not initialised — skipping upgrade")
            return

        fb_user = fb_auth.get_user_by_email(email)
        uid     = fb_user.uid
        db      = get_db()
        if db is None:
            logger.warning("Firestore not available — skipping upgrade")
            return

        expires = datetime.now(timezone.utc) + timedelta(days=32)  # slight buffer over 30
        update  = {
            "email":              email,
            "plan":               plan,
            "plan_expires_at":    expires.isoformat(),
            "payfast_reference":  reference,
            "subscription_cancelled": False,
            "updated_at":         datetime.now(timezone.utc).isoformat(),
        }
        if token:
            update["payfast_token"] = token   # needed for cancellation

        db.collection("users").document(uid).set(update, merge=True)
        logger.info(f"Upgraded {email} → plan={plan}, expires={expires.date()}, token={token or 'n/a'}")

    except Exception as e:
        logger.error(f"Failed to upgrade {email}: {e}")

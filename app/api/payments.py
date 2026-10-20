"""
Payments API — PayFast integration (South Africa)
Handles subscription initialisation, ITN webhooks, and cancellation.
Monthly plan auto-renews via PayFast recurring billing; the season pass is once-off.
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode, quote_plus, urlparse

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
# Stable notify URL: Firebase Hosting rewrites /api/** to the live Cloud Run service
PAYFAST_NOTIFY_URL = os.getenv(
    "PAYFAST_NOTIFY_URL",
    "https://epl-prediction-app.web.app/api/payments/webhook",
)

ALLOWED_RETURN_ORIGINS = [
    o.strip() for o in os.getenv(
        "PAYMENT_RETURN_ORIGINS",
        "https://epl-prediction-app.web.app,"
        "https://epl-prediction-app.firebaseapp.com,"
        "http://localhost:8001,http://localhost:3000",
    ).split(",") if o.strip()
]

PAYFAST_API = (
    "https://api.sandbox.payfast.co.za" if PAYFAST_SANDBOX
    else "https://api.payfast.co.za"
)

FEATURES = [
    "Personal briefing every gameweek",
    "Transfer planner with chips and hits",
    "Squad optimiser and 3-GW planner",
    "Mini-league view",
]

# "pro" stays the monthly id so older clients keep working.
PLANS = {
    "pro": {
        "name":      "FPL AI Pro (monthly)",
        "amount":    "79.00",     # ZAR, renews monthly
        "currency":  "ZAR",
        "recurring": True,
        "features":  FEATURES,
    },
    "season": {
        "name":      "FPL AI Season Pass",
        "amount":    "449.00",    # ZAR once-off, valid to 31 May
        "currency":  "ZAR",
        "recurring": False,
        "features":  FEATURES,
    },
}


def _season_end(now: datetime) -> datetime:
    """31 May at the end of the season running on `now` (seasons start in August)."""
    year = now.year + 1 if now.month >= 6 else now.year
    return datetime(year, 5, 31, 23, 59, tzinfo=timezone.utc)


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


def _itn_param_string(data: Dict[str, str]) -> str:
    """
    ITN param string, in the order PayFast posted it. Unlike the checkout
    signature, blank values are kept (PayFast's ITN sample does not skip them).
    """
    return "&".join(
        f"{k}={quote_plus(str(v).strip())}" for k, v in data.items() if k != "signature"
    )


def _verify_itn(data: Dict[str, str]) -> bool:
    """Verify a PayFast ITN payload signature."""
    received_sig = data.get("signature", "")
    param_string = _itn_param_string(data)
    if PAYFAST_PASSPHRASE:
        param_string += f"&passphrase={quote_plus(PAYFAST_PASSPHRASE.strip())}"
    expected = hashlib.md5(param_string.encode("utf-8")).hexdigest()
    return hmac.compare_digest(received_sig, expected)


async def _confirm_itn_with_payfast(data: Dict[str, str]) -> bool:
    """Ask PayFast to confirm the ITN really came from them."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{PAYFAST_HOST}/eng/query/validate",
                content=_itn_param_string(data),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        return resp.text.strip() == "VALID"
    except Exception as e:
        logger.error(f"PayFast ITN validation call failed: {e}")
        return False


def _amount_matches(data: Dict[str, str], plan: Dict[str, Any]) -> bool:
    try:
        return abs(float(data.get("amount_gross", "0")) - float(plan["amount"])) < 0.01
    except ValueError:
        return False


def _safe_return_url(url: str) -> str:
    """Only redirect back to our own origins after checkout."""
    try:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
    except ValueError:
        origin = ""
    if origin in ALLOWED_RETURN_ORIGINS:
        return url
    return f"{ALLOWED_RETURN_ORIGINS[0]}/?upgraded=1"


# ── Models ─────────────────────────────────────────────────────────────────────

class PaymentInitRequest(BaseModel):
    plan_id:    str
    return_url: str
    email:      Optional[str] = None   # ignored; kept for older clients


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans():
    """Return available subscription plans."""
    return {"plans": PLANS}


@router.post("/initialize")
async def initialize_payment(
    request: PaymentInitRequest,
    user: dict = Depends(get_current_user),
):
    """
    Build a PayFast recurring-subscription payment URL for the signed-in user.
    Returns { authorization_url, reference }.
    PayFast will auto-renew monthly and POST ITN on each renewal.
    """
    if not user["uid"]:
        raise HTTPException(status_code=401, detail="Sign in to upgrade")

    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not PAYFAST_MERCHANT_ID or not PAYFAST_MERCHANT_KEY:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return_url = _safe_return_url(request.return_url)
    m_payment_id = f"{user['uid']}-{int(datetime.now(timezone.utc).timestamp())}"

    # Field order matters: PayFast signs fields in its documented order
    # (custom_* before the subscription fields).
    params: Dict[str, str] = {
        "merchant_id":       PAYFAST_MERCHANT_ID,
        "merchant_key":      PAYFAST_MERCHANT_KEY,
        "return_url":        return_url,
        "cancel_url":        return_url + ("&" if "?" in return_url else "?") + "cancelled=1",
        "notify_url":        PAYFAST_NOTIFY_URL,
        "email_address":     user.get("email") or "",
        "m_payment_id":      m_payment_id,
        "amount":            plan["amount"],
        "item_name":         plan["name"],
        # Identify the user by uid in the webhook — never trust an email field
        "custom_str1":       request.plan_id,
        "custom_str2":       user["uid"],
    }
    if plan["recurring"]:
        params.update({
            "subscription_type": "1",
            "billing_date":      today,   # must be explicit or PayFast adds its own
            "recurring_amount":  plan["amount"],
            "frequency":         "3",     # 3 = monthly
            "cycles":            "0",     # 0 = unlimited
        })

    sig = _payfast_signature(params, PAYFAST_PASSPHRASE)

    # Subscriptions need a passphrase-signed request. Sign whenever a
    # passphrase is configured unless explicitly disabled.
    require_sig = os.getenv(
        "PAYFAST_REQUIRE_SIGNATURE", "true" if PAYFAST_PASSPHRASE else "false"
    ).lower() == "true"
    if require_sig:
        params["signature"] = sig

    payment_url = f"{PAYFAST_HOST}/eng/process?{urlencode(params)}"

    return {
        "authorization_url": payment_url,
        "reference":         m_payment_id,
    }


@router.post("/webhook")
async def handle_itn(request: Request):
    """
    Handle PayFast ITN (Instant Transaction Notification).
    Fires on initial payment AND on each monthly renewal.

    Checks, per PayFast's ITN guide: signature (passphrase required), merchant
    id, amount, and a server-to-server confirmation with PayFast.
    """
    if not PAYFAST_PASSPHRASE:
        logger.error("PayFast ITN received but PAYFAST_PASSPHRASE is not set — refusing")
        raise HTTPException(status_code=503, detail="Payment service not configured")

    try:
        form = await request.form()
        data = {k: str(v) for k, v in form.items()}

        logger.info(
            f"PayFast ITN: status={data.get('payment_status')} "
            f"ref={data.get('pf_payment_id','')}"
        )

        if not _verify_itn(data):
            logger.warning("PayFast ITN signature mismatch — ignoring")
            raise HTTPException(status_code=400, detail="Invalid ITN signature")

        if data.get("merchant_id") != PAYFAST_MERCHANT_ID:
            logger.warning("PayFast ITN merchant_id mismatch — ignoring")
            raise HTTPException(status_code=400, detail="Invalid merchant")

        if not await _confirm_itn_with_payfast(data):
            logger.warning("PayFast did not confirm ITN — ignoring")
            raise HTTPException(status_code=400, detail="ITN not confirmed")

        status = data.get("payment_status")
        uid = data.get("custom_str2", "")

        if status == "CANCELLED":
            if uid:
                await _mark_cancelled(uid)
            return {"status": "ok"}

        if status != "COMPLETE":
            return {"status": "ignored", "reason": status}

        plan_id = data.get("custom_str1", "")
        plan = PLANS.get(plan_id)
        if not plan:
            logger.warning(f"PayFast ITN for unknown plan '{plan_id}' — ignoring")
            raise HTTPException(status_code=400, detail="Unknown plan")

        if not _amount_matches(data, plan):
            logger.warning(
                f"PayFast ITN amount {data.get('amount_gross')} != {plan['amount']} — ignoring"
            )
            raise HTTPException(status_code=400, detail="Amount mismatch")

        if uid:
            await _upgrade_user(
                uid, "pro", data.get("pf_payment_id", ""), data.get("token", ""),
                expires=None if plan["recurring"] else _season_end(datetime.now(timezone.utc)),
            )

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

async def _resolve_uid(ref: str) -> str:
    """custom_str2 holds a uid; checkouts started before this change held an email."""
    if "@" not in ref:
        return ref
    from firebase_admin import auth as fb_auth
    return fb_auth.get_user_by_email(ref).uid


async def _upgrade_user(uid_or_email: str, plan: str, reference: str, token: str = "",
                        expires: Optional[datetime] = None):
    """Set the user's plan + subscription token in Firestore."""
    from datetime import timedelta

    try:
        db = get_db()
        if db is None:
            logger.error("Firestore not available — could not record payment %s", reference)
            return
        uid = await _resolve_uid(uid_or_email)

        if expires is None:
            expires = datetime.now(timezone.utc) + timedelta(days=32)  # slight buffer over 30
        update  = {
            "plan":               plan,
            "plan_expires_at":    expires.isoformat(),
            "payfast_reference":  reference,
            "subscription_cancelled": False,
            "updated_at":         datetime.now(timezone.utc).isoformat(),
        }
        if token:
            update["payfast_token"] = token   # needed for cancellation

        db.collection("users").document(uid).set(update, merge=True)
        logger.info(f"Upgraded {uid} → plan={plan}, expires={expires.date()}")

    except Exception as e:
        logger.error(f"Failed to upgrade {uid_or_email}: {e}")


async def _mark_cancelled(uid_or_email: str):
    """Subscription cancelled at PayFast — keep access until plan_expires_at."""
    try:
        db = get_db()
        if db is None:
            return
        uid = await _resolve_uid(uid_or_email)
        db.collection("users").document(uid).set({
            "subscription_cancelled":    True,
            "subscription_cancelled_at": datetime.now(timezone.utc).isoformat(),
            "updated_at":                datetime.now(timezone.utc).isoformat(),
        }, merge=True)
    except Exception as e:
        logger.error(f"Failed to mark {uid_or_email} cancelled: {e}")

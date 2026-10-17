"""
Payments API — PayFast integration (South Africa)
Handles subscription initialisation, ITN webhooks, and cancellation.
Subscriptions auto-renew monthly via PayFast recurring billing.
"""

import hashlib
import hmac
import logging
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import quote_plus, urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth.firebase_auth import get_current_user, get_db
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ── PayFast config ─────────────────────────────────────────────────────────────
PAYFAST_MERCHANT_ID  = os.getenv("PAYFAST_MERCHANT_ID",  "")
PAYFAST_MERCHANT_KEY = os.getenv("PAYFAST_MERCHANT_KEY", "")
PAYFAST_PASSPHRASE   = os.getenv("PAYFAST_PASSPHRASE",   "")
PAYFAST_SANDBOX      = os.getenv("PAYFAST_SANDBOX", "false").lower() == "true"
PAYFAST_NOTIFY_URL   = os.getenv("PAYFAST_NOTIFY_URL", f"{settings.PUBLIC_BASE_URL}/api/payments/webhook")
# Server-to-server confirmation of each ITN with PayFast. Only disable in tests.
PAYFAST_VALIDATE_ITN = os.getenv("PAYFAST_VALIDATE_ITN", "true").lower() == "true"

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

def _payfast_signature(params: dict[str, str], passphrase: str = "") -> str:
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


def _payfast_api_headers() -> dict[str, str]:
    """
    Build headers for PayFast API calls (subscriptions management).
    Signature = MD5 of sorted headers + passphrase.
    """
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
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


def _verify_itn(data: dict[str, str]) -> bool:
    """Verify a PayFast ITN payload signature (fields in the order received)."""
    received_sig = data.get("signature", "")
    params = {k: v for k, v in data.items() if k != "signature"}
    expected = _payfast_signature(params, PAYFAST_PASSPHRASE)
    return hmac.compare_digest(received_sig, expected)


async def _confirm_itn_with_payfast(data: dict[str, str]) -> bool:
    """Ask PayFast to confirm the ITN really came from them (step 4 of their ITN checks)."""
    param_string = urlencode([(k, v) for k, v in data.items() if k != "signature"])
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{PAYFAST_HOST}/eng/query/validate",
                content=param_string,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        return resp.status_code == 200 and resp.text.strip() == "VALID"
    except httpx.HTTPError as e:
        logger.error(f"PayFast ITN validation request failed: {e}")
        return False


def _amount_matches(data: dict[str, str], plan_id: str) -> bool:
    try:
        return abs(float(data.get("amount_gross", "0")) - float(PLANS[plan_id]["amount"])) < 0.01
    except (KeyError, ValueError):
        return False


def _is_allowed_return_url(url: str) -> bool:
    """Only redirect back to our own origins after checkout (no open redirect)."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return parsed.scheme in ("http", "https", "capacitor") and (
        origin == settings.PUBLIC_BASE_URL or origin in settings.CORS_ORIGINS
    )


# ── Models ─────────────────────────────────────────────────────────────────────

class PaymentInitRequest(BaseModel):
    plan_id:    str
    return_url: str
    email:      str | None = None  # ignored — the signed-in user's email is used


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans():
    """Return available subscription plans."""
    return {"plans": PLANS}


@router.post("/initialize")
async def initialize_payment(request: PaymentInitRequest, user: dict = Depends(get_current_user)):
    """
    Build a PayFast recurring-subscription payment URL for the signed-in user.
    Returns { authorization_url, reference }.
    PayFast will auto-renew monthly and POST ITN on each renewal.
    """
    if not user.get("uid"):
        raise HTTPException(status_code=401, detail="Sign in before upgrading")

    plan = PLANS.get(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not _is_allowed_return_url(request.return_url):
        raise HTTPException(status_code=400, detail="return_url must point back to this app")

    if not PAYFAST_MERCHANT_ID or not PAYFAST_MERCHANT_KEY:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    today = datetime.now(UTC).strftime("%Y-%m-%d")

    # Parameter order must match PayFast's expected order exactly
    params: dict[str, str] = {
        "merchant_id":       PAYFAST_MERCHANT_ID,
        "merchant_key":      PAYFAST_MERCHANT_KEY,
        "return_url":        request.return_url,
        "cancel_url":        request.return_url + ("&" if "?" in request.return_url else "?") + "cancelled=1",
        "notify_url":        PAYFAST_NOTIFY_URL,
        "email_address":     user.get("email") or "",
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
        "custom_str2":       user.get("email") or "",
        "custom_str3":       user["uid"],
    }

    sig = _payfast_signature(params, PAYFAST_PASSPHRASE)

    # Only include the signature in the redirect URL if PayFast's
    # "Enable require signature" is turned ON in merchant settings.
    # When it is OFF, sending a mismatched signature causes a 400 error.
    # ITN (webhook) verification uses the passphrase separately.
    require_sig = os.getenv("PAYFAST_REQUIRE_SIGNATURE", "false").lower() == "true"
    if require_sig:
        params["signature"] = sig

    payment_url = f"{PAYFAST_HOST}/eng/process?{urlencode(params)}"

    return {
        "authorization_url": payment_url,
        "reference":         sig,
    }


@router.post("/webhook")
async def handle_itn(request: Request):
    """
    Handle PayFast ITN (Instant Transaction Notification).
    Fires on initial payment AND on each monthly renewal.

    Follows PayFast's ITN security checks: signature (with passphrase),
    merchant id, amount, and a server-side confirmation with PayFast.
    """
    if not PAYFAST_PASSPHRASE or not PAYFAST_MERCHANT_ID:
        # Without a passphrase anyone could forge an ITN and grant themselves Pro.
        logger.error("PayFast ITN received but PAYFAST_PASSPHRASE / MERCHANT_ID not configured")
        raise HTTPException(status_code=503, detail="Payment service not configured")

    try:
        form = await request.form()
        data = {k: str(v) for k, v in form.items()}

        logger.info(
            f"PayFast ITN: status={data.get('payment_status')} ref={data.get('pf_payment_id','')}"
        )

        if not _verify_itn(data):
            logger.warning("PayFast ITN signature mismatch — rejecting")
            raise HTTPException(status_code=400, detail="Invalid ITN signature")

        if data.get("merchant_id") != PAYFAST_MERCHANT_ID:
            logger.warning("PayFast ITN merchant_id mismatch — rejecting")
            raise HTTPException(status_code=400, detail="Invalid merchant")

        if data.get("payment_status") != "COMPLETE":
            return {"status": "ignored", "reason": data.get("payment_status")}

        plan_id = data.get("custom_str1", "pro")
        if plan_id not in PLANS or not _amount_matches(data, plan_id):
            logger.warning(f"PayFast ITN amount/plan mismatch: plan={plan_id} amount={data.get('amount_gross')}")
            raise HTTPException(status_code=400, detail="Amount mismatch")

        if PAYFAST_VALIDATE_ITN and not await _confirm_itn_with_payfast(data):
            logger.warning("PayFast did not confirm ITN — rejecting")
            raise HTTPException(status_code=400, detail="ITN not confirmed by PayFast")

        uid     = data.get("custom_str3", "")
        email   = data.get("custom_str2") or data.get("email_address", "")
        ref     = data.get("pf_payment_id", "")
        token   = data.get("token", "")   # subscription token for future cancellation

        if uid or email:
            await _upgrade_user(uid=uid, email=email, plan=plan_id, reference=ref, token=token)

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ITN processing error: {e}")
        raise HTTPException(status_code=500, detail="ITN processing failed")


async def cancel_payfast_subscription(token: str) -> None:
    """Cancel a PayFast recurring subscription. Raises HTTPException(502) on failure."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.put(
                f"{PAYFAST_API}/subscriptions/{token}/cancel",
                headers=_payfast_api_headers(),
            )
    except httpx.HTTPError as e:
        logger.error(f"PayFast cancel error: {e}")
        raise HTTPException(status_code=502, detail="Could not reach PayFast to cancel")
    if resp.status_code not in (200, 204):
        logger.error(f"PayFast cancel API returned {resp.status_code}: {resp.text}")
        raise HTTPException(
            status_code=502,
            detail="PayFast could not cancel subscription. Please try again or contact support."
        )


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

    await cancel_payfast_subscription(token)
    logger.info(f"PayFast subscription cancelled for uid={user['uid']}")

    # Mark as cancelled in Firestore — keep plan active until expiry
    db.collection("users").document(user["uid"]).update({
        "subscription_cancelled": True,
        "subscription_cancelled_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    })

    expires = data.get("plan_expires_at", "")
    return {
        "status":  "cancelled",
        "message": "Your subscription has been cancelled. You will keep Pro access until your current period ends.",
        "access_until": expires,
    }


# ── Firestore upgrade helper ───────────────────────────────────────────────────

async def _upgrade_user(uid: str, email: str, plan: str, reference: str, token: str = ""):
    """Set the user's plan + subscription token in Firestore. Prefers uid; falls back to email lookup."""
    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth

        db = get_db()  # also initialises firebase_admin
        if db is None or not firebase_admin._apps:
            raise RuntimeError("Firestore not available")

        if not uid:
            uid = fb_auth.get_user_by_email(email).uid

        expires = datetime.now(UTC) + timedelta(days=32)  # slight buffer over 30
        update  = {
            "plan":               plan,
            "plan_expires_at":    expires.isoformat(),
            "payfast_reference":  reference,
            "subscription_cancelled": False,
            "updated_at":         datetime.now(UTC).isoformat(),
        }
        if email:
            update["email"] = email
        if token:
            update["payfast_token"] = token   # needed for cancellation

        db.collection("users").document(uid).set(update, merge=True)
        logger.info(f"Upgraded uid={uid} → plan={plan}, expires={expires.date()}")

    except Exception as e:
        # Re-raise so the ITN returns 5xx and PayFast retries the notification.
        logger.error(f"Failed to upgrade uid={uid or '?'}: {e}")
        raise

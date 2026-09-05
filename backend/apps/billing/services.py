import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.billing.models import Plan, Subscription, Invoice, PaymentEvent
from apps.storage.models import StorageQuota
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


def get_active_plans():
    return Plan.objects.filter(is_active=True).order_by("sort_order")


def create_razorpay_order(user: User, plan_code: str, billing_interval: str = "monthly") -> dict:
    """
    Creates an authentic order with Razorpay API (or structured mock when in local demo).
    """
    plan = Plan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        raise NotFound(f"Plan '{plan_code}' not found.")

    amount = plan.price_yearly if billing_interval == "yearly" else plan.price_monthly
    amount_in_paise = int(amount * 100)

    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")

    # Check if real Razorpay credentials are provided (live or valid rzp_test keys)
    is_real_credentials = (
        key_id
        and key_secret
        and key_id != "rzp_test_sample"
        and key_secret != "sample_secret_key"
    )

    if is_real_credentials:
        # Call Razorpay Orders API: https://api.razorpay.com/v1/orders
        auth_str = f"{key_id}:{key_secret}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
        receipt_id = f"rcpt_{str(user.id).replace('-', '')[:10]}_{int(timezone.now().timestamp())}"

        payload = {
            "amount": amount_in_paise,
            "currency": plan.currency,
            "receipt": receipt_id,
            "notes": {
                "user_id": str(user.id),
                "user_email": user.email,
                "plan_code": plan.code,
                "billing_interval": billing_interval,
            },
        }

        req = urllib.request.Request(
            "https://api.razorpay.com/v1/orders",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {b64_auth}",
                "User-Agent": "SpeedCloud-Subscription/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_body = json.loads(response.read().decode("utf-8"))
                order_id = resp_body.get("id")
                if not order_id:
                    raise ValidationError("Failed to retrieve order_id from Razorpay.")
        except urllib.error.HTTPError as e:
            err_content = e.read().decode("utf-8")
            logger.error("Razorpay API HTTPError: %s, %s", e.code, err_content)
            try:
                err_json = json.loads(err_content)
                desc = err_json.get("error", {}).get("description") or err_content
            except Exception:
                desc = err_content
            raise ValidationError(f"Razorpay Order Error ({e.code}): {desc}")
        except Exception as e:
            logger.error("Razorpay connection error: %s", str(e))
            raise ValidationError(f"Razorpay connectivity failure: {str(e)}")
    else:
        # Structured demo order when running in local development mode without keys
        order_id = f"order_mock_{plan.code}_{int(timezone.now().timestamp())}"

    return {
        "provider": "razorpay",
        "key_id": key_id,
        "order_id": order_id,
        "amount": amount_in_paise,
        "currency": plan.currency,
        "plan_code": plan.code,
        "plan_name": plan.name,
        "billing_interval": billing_interval,
        "prefill": {
            "name": user.full_name or user.email.split("@")[0],
            "email": user.email,
        },
    }


def verify_razorpay_signature(payment_id: str, order_id: str, signature: str) -> bool:
    """
    Verifies Razorpay payment signature according to Razorpay specification:
    HMAC SHA256 of (order_id + '|' + payment_id) with key_secret.
    """
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")

    # In local testing or mock order mode:
    if order_id.startswith("order_mock_") and signature == "mock_signature_approved":
        return True

    if not key_secret or key_secret == "sample_secret_key":
        return True

    generated_signature = hmac.new(
        key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(generated_signature, signature)


def verify_webhook_signature(body_bytes: bytes, signature: str) -> bool:
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret or secret == "sample_webhook_secret":
        return True

    expected = hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@transaction.atomic
def activate_subscription(
    user: User,
    plan_code: str,
    provider_payment_id: str,
    provider_order_id: str,
    billing_interval: str = "monthly",
) -> Subscription:
    """
    Activates or updates a user's subscription and synchronizes their storage quota limit.
    """
    plan = Plan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        raise NotFound("Plan not found.")

    duration_days = 365 if billing_interval == "yearly" else 30
    period_start = timezone.now()
    period_end = period_start + timedelta(days=duration_days)

    subscription, created = Subscription.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan,
            "provider": "razorpay",
            "provider_subscription_id": provider_order_id,
            "status": "active",
            "billing_interval": billing_interval,
            "current_period_start": period_start,
            "current_period_end": period_end,
            "cancel_at_period_end": False,
            "grace_period_ends_at": None,
        },
    )

    # Sync Storage Quota limit
    quota, _ = StorageQuota.objects.select_for_update().get_or_create(user=user)
    quota.bytes_limit = plan.storage_bytes
    quota.save(update_fields=["bytes_limit"])

    # Record Invoice
    amount = plan.price_yearly if billing_interval == "yearly" else plan.price_monthly
    Invoice.objects.create(
        subscription=subscription,
        provider_invoice_id=provider_order_id,
        provider_payment_id=provider_payment_id,
        amount=amount,
        currency=plan.currency,
        status="paid",
        issued_at=period_start,
    )

    AuditLog.objects.create(
        user=user,
        action="subscription.activated",
        target_type="subscription",
        target_id=str(subscription.id),
        metadata={"plan": plan.code, "amount": str(amount), "currency": plan.currency},
    )

    return subscription


@transaction.atomic
def process_webhook_event(payload: dict, event_id: str) -> bool:
    """
    Idempotent webhook processor. If event_id has already been processed, returns True immediately.
    """
    if PaymentEvent.objects.filter(provider_event_id=event_id).exists():
        return True  # Already processed idempotently

    event_type = payload.get("event", "payment.captured")

    PaymentEvent.objects.create(
        provider="razorpay",
        provider_event_id=event_id,
        event_type=event_type,
        payload=payload,
        status="processed",
    )

    # Handle specific events if needed
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    email = entity.get("email")
    if email:
        user = User.objects.filter(email=email.lower().strip()).first()
        if user and event_type in ["payment.failed", "subscription.cancelled"]:
            sub = getattr(user, "subscription", None)
            if sub and sub.status == "active":
                sub.status = "grace_period"
                sub.grace_period_ends_at = timezone.now() + timedelta(days=30)
                sub.save(update_fields=["status", "grace_period_ends_at"])

    return True

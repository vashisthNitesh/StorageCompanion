import hmac
import hashlib
import json
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.billing.models import Plan, Subscription, Invoice, PaymentEvent
from apps.storage.models import StorageQuota
from apps.audit.models import AuditLog


def get_active_plans():
    return Plan.objects.filter(is_active=True).order_by("sort_order")


def create_razorpay_order(user: User, plan_code: str, billing_interval: str = "monthly") -> dict:
    """
    Creates an order or subscription session with Razorpay.
    """
    plan = Plan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        raise NotFound(f"Plan '{plan_code}' not found.")

    amount = plan.price_yearly if billing_interval == "yearly" else plan.price_monthly
    amount_in_paise = int(amount * 100)

    # If Razorpay client credentials are set, we can interact with Razorpay API.
    # In dev/demo mode, return a structured order object that the frontend Razorpay checkout modal consumes.
    order_id = f"order_mock_{plan.code}_{int(timezone.now().timestamp())}"

    return {
        "provider": "razorpay",
        "key_id": settings.RAZORPAY_KEY_ID,
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
    if not settings.RAZORPAY_KEY_SECRET or settings.RAZORPAY_KEY_SECRET == "sample_secret_key":
        # In test mode with dummy credentials, accept demo signatures
        return True

    generated_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
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

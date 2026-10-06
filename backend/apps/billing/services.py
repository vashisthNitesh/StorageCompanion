import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.parse
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


SAMPLE_KEY_SECRET = "sample_secret_key"
SAMPLE_KEY_ID = "rzp_test_sample"
SAMPLE_WEBHOOK_SECRET = "sample_webhook_secret"
MOCK_SIGNATURE = "mock_signature_approved"


def get_active_plans():
    return Plan.objects.filter(is_active=True).order_by("sort_order")


def payments_mock_mode() -> bool:
    """Mock (fake) payments are only honoured when explicitly enabled (local dev / tests)."""
    return bool(getattr(settings, "PAYMENTS_MOCK_MODE", False))


def has_real_razorpay_credentials() -> bool:
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    return bool(key_id and key_secret and key_id != SAMPLE_KEY_ID and key_secret != SAMPLE_KEY_SECRET)


def build_mock_order_id(plan_code: str, billing_interval: str) -> str:
    return f"order_mock_{plan_code}_{billing_interval}_{int(timezone.now().timestamp())}"


def mock_order_matches(order_id: str, plan_code: str, billing_interval: str) -> bool:
    return order_id.startswith(f"order_mock_{plan_code}_{billing_interval}_")


def fetch_razorpay_order(order_id: str) -> dict:
    """Fetches an order from the Razorpay Orders API (used to bind plan/amount/user to a payment)."""
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    b64_auth = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode("ascii")
    req = urllib.request.Request(
        f"https://api.razorpay.com/v1/orders/{urllib.parse.quote(order_id, safe='')}",
        headers={"Authorization": f"Basic {b64_auth}", "User-Agent": "SmartSpaceData-Subscription/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_order_for_activation(user: User, order_id: str, plan_code: str, billing_interval: str) -> None:
    """
    Ensures the plan/interval being activated is the one the order was created (and paid) for,
    and that the order belongs to this user. Raises ValidationError otherwise.
    """
    if order_id.startswith("order_mock_"):
        if not payments_mock_mode():
            raise ValidationError("Mock payments are disabled.")
        if not mock_order_matches(order_id, plan_code, billing_interval):
            raise ValidationError("Order does not match the requested plan.")
        return

    plan = Plan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        raise NotFound("Plan not found.")
    try:
        order = fetch_razorpay_order(order_id)
    except Exception as e:
        logger.error("Could not fetch Razorpay order %s: %s", order_id, e)
        raise ValidationError("Could not verify the payment order with Razorpay.") from e

    notes = order.get("notes") or {}
    expected_amount = int((plan.price_yearly if billing_interval == "yearly" else plan.price_monthly) * 100)
    if (
        notes.get("user_id") != str(user.id)
        or notes.get("plan_code") != plan.code
        or notes.get("billing_interval", "monthly") != billing_interval
        or int(order.get("amount", -1)) != expected_amount
    ):
        raise ValidationError("Order does not match the requested plan.")
    if order.get("status") not in (None, "paid", "attempted"):
        raise ValidationError("Order has not been paid.")


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

    if has_real_razorpay_credentials():
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
                "User-Agent": "SmartSpaceData-Subscription/1.0",
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
            raise ValidationError(f"Razorpay Order Error ({e.code}): {desc}") from e
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Razorpay connection error: %s", str(e))
            raise ValidationError(f"Razorpay connectivity failure: {str(e)}") from e
    elif payments_mock_mode():
        # Structured demo order when running in local development mode without keys
        order_id = build_mock_order_id(plan.code, billing_interval)
    else:
        raise ValidationError("Online payments are not configured yet. Please contact support.")

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

    # Mock orders are only accepted when mock payments are explicitly enabled (local dev / tests)
    if order_id.startswith("order_mock_"):
        return payments_mock_mode() and hmac.compare_digest(signature, MOCK_SIGNATURE)

    # Never treat a missing / sample secret as "valid": the sample value is public.
    if not key_secret or key_secret == SAMPLE_KEY_SECRET:
        return False

    generated_signature = hmac.new(
        key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(generated_signature, signature)


def verify_webhook_signature(body_bytes: bytes, signature: str) -> bool:
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret or not signature:
        return False
    # The sample secret is public; only allow it for local mock-mode testing.
    if secret == SAMPLE_WEBHOOK_SECRET and not payments_mock_mode():
        return False

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

    # Replay protection: a payment / order can only activate a subscription once
    if Invoice.objects.filter(provider_payment_id=provider_payment_id).exists() or Invoice.objects.filter(
        provider_invoice_id=provider_order_id
    ).exists():
        raise ValidationError("This payment has already been used.")

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
                sub.grace_period_ends_at = timezone.now() + timedelta(days=15)
                sub.save(update_fields=["status", "grace_period_ends_at"])

    return True


def purge_user_vault_data(user: User) -> int:
    """
    Permanently deletes all encrypted vault files and folders for a user
    whose 90-day data retention window has lapsed without subscription renewal.
    Reclaims storage quota completely.
    """
    from apps.storage.models import Node
    # Delete all file/folder nodes owned by user (cascades to FileVersion, chunks)
    deleted_count, _ = Node.objects.filter(owner=user).delete()

    quota = StorageQuota.objects.filter(user=user).first()
    if quota:
        quota.bytes_used = 0
        quota.bytes_limit = 0
        quota.save(update_fields=["bytes_used", "bytes_limit"])

    AuditLog.objects.create(
        user=user,
        action="user.data_purged_90_days",
        target_type="user",
        target_id=str(user.id),
        metadata={
            "reason": "90_day_unpaid_retention_lapsed",
            "nodes_deleted": deleted_count,
        },
    )
    return deleted_count


@transaction.atomic
def process_expired_subscriptions() -> dict:
    """
    Evaluates subscription lifecycle transitions:
    1. Subscriptions that reached current_period_end:
       - Moves to expired (90 days read-only retention) with uploads blocked.
       - grace_period_ends_at set to 90 days from expiration.
       - Reclaims unused reserved pool quota while preserving existing encrypted files.
    2. Subscriptions in expired / grace_period whose 90-day retention window has elapsed:
       - Permanently purges user files, resets quota, and marks status as 'purged'.
    """
    now = timezone.now()
    summary = {
        "transitioned_to_expired_grace": 0,
        "transitioned_to_grace_period": 0,
        "transitioned_to_expired": 0,
        "transitioned_to_canceled": 0,
        "purged_after_90_days": 0,
    }

    # 1. Process active/extended/trialing subscriptions past their billing cycle
    lapsed_subs = Subscription.objects.select_for_update().filter(
        status__in=["active", "extended", "trialing"],
        current_period_end__lt=now,
    )

    for sub in lapsed_subs:
        if sub.cancel_at_period_end:
            sub.status = "canceled"
            # 90-day retention still applies to preserve data before deletion
            sub.grace_period_ends_at = sub.current_period_end + timedelta(days=90)
            sub.save(update_fields=["status", "grace_period_ends_at"])

            # Reclaim unused pool quota while protecting existing files
            quota = StorageQuota.objects.filter(user=sub.user).first()
            if quota:
                quota.bytes_limit = max(0, quota.bytes_used)
                quota.save(update_fields=["bytes_limit"])

            AuditLog.objects.create(
                user=sub.user,
                action="subscription.canceled_period_end",
                target_type="subscription",
                target_id=str(sub.id),
                metadata={
                    "plan": sub.plan.code,
                    "retention_days": 90,
                    "grace_period_ends_at": sub.grace_period_ends_at.isoformat(),
                },
            )
            summary["transitioned_to_canceled"] += 1
        else:
            sub.status = "expired"
            sub.grace_period_ends_at = sub.current_period_end + timedelta(days=90)
            sub.save(update_fields=["status", "grace_period_ends_at"])

            # Reclaim unused pool quota
            quota = StorageQuota.objects.filter(user=sub.user).first()
            if quota:
                quota.bytes_limit = max(0, quota.bytes_used)
                quota.save(update_fields=["bytes_limit"])

            AuditLog.objects.create(
                user=sub.user,
                action="subscription.entered_90_day_retention",
                target_type="subscription",
                target_id=str(sub.id),
                metadata={
                    "plan": sub.plan.code,
                    "retention_days": 90,
                    "grace_period_ends_at": sub.grace_period_ends_at.isoformat(),
                },
            )
            summary["transitioned_to_expired_grace"] += 1
            summary["transitioned_to_grace_period"] += 1
            summary["transitioned_to_expired"] += 1

    # 2. Process expired/grace subscriptions that have exceeded the 90-day retention window
    purge_candidates = Subscription.objects.select_for_update().filter(
        status__in=["expired", "grace_period", "canceled", "past_due"],
        grace_period_ends_at__lt=now,
    )

    for sub in purge_candidates:
        # 90 days expired without subscription renewal -> purge vault data
        deleted_nodes = purge_user_vault_data(sub.user)

        sub.status = "purged"
        sub.save(update_fields=["status"])

        AuditLog.objects.create(
            user=sub.user,
            action="subscription.vault_purged_90_days",
            target_type="subscription",
            target_id=str(sub.id),
            metadata={
                "plan": sub.plan.code,
                "reason": "90_days_retention_elapsed_without_renewal",
                "nodes_deleted": deleted_nodes,
            },
        )
        summary["purged_after_90_days"] += 1

    return summary

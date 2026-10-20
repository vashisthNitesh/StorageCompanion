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
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.accounts.models import User
from apps.billing.gst import GST_STATES
from apps.billing.models import Plan, Subscription, Invoice, PaymentEvent, PaymentOrder
from apps.storage.models import StorageQuota
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


def get_active_plans():
    return Plan.objects.filter(is_active=True).order_by("sort_order")


class PaymentsNotConfigured(APIException):
    status_code = 503
    default_detail = "Online payments are not available right now. Please try again later."
    default_code = "payments_not_configured"


def razorpay_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def create_razorpay_order(
    user: User,
    plan_code: str,
    billing_interval: str = "monthly",
    billing_state: str = "",
) -> dict:
    """
    Creates an order with the Razorpay Orders API and records it locally, so that the
    plan and amount a payment buys are fixed on the server.
    """
    if not razorpay_configured():
        raise PaymentsNotConfigured()

    plan = Plan.objects.filter(code=plan_code, is_active=True).first()
    if not plan:
        raise NotFound(f"Plan '{plan_code}' not found.")
    if billing_state and billing_state not in GST_STATES:
        raise ValidationError("Unknown billing state.")

    amount = plan.price_yearly if billing_interval == "yearly" else plan.price_monthly
    amount_in_paise = int(amount * 100)

    key_id = settings.RAZORPAY_KEY_ID
    auth_str = f"{key_id}:{settings.RAZORPAY_KEY_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
    receipt_id = f"rcpt_{str(user.id).replace('-', '')[:10]}_{int(timezone.now().timestamp())}"

    payload = {
        "amount": amount_in_paise,
        "currency": plan.currency,
        "receipt": receipt_id,
        "notes": {
            "user_id": str(user.id),
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
            "User-Agent": "SmartSpace-Billing/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            resp_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8", errors="ignore")
        logger.error("Razorpay order creation failed: %s, %s", e.code, err_content[:300])
        raise ValidationError("Could not start the payment. Please try again.")
    except Exception as e:
        logger.error("Razorpay connection error: %s", e)
        raise ValidationError("Could not reach the payment provider. Please try again.")

    order_id = resp_body.get("id")
    if not order_id:
        raise ValidationError("Could not start the payment. Please try again.")

    PaymentOrder.objects.create(
        user=user,
        plan=plan,
        billing_interval=billing_interval,
        amount=amount,
        currency=plan.currency,
        billing_state=billing_state,
        provider_order_id=order_id,
    )

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
    key_secret = settings.RAZORPAY_KEY_SECRET
    if not key_secret or not signature:
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

    expected = hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@transaction.atomic
def fulfil_payment_order(order_id: str, payment_id: str, user: User | None = None) -> Subscription:
    """
    Marks a server-side order as paid and activates the plan recorded on it.
    Each order (and each payment id) can only be used once.
    """
    orders = PaymentOrder.objects.select_for_update().select_related("plan", "user")
    order = orders.filter(provider_order_id=order_id).first()
    if order is None or (user is not None and order.user_id != user.id):
        raise ValidationError("Payment order not found.")
    if order.status == PaymentOrder.STATUS_PAID:
        if order.provider_payment_id == payment_id:
            return order.user.subscription
        raise ValidationError("This order has already been paid.")
    if PaymentOrder.objects.filter(provider_payment_id=payment_id).exclude(id=order.id).exists():
        raise ValidationError("This payment has already been used.")

    order.status = PaymentOrder.STATUS_PAID
    order.provider_payment_id = payment_id
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "provider_payment_id", "paid_at"])

    return activate_subscription(order)


def activate_subscription(order: PaymentOrder) -> Subscription:
    """
    Activates or renews a user's subscription for a paid order and synchronizes their
    storage quota limit. Renewing the same plan before it ends extends the current period.
    """
    user = order.user
    plan = order.plan
    duration_days = 365 if order.billing_interval == "yearly" else 30
    now = timezone.now()

    existing = Subscription.objects.select_for_update().filter(user=user).first()
    period_start = now
    if (
        existing
        and existing.plan_id == plan.id
        and existing.status in ("active", "extended", "trialing")
        and existing.current_period_end
        and existing.current_period_end > now
    ):
        period_start = existing.current_period_end
    period_end = period_start + timedelta(days=duration_days)

    subscription, _ = Subscription.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan,
            "provider": "razorpay",
            "provider_subscription_id": order.provider_order_id,
            "status": "active",
            "billing_interval": order.billing_interval,
            "current_period_start": now if period_start == now else existing.current_period_start,
            "current_period_end": period_end,
            "cancel_at_period_end": False,
            "grace_period_ends_at": None,
        },
    )

    quota, _ = StorageQuota.objects.select_for_update().get_or_create(user=user)
    quota.bytes_limit = plan.storage_bytes
    quota.save(update_fields=["bytes_limit"])

    Invoice.objects.create(
        subscription=subscription,
        provider_invoice_id=order.provider_order_id,
        provider_payment_id=order.provider_payment_id or "",
        amount=order.amount,
        currency=order.currency,
        status="paid",
        issued_at=now,
        plan_name=plan.name,
        billing_interval=order.billing_interval,
        place_of_supply=order.billing_state,
    )

    AuditLog.objects.create(
        user=user,
        action="subscription.activated",
        target_type="subscription",
        target_id=str(subscription.id),
        metadata={"plan": plan.code, "amount": str(order.amount), "currency": order.currency, "order_id": order.provider_order_id},
    )

    return subscription


@transaction.atomic
def process_webhook_event(payload: dict, event_id: str) -> bool:
    """
    Idempotent webhook processor for signed Razorpay events. A captured payment for a
    known order activates the subscription even if the browser never called /verify.
    """
    if not event_id:
        event_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    if PaymentEvent.objects.filter(provider_event_id=event_id).exists():
        return True  # Already processed idempotently

    event_type = payload.get("event", "")

    PaymentEvent.objects.create(
        provider="razorpay",
        provider_event_id=event_id,
        event_type=event_type,
        payload=payload,
        status="processed",
    )

    entity = payload.get("payload", {}).get("payment", {}).get("entity", {}) or {}
    order_id = entity.get("order_id")
    payment_id = entity.get("id")
    if not order_id or not payment_id:
        return True

    if event_type in ("payment.captured", "order.paid"):
        order = PaymentOrder.objects.filter(provider_order_id=order_id).first()
        if order and order.status != PaymentOrder.STATUS_PAID and int(entity.get("amount", 0)) == int(order.amount * 100):
            fulfil_payment_order(order_id, payment_id)
    elif event_type == "payment.failed":
        PaymentOrder.objects.filter(provider_order_id=order_id, status=PaymentOrder.STATUS_CREATED).update(
            status=PaymentOrder.STATUS_FAILED
        )

    return True


def purge_user_vault_data(user: User) -> int:
    """
    Permanently deletes all encrypted vault files and folders for a user
    whose 90-day data retention window has lapsed without subscription renewal.
    Reclaims storage quota completely. Also deletes upstream SpaceByte entries.
    """
    from apps.storage.models import Node
    from apps.storage.services import delete_spacebyte_entries_for_nodes

    nodes = list(Node.objects.filter(owner=user).only("id", "spacebyte_entry_id", "type"))
    delete_spacebyte_entries_for_nodes(nodes, delete_forever=True)
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

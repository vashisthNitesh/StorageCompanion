import pytest
from apps.billing.models import Plan, Subscription, PaymentEvent
from apps.storage.models import StorageQuota


@pytest.mark.django_db
def test_webhook_idempotency(api_client, subscribed_user):
    event_id = "evt_test_unique_998877"
    payload = {
        "event_id": event_id,
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_123",
                    "email": subscribed_user.email,
                    "amount": 19900,
                }
            }
        },
    }

    # First call
    res1 = api_client.post("/api/v1/webhooks/razorpay", payload, format="json")
    assert res1.status_code == 200
    assert PaymentEvent.objects.filter(provider_event_id=event_id).count() == 1

    # Second duplicate call
    res2 = api_client.post("/api/v1/webhooks/razorpay", payload, format="json")
    assert res2.status_code == 200
    # Still only 1 record created due to idempotency
    assert PaymentEvent.objects.filter(provider_event_id=event_id).count() == 1


@pytest.mark.django_db
def test_subscription_activation_syncs_quota(auth_client, subscribed_user):
    new_plan = Plan.objects.create(
        code="test_business_plan",
        name="Business Plan Test",
        storage_bytes=500 * 1024 * 1024,  # 500 MB
        price_monthly=499.00,
        price_yearly=4999.00,
        currency="INR",
        max_file_size=100 * 1024 * 1024,
        is_active=True,
    )

    verify_payload = {
        "plan_code": "test_business_plan",
        "razorpay_payment_id": "pay_test_abc123",
        "razorpay_order_id": "order_test_xyz789",
        "razorpay_signature": "mock_valid_signature",
        "billing_interval": "monthly",
    }

    res = auth_client.post("/api/v1/subscription/verify", verify_payload, format="json")
    assert res.status_code == 200

    subscribed_user.refresh_from_db()
    sub = subscribed_user.subscription
    assert sub.plan.code == "test_business_plan"
    assert sub.status == "active"

    quota = StorageQuota.objects.get(user=subscribed_user)
    assert quota.bytes_limit == 500 * 1024 * 1024


@pytest.mark.django_db
def test_process_expired_subscriptions_lifecycle(subscribed_user):
    from datetime import timedelta
    from django.utils import timezone
    from django.core.management import call_command
    from apps.billing.services import process_expired_subscriptions
    from apps.accounts.models import User

    now = timezone.now()

    # User 1: lapsed active subscription without explicit cancellation -> grace period
    sub1 = subscribed_user.subscription
    sub1.current_period_end = now - timedelta(days=1)
    sub1.cancel_at_period_end = False
    sub1.save()

    # User 2: lapsed active subscription with cancel_at_period_end -> canceled & quota reclaimed
    user2 = User.objects.create_user(email="user2@example.com", password="Password123!")
    quota2 = StorageQuota.objects.create(user=user2, bytes_used=10 * 1024 * 1024, bytes_limit=100 * 1024 * 1024)
    sub2 = Subscription.objects.create(
        user=user2,
        plan=sub1.plan,
        status="active",
        current_period_start=now - timedelta(days=31),
        current_period_end=now - timedelta(days=1),
        cancel_at_period_end=True,
    )

    # User 3: in grace period that has expired -> expired & unused quota reclaimed
    user3 = User.objects.create_user(email="user3@example.com", password="Password123!")
    quota3 = StorageQuota.objects.create(user=user3, bytes_used=25 * 1024 * 1024, bytes_limit=100 * 1024 * 1024)
    sub3 = Subscription.objects.create(
        user=user3,
        plan=sub1.plan,
        status="grace_period",
        current_period_start=now - timedelta(days=45),
        current_period_end=now - timedelta(days=16),
        grace_period_ends_at=now - timedelta(hours=2),
    )

    # Run expiration processor
    summary = process_expired_subscriptions()
    assert summary["transitioned_to_grace_period"] == 1
    assert summary["transitioned_to_canceled"] == 1
    assert summary["transitioned_to_expired"] == 1

    sub1.refresh_from_db()
    assert sub1.status == "grace_period"
    assert sub1.grace_period_ends_at is not None
    assert sub1.can_upload is False

    sub2.refresh_from_db()
    assert sub2.status == "canceled"
    quota2.refresh_from_db()
    # Unused quota was reclaimed, but actual files (10 MB) are preserved!
    assert quota2.bytes_limit == 10 * 1024 * 1024
    assert quota2.bytes_used == 10 * 1024 * 1024

    sub3.refresh_from_db()
    assert sub3.status == "expired"
    quota3.refresh_from_db()
    # Files preserved (25 MB), unused quota returned to pool
    assert quota3.bytes_limit == 25 * 1024 * 1024
    assert quota3.bytes_used == 25 * 1024 * 1024

    # Also test the management command executes cleanly
    call_command("process_expired_subscriptions")


@pytest.mark.django_db
def test_grace_period_blocks_upload_preserves_download(auth_client, subscribed_user):
    from datetime import timedelta
    from django.utils import timezone

    now = timezone.now()
    sub = subscribed_user.subscription
    sub.status = "grace_period"
    sub.grace_period_ends_at = now + timedelta(days=10)
    sub.save()

    # 1. Upload must be blocked with ACCOUNT_IN_GRACE_PERIOD
    payload = {
        "encrypted_name": "ZW5jcnlwdGVkX2ZpbGU=",
        "name_nonce": "1122334455667788",
        "size_bytes": 1024,
    }
    res = auth_client.post("/api/v1/uploads", payload, format="json")
    assert res.status_code == 402
    assert res.data.get("code") == "ACCOUNT_IN_GRACE_PERIOD"

    # 2. Quota endpoint reflects grace period and blocks upload
    quota_res = auth_client.get("/api/v1/quota")
    assert quota_res.status_code == 200
    assert quota_res.data["can_upload"] is False
    assert quota_res.data["subscription_status"] == "grace_period"
    assert quota_res.data["is_in_grace_period"] is True


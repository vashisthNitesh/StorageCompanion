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

import hashlib
import hmac
import json
from unittest import mock

import pytest
from django.test import override_settings

from apps.billing.models import Plan, Subscription


@pytest.fixture
def big_plan(db):
    return Plan.objects.create(
        code="big", name="Big", storage_bytes=10 * 1024**3, price_monthly=999, price_yearly=9999,
        currency="INR", max_file_size=1024**3, is_active=True,
    )


def verify(client, **overrides):
    payload = {
        "plan_code": "test_personal",
        "billing_interval": "monthly",
        "razorpay_payment_id": "pay_1",
        "razorpay_order_id": "order_mock_test_personal_monthly_1",
        "razorpay_signature": "mock_signature_approved",
    }
    payload.update(overrides)
    return client.post("/api/v1/subscription/verify", payload, format="json")


@pytest.mark.django_db
def test_forged_signature_with_sample_secret_rejected(auth_client, big_plan):
    res = verify(auth_client, plan_code="big", razorpay_order_id="order_real_123", razorpay_signature="deadbeef")
    assert res.status_code == 400


@pytest.mark.django_db
def test_mock_order_cannot_claim_other_plan_or_interval(auth_client, big_plan):
    assert verify(auth_client, plan_code="big").status_code == 400
    assert verify(auth_client, billing_interval="yearly").status_code == 400


@pytest.mark.django_db
def test_payment_replay_rejected(auth_client, subscribed_user):
    assert verify(auth_client).status_code == 200
    assert verify(auth_client).status_code == 400
    assert verify(auth_client, razorpay_payment_id="pay_2").status_code == 400  # same order id


@pytest.mark.django_db
@override_settings(PAYMENTS_MOCK_MODE=False)
def test_mock_payments_disabled_outside_mock_mode(auth_client, subscribed_user):
    assert verify(auth_client).status_code == 400
    res = auth_client.post("/api/v1/subscription/checkout", {"plan_code": "test_personal"}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
@override_settings(RAZORPAY_KEY_ID="rzp_test_real", RAZORPAY_KEY_SECRET="real_secret")
def test_real_signature_bound_to_order_plan(auth_client, subscribed_user, big_plan):
    order_id, pay_id = "order_ABC", "pay_XYZ"
    sig = hmac.new(b"real_secret", f"{order_id}|{pay_id}".encode(), hashlib.sha256).hexdigest()
    order = {"id": order_id, "amount": 19900, "status": "paid",
             "notes": {"user_id": str(subscribed_user.id), "plan_code": "test_personal", "billing_interval": "monthly"}}
    with mock.patch("apps.billing.services.fetch_razorpay_order", return_value=order):
        # paid for test_personal, tries to claim "big"
        assert verify(auth_client, plan_code="big", razorpay_order_id=order_id, razorpay_payment_id=pay_id,
                      razorpay_signature=sig).status_code == 400
        res = verify(auth_client, razorpay_order_id=order_id, razorpay_payment_id=pay_id, razorpay_signature=sig)
        assert res.status_code == 200
    assert Subscription.objects.get(user=subscribed_user).plan.code == "test_personal"


@pytest.mark.django_db
def test_unsigned_webhook_rejected(api_client, subscribed_user):
    payload = {"event": "payment.failed", "id": "evt_1",
               "payload": {"payment": {"entity": {"email": subscribed_user.email}}}}
    res = api_client.post("/api/v1/webhooks/razorpay", payload, format="json")
    assert res.status_code == 400
    subscribed_user.subscription.refresh_from_db()
    assert subscribed_user.subscription.status == "active"


@pytest.mark.django_db
@override_settings(PAYMENTS_MOCK_MODE=False)
def test_sample_webhook_secret_rejected_outside_mock_mode(api_client, subscribed_user):
    body = json.dumps({"event": "payment.failed", "id": "evt_2"})
    sig = hmac.new(b"sample_webhook_secret", body.encode(), hashlib.sha256).hexdigest()
    res = api_client.post("/api/v1/webhooks/razorpay", body, content_type="application/json",
                          HTTP_X_RAZORPAY_SIGNATURE=sig)
    assert res.status_code == 400

"""Double-charge / duplicate-activation protections across checkout, /verify and the webhook."""
import hashlib
import hmac
import json
from datetime import timedelta
from unittest import mock

import pytest
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

from apps.billing.models import CheckoutOrder, Invoice, Plan, Subscription


@pytest.fixture
def smart_plan(db):
    return Plan.objects.create(code="smart", name="Smart", storage_bytes=100 * 1024**3, price_monthly=89,
                               price_yearly=890, currency="INR", max_file_size=1024**3, is_active=True)


def checkout(client, plan_code="test_personal", interval="monthly"):
    res = client.post("/api/v1/subscription/checkout", {"plan_code": plan_code, "billing_interval": interval}, format="json")
    assert res.status_code == 200, res.data
    return res.data


def verify(client, order_id, payment_id="pay_1", plan_code="test_personal"):
    return client.post("/api/v1/subscription/verify", {
        "plan_code": plan_code, "billing_interval": "monthly", "razorpay_payment_id": payment_id,
        "razorpay_order_id": order_id, "razorpay_signature": "mock_signature_approved"}, format="json")


def webhook(client, event_id, order_id, payment_id="pay_1", amount=19900, event="payment.captured"):
    body = json.dumps({"entity": "event", "event": event, "payload": {"payment": {"entity": {
        "id": payment_id, "order_id": order_id, "amount": amount, "status": "captured"}}}})
    sig = hmac.new(b"sample_webhook_secret", body.encode(), hashlib.sha256).hexdigest()
    return client.post("/api/v1/webhooks/razorpay", body, content_type="application/json",
                       HTTP_X_RAZORPAY_SIGNATURE=sig, HTTP_X_RAZORPAY_EVENT_ID=event_id)


@pytest.mark.django_db
def test_repeated_checkout_reuses_pending_order(auth_client, smart_plan):
    a = checkout(auth_client)
    b = checkout(auth_client)
    assert a["order_id"] == b["order_id"]  # double click / retry -> same payable order
    c = checkout(auth_client, plan_code="smart")
    assert c["order_id"] != a["order_id"]
    assert CheckoutOrder.objects.count() == 2


@pytest.mark.django_db
def test_paid_order_is_not_reused(auth_client, subscribed_user):
    a = checkout(auth_client)
    assert verify(auth_client, a["order_id"]).status_code == 200
    assert checkout(auth_client)["order_id"] != a["order_id"]


@pytest.mark.django_db
def test_verify_and_webhook_for_same_payment_create_one_invoice(auth_client, api_client, subscribed_user):
    order_id = checkout(auth_client)["order_id"]
    assert verify(auth_client, order_id).status_code == 200
    end = Subscription.objects.get(user=subscribed_user).current_period_end
    assert webhook(api_client, "evt_1", order_id).status_code == 200
    assert webhook(api_client, "evt_1", order_id).status_code == 200  # redelivery
    assert webhook(api_client, "evt_2", order_id, event="order.paid").status_code == 200  # 2nd event type
    assert Invoice.objects.filter(subscription__user=subscribed_user).count() == 1
    assert Subscription.objects.get(user=subscribed_user).current_period_end == end


@pytest.mark.django_db
def test_webhook_activates_when_browser_never_verified(auth_client, api_client, subscribed_user, smart_plan):
    order_id = checkout(auth_client, plan_code="smart")["order_id"]
    assert webhook(api_client, "evt_9", order_id, payment_id="pay_9", amount=8900).status_code == 200
    sub = Subscription.objects.get(user=subscribed_user)
    assert sub.plan.code == "smart"
    # The late /verify for the same payment is a no-op, not a second activation
    assert verify(auth_client, order_id, payment_id="pay_9", plan_code="smart").status_code == 200
    assert Invoice.objects.filter(subscription__user=subscribed_user).count() == 1
    assert CheckoutOrder.objects.get(provider_order_id=order_id).status == "paid"


@pytest.mark.django_db
def test_webhook_amount_mismatch_ignored(auth_client, api_client, subscribed_user, smart_plan):
    order_id = checkout(auth_client, plan_code="smart")["order_id"]
    webhook(api_client, "evt_x", order_id, payment_id="pay_x", amount=100)
    assert Subscription.objects.get(user=subscribed_user).plan.code == "test_personal"


@pytest.mark.django_db
def test_failed_payment_attempt_does_not_downgrade_active_plan(api_client, subscribed_user):
    body = json.dumps({"event": "payment.failed", "payload": {"payment": {"entity": {
        "id": "pay_f", "email": subscribed_user.email}}}})
    sig = hmac.new(b"sample_webhook_secret", body.encode(), hashlib.sha256).hexdigest()
    api_client.post("/api/v1/webhooks/razorpay", body, content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=sig, HTTP_X_RAZORPAY_EVENT_ID="evt_f")
    assert Subscription.objects.get(user=subscribed_user).status == "active"


@pytest.mark.django_db
def test_events_without_body_id_are_not_all_dropped(auth_client, api_client, subscribed_user, smart_plan):
    from apps.billing.models import PaymentEvent

    o1 = checkout(auth_client)["order_id"]
    webhook(api_client, "evt_a", o1, payment_id="pay_a")
    o2 = checkout(auth_client, plan_code="smart")["order_id"]
    webhook(api_client, "evt_b", o2, payment_id="pay_b", amount=8900)
    assert PaymentEvent.objects.count() == 2
    assert Subscription.objects.get(user=subscribed_user).plan.code == "smart"


@pytest.mark.django_db
def test_same_plan_renewal_extends_from_current_end(auth_client, subscribed_user):
    sub = Subscription.objects.get(user=subscribed_user)
    sub.current_period_end = timezone.now() + timedelta(days=10)
    sub.save()
    old_end = sub.current_period_end
    order_id = checkout(auth_client)["order_id"]
    assert verify(auth_client, order_id).status_code == 200
    sub.refresh_from_db()
    assert abs((sub.current_period_end - (old_end + timedelta(days=30))).total_seconds()) < 5


@pytest.mark.django_db
def test_db_rejects_duplicate_payment_invoice(subscribed_user):
    sub = Subscription.objects.get(user=subscribed_user)
    Invoice.objects.create(subscription=sub, provider_payment_id="pay_dup", provider_invoice_id="order_1", amount=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(subscription=sub, provider_payment_id="pay_dup", provider_invoice_id="order_2", amount=1)
    # Blank ids (e.g. admin-created) are still allowed many times
    Invoice.objects.create(subscription=sub, amount=1)
    Invoice.objects.create(subscription=sub, amount=1)


@pytest.mark.django_db
@override_settings(RAZORPAY_KEY_ID="rzp_test_real", RAZORPAY_KEY_SECRET="real_secret")
def test_real_payment_must_be_captured_for_the_order(auth_client, subscribed_user):
    order_id, pay_id = "order_REAL1", "pay_REAL1"
    CheckoutOrder.objects.create(user=subscribed_user, plan=subscribed_user.subscription.plan,
                                 provider_order_id=order_id, amount_paise=19900)
    sig = hmac.new(b"real_secret", f"{order_id}|{pay_id}".encode(), hashlib.sha256).hexdigest()
    order = {"id": order_id, "amount": 19900, "status": "attempted",
             "notes": {"user_id": str(subscribed_user.id), "plan_code": "test_personal", "billing_interval": "monthly"}}
    for payment in ({"order_id": order_id, "status": "failed", "amount": 19900},
                    {"order_id": "order_OTHER", "status": "captured", "amount": 19900}):
        with mock.patch("apps.billing.services.fetch_razorpay_order", return_value=order), \
                mock.patch("apps.billing.services.fetch_razorpay_payment", return_value=payment):
            res = auth_client.post("/api/v1/subscription/verify", {
                "plan_code": "test_personal", "billing_interval": "monthly", "razorpay_payment_id": pay_id,
                "razorpay_order_id": order_id, "razorpay_signature": sig}, format="json")
            assert res.status_code == 400
    assert not Invoice.objects.exists()

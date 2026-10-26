import hashlib
import hmac
import json
from decimal import Decimal
from unittest import mock

import pytest
from django.test import override_settings

from apps.billing.models import Invoice, Plan, PaymentEvent, PaymentOrder, Subscription
from apps.storage.models import StorageQuota

KEY_SECRET = "unit_test_key_secret"
WEBHOOK_SECRET = "unit_test_webhook_secret"


def sign_payment(order_id: str, payment_id: str) -> str:
    return hmac.new(KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def sign_webhook(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def fake_razorpay_order(order_id: str):
    response = mock.MagicMock()
    response.read.return_value = json.dumps({"id": order_id}).encode()
    response.__enter__.return_value = response
    return mock.patch("apps.billing.services.urllib.request.urlopen", return_value=response)


@pytest.fixture
def mega_plan(db):
    return Plan.objects.create(
        code="mega_test",
        name="Mega Test",
        storage_bytes=1000 * 1024 * 1024 * 1024,
        price_monthly=Decimal("449.00"),
        currency="INR",
        max_file_size=100 * 1024 * 1024 * 1024,
        is_active=True,
    )


@pytest.fixture
def business_plan(db):
    return Plan.objects.create(
        code="test_business_plan",
        name="Business Plan Test",
        storage_bytes=500 * 1024 * 1024,
        price_monthly=Decimal("499.00"),
        currency="INR",
        max_file_size=100 * 1024 * 1024,
        is_active=True,
    )


def checkout(client, plan_code: str, order_id: str, **extra):
    with fake_razorpay_order(order_id):
        res = client.post(
            "/api/v1/subscription/checkout",
            {"plan_code": plan_code, "billing_interval": "monthly", **extra},
            format="json",
        )
    assert res.status_code == 200, res.content
    return res


@pytest.mark.django_db
def test_paid_order_activates_the_plan_on_the_order(auth_client, subscribed_user, business_plan):
    checkout(auth_client, "test_business_plan", "order_biz_1")
    res = auth_client.post(
        "/api/v1/subscription/verify",
        {
            "razorpay_order_id": "order_biz_1",
            "razorpay_payment_id": "pay_biz_1",
            "razorpay_signature": sign_payment("order_biz_1", "pay_biz_1"),
        },
        format="json",
    )
    assert res.status_code == 200, res.content

    subscribed_user.refresh_from_db()
    assert subscribed_user.subscription.plan.code == "test_business_plan"
    assert StorageQuota.objects.get(user=subscribed_user).bytes_limit == 500 * 1024 * 1024
    invoice = Invoice.objects.get(provider_payment_id="pay_biz_1")
    assert invoice.amount == Decimal("499.00")


@pytest.mark.django_db
def test_fake_signature_is_rejected(auth_client, subscribed_user, mega_plan):
    checkout(auth_client, "mega_test", "order_mega_1")
    res = auth_client.post(
        "/api/v1/subscription/verify",
        {"razorpay_order_id": "order_mega_1", "razorpay_payment_id": "pay_fake", "razorpay_signature": "mock_signature_approved"},
        format="json",
    )
    assert res.status_code == 400
    subscribed_user.refresh_from_db()
    assert subscribed_user.subscription.plan.code != "mega_test"


@pytest.mark.django_db
def test_browser_cannot_upgrade_a_cheap_order_to_mega(auth_client, subscribed_user, sample_plan, mega_plan):
    checkout(auth_client, sample_plan.code, "order_cheap_1")
    res = auth_client.post(
        "/api/v1/subscription/verify",
        {
            "plan_code": "mega_test",  # ignored: the plan comes from the order
            "razorpay_order_id": "order_cheap_1",
            "razorpay_payment_id": "pay_cheap_1",
            "razorpay_signature": sign_payment("order_cheap_1", "pay_cheap_1"),
        },
        format="json",
    )
    assert res.status_code == 200
    subscribed_user.refresh_from_db()
    assert subscribed_user.subscription.plan.code == sample_plan.code


@pytest.mark.django_db
def test_unknown_order_is_rejected(auth_client):
    res = auth_client.post(
        "/api/v1/subscription/verify",
        {
            "razorpay_order_id": "order_never_created",
            "razorpay_payment_id": "pay_x",
            "razorpay_signature": sign_payment("order_never_created", "pay_x"),
        },
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_one_payment_cannot_be_reused(auth_client, subscribed_user, business_plan):
    from tests.conftest import bearer_client_for
    from apps.accounts.models import User

    checkout(auth_client, "test_business_plan", "order_reuse_1")
    body = {
        "razorpay_order_id": "order_reuse_1",
        "razorpay_payment_id": "pay_reuse_1",
        "razorpay_signature": sign_payment("order_reuse_1", "pay_reuse_1"),
    }
    assert auth_client.post("/api/v1/subscription/verify", body, format="json").status_code == 200
    # Replaying it is idempotent and does not create a second invoice
    assert auth_client.post("/api/v1/subscription/verify", body, format="json").status_code == 200
    assert Invoice.objects.filter(provider_payment_id="pay_reuse_1").count() == 1

    # Another user cannot use the same order/payment
    other = User.objects.create_user(email="other@example.com", password="OtherPassword123!")
    res = bearer_client_for(other).post("/api/v1/subscription/verify", body, format="json")
    assert res.status_code == 400
    assert not Subscription.objects.filter(user=other).exists()

    # The same payment id cannot pay for a second order
    checkout(auth_client, "test_business_plan", "order_reuse_2")
    res = auth_client.post(
        "/api/v1/subscription/verify",
        {
            "razorpay_order_id": "order_reuse_2",
            "razorpay_payment_id": "pay_reuse_1",
            "razorpay_signature": sign_payment("order_reuse_2", "pay_reuse_1"),
        },
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
@override_settings(RAZORPAY_KEY_ID="", RAZORPAY_KEY_SECRET="")
def test_checkout_refused_without_razorpay_keys(auth_client, sample_plan):
    res = auth_client.post("/api/v1/subscription/checkout", {"plan_code": sample_plan.code}, format="json")
    assert res.status_code == 503


@pytest.mark.django_db
def test_unsigned_webhook_is_rejected(api_client):
    res = api_client.post("/api/v1/webhooks/razorpay", {"event": "payment.captured"}, format="json")
    assert res.status_code == 400
    assert PaymentEvent.objects.count() == 0


@pytest.mark.django_db
@override_settings(RAZORPAY_WEBHOOK_SECRET="")
def test_webhook_refused_without_secret(api_client):
    res = api_client.post("/api/v1/webhooks/razorpay", {"event": "payment.captured"}, format="json")
    assert res.status_code == 503


@pytest.mark.django_db
def test_signed_webhook_is_idempotent_and_fulfils_order(api_client, auth_client, subscribed_user, business_plan):
    checkout(auth_client, "test_business_plan", "order_wh_1")
    payload = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_wh_1", "order_id": "order_wh_1", "amount": 49900}}},
    }
    body = json.dumps(payload).encode()
    headers = {"HTTP_X_RAZORPAY_SIGNATURE": sign_webhook(body), "HTTP_X_RAZORPAY_EVENT_ID": "evt_1"}

    res1 = api_client.post("/api/v1/webhooks/razorpay", body, content_type="application/json", **headers)
    assert res1.status_code == 200
    res2 = api_client.post("/api/v1/webhooks/razorpay", body, content_type="application/json", **headers)
    assert res2.status_code == 200
    assert PaymentEvent.objects.filter(provider_event_id="evt_1").count() == 1
    assert PaymentOrder.objects.get(provider_order_id="order_wh_1").status == PaymentOrder.STATUS_PAID
    subscribed_user.refresh_from_db()
    assert subscribed_user.subscription.plan.code == "test_business_plan"


@pytest.mark.django_db
def test_invoice_escapes_user_data_and_is_tax_inclusive(auth_client, subscribed_user, business_plan):
    subscribed_user.full_name = '<script>alert("x")</script>'
    subscribed_user.save()
    checkout(auth_client, "test_business_plan", "order_inv_1")
    auth_client.post(
        "/api/v1/subscription/verify",
        {
            "razorpay_order_id": "order_inv_1",
            "razorpay_payment_id": "pay_inv_1",
            "razorpay_signature": sign_payment("order_inv_1", "pay_inv_1"),
        },
        format="json",
    )
    invoice = Invoice.objects.get(provider_payment_id="pay_inv_1")
    html = auth_client.get(f"/api/v1/invoices/{invoice.id}/download").content.decode()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Inclusive of all taxes" in html
    assert "₹499.00" in html
    assert "GST" not in html


@pytest.mark.django_db
def test_legacy_invoice_with_place_of_supply_still_renders(auth_client, subscribed_user):
    invoice = Invoice.objects.create(
        subscription=subscribed_user.subscription,
        amount=Decimal("1490.00"),
        plan_name="Value Pack",
        billing_interval="yearly",
        place_of_supply="27",
    )
    res = auth_client.get(f"/api/v1/invoices/{invoice.id}/download")
    assert res.status_code == 200
    html = res.content.decode()
    assert "₹1,490.00" in html and "Annual (12 months)" in html and "Inclusive of all taxes" in html


@pytest.mark.django_db
def test_process_expired_subscriptions_lifecycle(subscribed_user):
    from datetime import timedelta
    from django.utils import timezone
    from django.core.management import call_command
    from apps.billing.services import process_expired_subscriptions
    from apps.accounts.models import User

    now = timezone.now()

    sub1 = subscribed_user.subscription
    sub1.current_period_end = now - timedelta(days=1)
    sub1.cancel_at_period_end = False
    sub1.save()

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

    summary = process_expired_subscriptions()
    assert summary["transitioned_to_grace_period"] == 1
    assert summary["transitioned_to_canceled"] == 1
    assert summary["transitioned_to_expired"] == 1

    sub1.refresh_from_db()
    assert sub1.status in ["expired", "grace_period"]
    assert sub1.can_upload is False

    sub2.refresh_from_db()
    assert sub2.status == "canceled"
    quota2.refresh_from_db()
    assert quota2.bytes_limit == 10 * 1024 * 1024
    assert quota2.bytes_used == 10 * 1024 * 1024

    sub3.refresh_from_db()
    assert sub3.status in ["expired", "purged"]
    quota3.refresh_from_db()
    assert quota3.bytes_limit in [0, 25 * 1024 * 1024]

    call_command("process_expired_subscriptions")


@pytest.mark.django_db
def test_grace_period_blocks_upload(auth_client, subscribed_user):
    from datetime import timedelta
    from django.utils import timezone

    sub = subscribed_user.subscription
    sub.status = "grace_period"
    sub.grace_period_ends_at = timezone.now() + timedelta(days=10)
    sub.save()

    res = auth_client.post(
        "/api/v1/uploads",
        {"encrypted_name": "ZW5j", "name_nonce": "1122334455667788", "size_bytes": 1024},
        format="json",
    )
    assert res.status_code == 402
    assert res.data.get("code") == "ACCOUNT_IN_GRACE_PERIOD"

    quota_res = auth_client.get("/api/v1/quota")
    assert quota_res.status_code == 200
    assert quota_res.data["can_upload"] is False
    assert quota_res.data["subscription_status"] == "grace_period"
    assert quota_res.data["is_in_grace_period"] is True

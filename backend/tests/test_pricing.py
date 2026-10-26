"""Pricing: yearly = monthly x 10, the server decides every amount, and nothing is added at checkout."""
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone

from apps.billing.models import Invoice, PaymentOrder, Plan
from tests.test_billing_webhooks import sign_payment


@pytest.fixture
def value_plan(db):
    return Plan.objects.create(
        code="value_test",
        name="Value Test",
        storage_bytes=200 * 1024**3,
        price_monthly=Decimal("149.00"),
        currency="INR",
        max_file_size=25 * 1024**3,
        is_active=True,
    )


def start_checkout(client, body, order_id="order_price_1"):
    """Posts to checkout with Razorpay mocked; returns (response, payload sent to Razorpay)."""
    sent = {}
    response = mock.MagicMock()
    response.read.return_value = json.dumps({"id": order_id}).encode()
    response.__enter__.return_value = response

    def fake_urlopen(req, timeout=None):
        sent.update(json.loads(req.data.decode()))
        return response

    with mock.patch("apps.billing.services.urllib.request.urlopen", side_effect=fake_urlopen):
        res = client.post("/api/v1/subscription/checkout", body, format="json")
    return res, sent


@pytest.mark.django_db
def test_yearly_price_is_always_ten_months(value_plan):
    assert value_plan.price_yearly == Decimal("1490.00")
    assert value_plan.price_for("yearly") == Decimal("1490.00")
    assert value_plan.price_for("monthly") == Decimal("149.00")

    value_plan.price_monthly = Decimal("199.00")
    value_plan.save(update_fields=["price_monthly"])
    value_plan.refresh_from_db()
    assert value_plan.price_yearly == Decimal("1990.00")


@pytest.mark.django_db
def test_plans_api_exposes_monthly_and_derived_yearly(api_client, value_plan):
    plan = next(p for p in api_client.get("/api/v1/plans").json() if p["code"] == "value_test")
    assert plan["price_monthly"] == "149.00"
    assert plan["price_yearly"] == "1490.00"
    assert plan["yearly_paid_months"] == 10


@pytest.mark.django_db
def test_yearly_checkout_charges_exactly_ten_months(auth_client, subscribed_user, value_plan):
    res, sent = start_checkout(auth_client, {"plan_code": "value_test", "billing_interval": "yearly"})
    assert res.status_code == 200, res.content
    assert sent["amount"] == 149000  # paise: 149 x 10 x 100
    assert res.json()["amount"] == 149000
    order = PaymentOrder.objects.get(provider_order_id="order_price_1")
    assert order.amount == Decimal("1490.00") and order.billing_interval == "yearly"


@pytest.mark.django_db
def test_monthly_checkout_charges_the_monthly_price(auth_client, subscribed_user, value_plan):
    res, sent = start_checkout(auth_client, {"plan_code": "value_test", "billing_interval": "monthly"})
    assert res.status_code == 200
    assert sent["amount"] == 14900


@pytest.mark.django_db
def test_client_sent_prices_are_ignored(auth_client, subscribed_user, value_plan):
    res, sent = start_checkout(
        auth_client,
        {"plan_code": "value_test", "billing_interval": "yearly", "amount": 1, "price": "1.00", "billing_state": "27"},
    )
    assert res.status_code == 200
    assert sent["amount"] == 149000


@pytest.mark.django_db
def test_stale_yearly_column_cannot_change_the_charge(auth_client, subscribed_user, value_plan):
    # Even if the stored column drifted (e.g. a raw SQL edit), the charge is derived from the monthly price.
    Plan.objects.filter(id=value_plan.id).update(price_yearly=Decimal("999.00"))
    res, sent = start_checkout(auth_client, {"plan_code": "value_test", "billing_interval": "yearly"})
    assert res.status_code == 200
    assert sent["amount"] == 149000


@pytest.mark.django_db
def test_unknown_billing_period_is_rejected(auth_client, value_plan):
    res, sent = start_checkout(auth_client, {"plan_code": "value_test", "billing_interval": "weekly"})
    assert res.status_code == 400
    assert not sent


@pytest.mark.django_db
def test_paid_yearly_order_gives_a_year_and_a_matching_invoice(auth_client, subscribed_user, value_plan):
    start_checkout(auth_client, {"plan_code": "value_test", "billing_interval": "yearly"}, order_id="order_y_1")
    before = timezone.now()
    res = auth_client.post(
        "/api/v1/subscription/verify",
        {"razorpay_order_id": "order_y_1", "razorpay_payment_id": "pay_y_1", "razorpay_signature": sign_payment("order_y_1", "pay_y_1")},
        format="json",
    )
    assert res.status_code == 200
    sub = subscribed_user.subscription
    sub.refresh_from_db()
    assert sub.plan_id == value_plan.id and sub.billing_interval == "yearly"
    assert sub.current_period_end - before >= timedelta(days=364)
    invoice = Invoice.objects.get(provider_payment_id="pay_y_1")
    assert invoice.amount == Decimal("1490.00") and invoice.billing_interval == "yearly"
    assert auth_client.get("/api/v1/invoices").json()[0]["amount"] == "1490.00"


@pytest.mark.django_db
def test_renewing_the_same_yearly_plan_extends_from_the_current_end(auth_client, subscribed_user, value_plan):
    for n in (1, 2):
        start_checkout(auth_client, {"plan_code": "value_test", "billing_interval": "yearly"}, order_id=f"order_r_{n}")
        auth_client.post(
            "/api/v1/subscription/verify",
            {"razorpay_order_id": f"order_r_{n}", "razorpay_payment_id": f"pay_r_{n}", "razorpay_signature": sign_payment(f"order_r_{n}", f"pay_r_{n}")},
            format="json",
        )
    sub = subscribed_user.subscription
    sub.refresh_from_db()
    assert sub.current_period_end - timezone.now() >= timedelta(days=729)
    assert list(Invoice.objects.filter(subscription=sub, provider_payment_id__startswith="pay_r_").values_list("amount", flat=True)) == [
        Decimal("1490.00"),
        Decimal("1490.00"),
    ]


@pytest.mark.django_db
def test_webhook_with_a_different_amount_does_not_activate(api_client, auth_client, subscribed_user, value_plan):
    from tests.test_billing_webhooks import sign_webhook

    start_checkout(auth_client, {"plan_code": "value_test", "billing_interval": "yearly"}, order_id="order_wa_1")
    payload = {"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_wa_1", "order_id": "order_wa_1", "amount": 14900}}}}
    body = json.dumps(payload).encode()
    api_client.post(
        "/api/v1/webhooks/razorpay", body, content_type="application/json",
        HTTP_X_RAZORPAY_SIGNATURE=sign_webhook(body), HTTP_X_RAZORPAY_EVENT_ID="evt_wa_1",
    )
    assert PaymentOrder.objects.get(provider_order_id="order_wa_1").status == PaymentOrder.STATUS_CREATED

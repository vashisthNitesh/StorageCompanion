from django.urls import path
from apps.billing.views import (
    PlanListView,
    SubscriptionDetailView,
    CheckoutInitView,
    PaymentVerifyView,
    SubscriptionCancelView,
    InvoiceListView,
    RazorpayWebhookView,
)

urlpatterns = [
    path("plans", PlanListView.as_view(), name="plan-list"),
    path("subscription", SubscriptionDetailView.as_view(), name="subscription-detail"),
    path("subscription/checkout", CheckoutInitView.as_view(), name="subscription-checkout"),
    path("subscription/verify", PaymentVerifyView.as_view(), name="subscription-verify"),
    path("subscription/cancel", SubscriptionCancelView.as_view(), name="subscription-cancel"),
    path("invoices", InvoiceListView.as_view(), name="invoice-list"),
    path("webhooks/razorpay", RazorpayWebhookView.as_view(), name="webhook-razorpay"),
]

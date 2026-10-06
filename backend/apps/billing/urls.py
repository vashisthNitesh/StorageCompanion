from django.urls import path

from apps.billing.views import (
    CheckoutInitView,
    InvoiceListView,
    HealthView,
    PaymentVerifyView,
    PlanListView,
    RazorpayWebhookView,
    SubscriptionCancelView,
    SubscriptionDetailView,
)

urlpatterns = [
    path("plans", PlanListView.as_view(), name="plan-list"),
    path("health", HealthView.as_view(), name="health"),
    path("subscription", SubscriptionDetailView.as_view(), name="subscription-detail"),
    path("subscription/checkout", CheckoutInitView.as_view(), name="subscription-checkout"),
    path("subscription/verify", PaymentVerifyView.as_view(), name="subscription-verify"),
    path("subscription/cancel", SubscriptionCancelView.as_view(), name="subscription-cancel"),
    path("invoices", InvoiceListView.as_view(), name="invoice-list"),
    path("webhooks/razorpay", RazorpayWebhookView.as_view(), name="webhook-razorpay"),
]

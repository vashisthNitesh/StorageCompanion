import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import BaseModel, TimeStampedModel


class Plan(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    storage_bytes = models.BigIntegerField(help_text="Storage limit in bytes")
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    max_file_size = models.BigIntegerField(help_text="Max single file size in bytes")
    version_retention_days = models.IntegerField(default=30)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price_monthly"]

    def __str__(self):
        return f"{self.name} ({self.currency} {self.price_monthly}/mo)"


class Subscription(BaseModel):
    STATUS_CHOICES = [
        ("trialing", "Trialing"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("grace_period", "Grace Period (30 days)"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    provider = models.CharField(max_length=50, default="razorpay")
    provider_subscription_id = models.CharField(max_length=255, blank=True, default="")
    provider_customer_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="active")
    billing_interval = models.CharField(max_length=20, default="monthly")  # monthly or yearly
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_in_grace_period(self):
        """Returns True if subscription is currently in an active grace period."""
        if self.status == "grace_period":
            if self.grace_period_ends_at:
                return timezone.now() <= self.grace_period_ends_at
            return True
        return False

    @property
    def is_expired(self):
        """Returns True if subscription has lapsed beyond valid billing or grace periods."""
        if self.status in ["expired", "canceled"]:
            return True
        now = timezone.now()
        if self.status == "grace_period" and self.grace_period_ends_at and now > self.grace_period_ends_at:
            return True
        if self.status in ["active", "trialing"] and self.current_period_end and now > self.current_period_end:
            return True
        return False

    @property
    def is_valid(self):
        """
        Returns True if user currently has valid storage access (active, trialing, or in grace period).
        Users in grace period have read access to protect their data without deleting.
        """
        now = timezone.now()
        if self.status in ["active", "trialing"]:
            if self.current_period_end and now > self.current_period_end:
                return False
            return True
        if self.status == "grace_period":
            if self.grace_period_ends_at and now > self.grace_period_ends_at:
                return False
            return True
        return False

    @property
    def can_upload(self):
        """
        During grace period, past due, or expired states, uploads are blocked.
        Only active/trialing subscriptions within their billing cycle can upload.
        """
        if not self.is_valid:
            return False
        if self.status not in ["active", "trialing"]:
            return False
        if self.current_period_end and timezone.now() > self.current_period_end:
            return False
        return True

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"


class Invoice(BaseModel):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    provider_invoice_id = models.CharField(max_length=255, blank=True, default="")
    provider_payment_id = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=50, default="paid")  # paid, pending, failed
    pdf_url = models.URLField(blank=True, default="")
    issued_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Invoice {self.id} - {self.subscription.user.email} ({self.currency} {self.amount})"


class PaymentEvent(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=50, default="razorpay")
    provider_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="processed")

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self):
        return f"[{self.provider}] {self.event_type} - {self.provider_event_id}"

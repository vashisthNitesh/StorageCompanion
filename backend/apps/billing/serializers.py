from rest_framework import serializers
from apps.billing.models import Plan, Subscription, Invoice


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "code",
            "name",
            "description",
            "storage_bytes",
            "price_monthly",
            "price_yearly",
            "currency",
            "max_file_size",
            "version_retention_days",
            "features",
            "is_active",
            "sort_order",
        ]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_details = PlanSerializer(source="plan", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    can_upload = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "plan_details",
            "provider",
            "status",
            "billing_interval",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "grace_period_ends_at",
            "is_valid",
            "can_upload",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            "provider_invoice_id",
            "provider_payment_id",
            "amount",
            "currency",
            "status",
            "pdf_url",
            "issued_at",
        ]
        read_only_fields = fields


class CheckoutInitSerializer(serializers.Serializer):
    plan_code = serializers.CharField()
    billing_interval = serializers.ChoiceField(choices=["monthly", "yearly"], default="monthly")


class PaymentVerifySerializer(serializers.Serializer):
    plan_code = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_order_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
    billing_interval = serializers.ChoiceField(choices=["monthly", "yearly"], default="monthly")

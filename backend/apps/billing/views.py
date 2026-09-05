from django.utils import timezone
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, ValidationError

from apps.billing.models import Plan, Subscription, Invoice
from apps.billing.serializers import (
    PlanSerializer,
    SubscriptionSerializer,
    InvoiceSerializer,
    CheckoutInitSerializer,
    PaymentVerifySerializer,
)
from apps.billing.services import (
    get_active_plans,
    create_razorpay_order,
    verify_razorpay_signature,
    activate_subscription,
    verify_webhook_signature,
    process_webhook_event,
)
from apps.audit.models import AuditLog


class PlanListView(generics.ListAPIView):
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return get_active_plans()


class SubscriptionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sub = Subscription.objects.filter(user=request.user).first()
        if not sub:
            return Response(
                {"status": "none", "is_valid": False, "message": "No active subscription found."},
                status=status.HTTP_200_OK,
            )
        return Response(SubscriptionSerializer(sub).data)


class CheckoutInitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order_data = create_razorpay_order(
            user=request.user,
            plan_code=data["plan_code"],
            billing_interval=data.get("billing_interval", "monthly"),
        )
        return Response(order_data, status=status.HTTP_200_OK)


class PaymentVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        is_valid = verify_razorpay_signature(
            payment_id=data["razorpay_payment_id"],
            order_id=data["razorpay_order_id"],
            signature=data["razorpay_signature"],
        )
        if not is_valid:
            return Response(
                {"error": "Invalid payment signature. Verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = activate_subscription(
            user=request.user,
            plan_code=data["plan_code"],
            provider_payment_id=data["razorpay_payment_id"],
            provider_order_id=data["razorpay_order_id"],
            billing_interval=data.get("billing_interval", "monthly"),
        )

        return Response(
            {
                "success": True,
                "message": "Subscription activated successfully!",
                "subscription": SubscriptionSerializer(subscription).data,
            },
            status=status.HTTP_200_OK,
        )


class SubscriptionCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        sub = Subscription.objects.filter(user=request.user, status="active").first()
        if not sub:
            raise NotFound("No active subscription to cancel.")

        sub.cancel_at_period_end = True
        sub.save(update_fields=["cancel_at_period_end"])

        AuditLog.objects.create(
            user=request.user,
            action="subscription.canceled",
            target_type="subscription",
            target_id=str(sub.id),
        )
        return Response({
            "success": True,
            "message": f"Subscription will cancel at the end of the current billing cycle on {sub.current_period_end.strftime('%Y-%m-%d')}.",
        })


class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(subscription__user=self.request.user)


class RazorpayWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature", "")
        body_bytes = request.body

        if not verify_webhook_signature(body_bytes, signature):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data
        event_id = payload.get("event_id") or payload.get("id") or request.headers.get("X-Razorpay-Event-Id", "")

        process_webhook_event(payload=payload, event_id=event_id)
        return Response({"status": "ok"}, status=status.HTTP_200_OK)

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


from django.http import HttpResponse
from django.shortcuts import get_object_or_404

class InvoiceDownloadView(APIView):
    """
    Generates a printable HTML/PDF receipt for an invoice.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, id=pk, subscription__user=request.user)
        user = request.user
        plan_name = invoice.subscription.plan.name if invoice.subscription and invoice.subscription.plan else "Storage Subscription"
        amount = float(invoice.amount)
        subtotal = round(amount / 1.18, 2)
        gst = round(amount - subtotal, 2)
        date_str = invoice.issued_at.strftime("%B %d, %Y")

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Tax Invoice #{str(invoice.id)[:8].upper()}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; margin: 0; padding: 40px; background: #fff; }}
  .container {{ max-width: 650px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #f1f5f9; padding-bottom: 24px; margin-bottom: 24px; }}
  .brand {{ font-size: 22px; font-weight: 800; color: #0f172a; }}
  .brand-sub {{ font-size: 11px; color: #64748b; font-family: monospace; }}
  .badge {{ background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; }}
  .details {{ display: flex; justify-content: space-between; margin-bottom: 24px; font-size: 13px; line-height: 1.6; }}
  .table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }}
  .table th {{ text-align: left; padding: 10px 12px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-transform: uppercase; color: #64748b; }}
  .table td {{ padding: 12px; border-bottom: 1px solid #f1f5f9; }}
  .table .amount {{ text-align: right; font-family: monospace; font-weight: 600; }}
  .summary {{ margin-left: auto; width: 240px; font-size: 13px; line-height: 1.8; }}
  .summary div {{ display: flex; justify-content: space-between; }}
  .total {{ font-weight: 800; font-size: 15px; border-top: 2px solid #e2e8f0; padding-top: 6px; margin-top: 6px; color: #0f172a; }}
  .footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #f1f5f9; text-align: center; font-size: 11px; color: #94a3b8; }}
  @media print {{ body {{ padding: 0; }} .container {{ border: none; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="brand">SmartSpace</div>
      <div class="brand-sub">smartspacedata.com • SpeedCloud Vault</div>
      <div style="font-size: 11px; color: #64748b; margin-top: 4px;">GSTIN: 07AAACS1429B1Z8</div>
    </div>
    <div style="text-align: right;">
      <span class="badge">Paid</span>
      <div style="font-size: 12px; font-weight: 600; color: #334155; margin-top: 6px;">Invoice #{str(invoice.id)[:8].upper()}</div>
      <div style="font-size: 11px; color: #64748b;">{date_str}</div>
    </div>
  </div>

  <div class="details">
    <div>
      <strong style="color: #0f172a;">Billed To:</strong><br>
      {user.full_name or 'Account Holder'}<br>
      {user.email}
    </div>
    <div style="text-align: right;">
      <strong style="color: #0f172a;">Payment Reference:</strong><br>
      Razorpay Payment ID:<br>
      <code style="font-size: 11px; color: #475569;">{invoice.provider_invoice_id}</code>
    </div>
  </div>

  <table class="table">
    <thead>
      <tr>
        <th>Description</th>
        <th class="amount">Qty</th>
        <th class="amount">Subtotal</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>{plan_name}</strong> - Zero-Knowledge Cloud Storage Subscription</td>
        <td class="amount">1</td>
        <td class="amount">₹{subtotal:.2f}</td>
      </tr>
    </tbody>
  </table>

  <div class="summary">
    <div><span>Subtotal:</span> <span class="amount">₹{subtotal:.2f}</span></div>
    <div><span>CGST (9%):</span> <span class="amount">₹{(gst/2):.2f}</span></div>
    <div><span>SGST (9%):</span> <span class="amount">₹{(gst/2):.2f}</span></div>
    <div class="total"><span>Total Paid:</span> <span>₹{amount:.2f}</span></div>
  </div>

  <div class="footer">
    Thank you for subscribing to SmartSpace Data. This is a computer-generated tax invoice.
  </div>
</div>
<script>
  if (window.location.search.includes('print=true')) {{
    window.print();
  }}
</script>
</body>
</html>"""
        response = HttpResponse(html_content, content_type="text/html; charset=utf-8")
        if request.query_params.get("download") == "true":
            response["Content-Disposition"] = f'attachment; filename="Invoice-{str(invoice.id)[:8].upper()}.html"'
        return response


import logging
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.html import escape
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from apps.billing.gst import GST_STATES, tax_breakdown
from apps.billing.models import Subscription, Invoice
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
    fulfil_payment_order,
    verify_webhook_signature,
    process_webhook_event,
)
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


class PlanListView(generics.ListAPIView):
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []
    pagination_class = None

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
            billing_state=data.get("billing_state", ""),
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

        # The plan and interval come from the server-side order, not from the request.
        subscription = fulfil_payment_order(
            order_id=data["razorpay_order_id"],
            payment_id=data["razorpay_payment_id"],
            user=request.user,
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
            "message": f"Your plan stays active until {sub.current_period_end.strftime('%d %b %Y')} and will not renew.",
        })


class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Invoice.objects.filter(subscription__user=self.request.user)


class RazorpayWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.error("Razorpay webhook received but RAZORPAY_WEBHOOK_SECRET is not configured.")
            return Response({"error": "Webhooks are not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        signature = request.headers.get("X-Razorpay-Signature", "")
        body_bytes = request.body

        if not verify_webhook_signature(body_bytes, signature):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data
        event_id = request.headers.get("X-Razorpay-Event-Id", "") or payload.get("id", "")

        process_webhook_event(payload=payload, event_id=event_id)
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class InvoiceDownloadView(APIView):
    """
    Renders a printable HTML invoice. Every value that comes from user or provider data
    is HTML-escaped, and the page runs no scripts.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, id=pk, subscription__user=request.user)
        user = request.user
        plan_name = invoice.plan_name or (invoice.subscription.plan.name if invoice.subscription.plan else "Storage plan")
        interval = {"yearly": "Annual", "monthly": "Monthly"}.get(invoice.billing_interval, "")
        seller_gstin = settings.BUSINESS_GSTIN
        seller_state = settings.BUSINESS_STATE_CODE
        taxes = tax_breakdown(Decimal(invoice.amount), seller_state, invoice.place_of_supply)
        number = str(invoice.id)[:8].upper()
        symbol = "₹" if invoice.currency == "INR" else f"{escape(invoice.currency)} "

        def money(value) -> str:
            return f"{symbol}{Decimal(value):,.2f}"

        if seller_gstin:
            title = "Tax Invoice"
            tax_rows = "".join(
                f"<div><span>{escape(label)}</span><span>{money(value)}</span></div>" for label, value in taxes["lines"]
            )
            summary = f"<div><span>Taxable value</span><span>{money(taxes['taxable'])}</span></div>{tax_rows}"
            seller_tax = f"<div>GSTIN: {escape(seller_gstin)}</div>"
        else:
            title = "Payment Receipt"
            summary = ""
            seller_tax = ""

        place = GST_STATES.get(invoice.place_of_supply, "")
        place_line = f"<div>Place of supply: {escape(place)} ({escape(invoice.place_of_supply)})</div>" if place else ""
        address = f"<div>{escape(settings.BUSINESS_ADDRESS)}</div>" if settings.BUSINESS_ADDRESS else ""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} {number}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0f172a; margin: 0; padding: 40px 16px; background: #fff; }}
  .wrap {{ max-width: 680px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; }}
  .row {{ display: flex; justify-content: space-between; gap: 24px; flex-wrap: wrap; }}
  .muted {{ color: #64748b; font-size: 12px; line-height: 1.6; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .badge {{ background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 13px; }}
  th {{ text-align: left; padding: 10px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-transform: uppercase; color: #64748b; }}
  td {{ padding: 12px 10px; border-bottom: 1px solid #f1f5f9; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .summary {{ margin-left: auto; width: 260px; font-size: 13px; line-height: 2; }}
  .summary div {{ display: flex; justify-content: space-between; }}
  .total {{ font-weight: 700; font-size: 15px; border-top: 2px solid #e2e8f0; margin-top: 4px; }}
  footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #f1f5f9; text-align: center; font-size: 11px; color: #94a3b8; }}
  @media print {{ body {{ padding: 0; }} .wrap {{ border: none; }} }}
</style>
</head>
<body>
<div class="wrap">
  <div class="row">
    <div>
      <h1>{escape(settings.BUSINESS_NAME)}</h1>
      <div class="muted">{address}{seller_tax}</div>
    </div>
    <div style="text-align:right">
      <span class="badge">Paid</span>
      <div style="font-weight:600;margin-top:8px">{title} #{number}</div>
      <div class="muted">{invoice.issued_at.strftime("%d %B %Y")}</div>
    </div>
  </div>
  <div class="row" style="margin-top:28px">
    <div class="muted"><strong style="color:#0f172a">Billed to</strong><br>{escape(user.full_name or "Account holder")}<br>{escape(user.email)}{place_line}</div>
    <div class="muted" style="text-align:right"><strong style="color:#0f172a">Payment reference</strong><br>Order: {escape(invoice.provider_invoice_id)}<br>Payment: {escape(invoice.provider_payment_id)}</div>
  </div>
  <table>
    <thead><tr><th>Description</th><th class="num">Qty</th><th class="num">Amount</th></tr></thead>
    <tbody><tr><td><strong>{escape(plan_name)}</strong> {escape(interval)} cloud storage plan</td><td class="num">1</td><td class="num">{money(taxes["taxable"] if seller_gstin else invoice.amount)}</td></tr></tbody>
  </table>
  <div class="summary">
    {summary}
    <div class="total"><span>Total paid</span><span>{money(invoice.amount)}</span></div>
  </div>
  <footer>Thank you for choosing {escape(settings.BUSINESS_NAME)}. This is a computer-generated document.</footer>
</div>
</body>
</html>"""
        response = HttpResponse(html_content, content_type="text/html; charset=utf-8")
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"
        response["Content-Disposition"] = f'attachment; filename="Invoice-{number}.html"'
        return response

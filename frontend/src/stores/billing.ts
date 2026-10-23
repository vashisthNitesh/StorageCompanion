import { defineStore } from "pinia";
import { ref } from "vue";
import { apiFetch, apiRequest, errorFromResponse } from "../lib/api";
import { useAuthStore } from "./auth";

export interface Plan {
  id: string;
  code: string;
  name: string;
  description: string;
  storage_bytes: number;
  price_monthly: string;
  price_yearly: string;
  currency: string;
  max_file_size: number;
  version_retention_days: number;
  features: string[];
  is_active: boolean;
  sort_order: number;
}

export interface Subscription {
  id: string;
  plan: string;
  plan_details: Plan;
  provider: string;
  status: string;
  billing_interval: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  grace_period_ends_at?: string | null;
  is_valid: boolean;
  can_upload: boolean;
}

export interface Invoice {
  id: string;
  provider_invoice_id: string;
  provider_payment_id: string;
  amount: string;
  currency: string;
  status: string;
  plan_name: string;
  billing_interval: string;
  issued_at: string;
}

/** The person closed the Razorpay window. */
export class PaymentCancelled extends Error {}
/** Razorpay declined or failed the payment (reason is gateway text; not shown verbatim). */
export class PaymentFailed extends Error {
  constructor(public orderId: string) {
    super("payment_failed");
  }
}

let razorpayLoader: Promise<void> | null = null;
function loadRazorpay(): Promise<void> {
  if (typeof (window as any).Razorpay === "function") return Promise.resolve();
  if (razorpayLoader) return razorpayLoader;
  razorpayLoader = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      razorpayLoader = null;
      reject(new Error("razorpay_unavailable"));
    };
    document.head.appendChild(script);
  });
  return razorpayLoader;
}

export const useBillingStore = defineStore("billing", () => {
  const authStore = useAuthStore();
  const plans = ref<Plan[]>([]);
  const plansLoaded = ref(false);
  const plansError = ref<unknown>(null);
  const currentSubscription = ref<Subscription | null>(null);
  const invoices = ref<Invoice[]>([]);

  async function fetchPlans() {
    plansError.value = null;
    try {
      plans.value = await apiRequest<Plan[]>("/api/v1/plans");
      plansLoaded.value = true;
    } catch (err) {
      plansError.value = err;
    }
  }

  async function ensurePlans() {
    if (!plansLoaded.value) await fetchPlans();
  }

  async function fetchSubscription() {
    try {
      const data = await apiRequest<Subscription>("/api/v1/subscription");
      currentSubscription.value = data.id ? data : null;
    } catch {
      currentSubscription.value = null;
    }
  }

  async function fetchInvoices() {
    invoices.value = await apiRequest<Invoice[]>("/api/v1/invoices");
  }

  /**
   * Creates the server-side order, opens Razorpay and verifies the payment.
   * Throws PaymentCancelled / PaymentFailed / ApiError.
   * Call it with no modal dialog open: a dialog's focus trap and pointer lock would
   * make the Razorpay window unclickable.
   */
  async function checkout(
    planCode: string,
    interval: "monthly" | "yearly",
    billingState: string,
    hooks: { onVerifying?: () => void } = {}
  ): Promise<void> {
    const order = await apiRequest<{
      key_id: string;
      order_id: string;
      amount: number;
      currency: string;
      plan_name: string;
      prefill: { name: string; email: string };
    }>("/api/v1/subscription/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_code: planCode, billing_interval: interval, billing_state: billingState }),
    });

    await loadRazorpay();

    await new Promise<void>((resolve, reject) => {
      let settled = false;
      const rzp = new (window as any).Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "SmartSpace",
        description: `${order.plan_name} · ${interval === "yearly" ? "Yearly" : "Monthly"}`,
        image: "/logo.png",
        order_id: order.order_id,
        prefill: order.prefill,
        theme: { color: "#2F5BEA" },
        handler: async (response: any) => {
          settled = true;
          hooks.onVerifying?.();
          try {
            await apiRequest("/api/v1/subscription/verify", {
              method: "POST",
              body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });
            resolve();
          } catch (e) {
            reject(e);
          }
        },
        modal: { ondismiss: () => !settled && reject(new PaymentCancelled()) },
      });
      rzp.on("payment.failed", () => {
        settled = true;
        reject(new PaymentFailed(order.order_id));
      });
      rzp.open();
    });

    await Promise.all([authStore.fetchProfile(), fetchSubscription(), fetchInvoices().catch(() => {})]);
  }

  async function cancel() {
    await apiRequest("/api/v1/subscription/cancel", { method: "POST" });
    await fetchSubscription();
  }

  async function downloadInvoice(invoice: Invoice) {
    const res = await apiFetch(`/api/v1/invoices/${invoice.id}/download`);
    if (!res.ok) throw await errorFromResponse(res);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `SmartSpace-invoice-${invoice.id.slice(0, 8).toUpperCase()}.html`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  }

  return {
    plans,
    plansLoaded,
    plansError,
    currentSubscription,
    invoices,
    fetchPlans,
    ensurePlans,
    fetchSubscription,
    fetchInvoices,
    checkout,
    cancel,
    downloadInvoice,
  };
});

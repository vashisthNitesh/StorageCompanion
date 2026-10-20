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

let razorpayLoader: Promise<void> | null = null;

/** Loads Razorpay Checkout only when the user actually starts a payment. */
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
      reject(new Error("The payment window couldn't load. Disable ad blockers for this site and try again."));
    };
    document.head.appendChild(script);
  });
  return razorpayLoader;
}

export const useBillingStore = defineStore("billing", () => {
  const authStore = useAuthStore();
  const plans = ref<Plan[]>([]);
  const plansError = ref("");
  const currentSubscription = ref<Subscription | null>(null);
  const invoices = ref<Invoice[]>([]);
  const isCheckingOut = ref(false);

  async function fetchPlans() {
    plansError.value = "";
    try {
      plans.value = await apiRequest<Plan[]>("/api/v1/plans");
    } catch (err: any) {
      plansError.value = err.message || "Couldn't load plans.";
    }
  }

  async function fetchSubscription() {
    try {
      const data = await apiRequest<Subscription & { status: string }>("/api/v1/subscription");
      currentSubscription.value = data.id ? data : null;
    } catch {
      currentSubscription.value = null;
    }
  }

  async function fetchInvoices() {
    try {
      invoices.value = await apiRequest<Invoice[]>("/api/v1/invoices");
    } catch {
      invoices.value = [];
    }
  }

  async function checkout(planCode: string, interval: "monthly" | "yearly", billingState: string): Promise<void> {
    isCheckingOut.value = true;
    try {
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
          image: "/logo.svg",
          order_id: order.order_id,
          prefill: order.prefill,
          theme: { color: "#2563eb" },
          handler: async (response: any) => {
            settled = true;
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
          modal: {
            ondismiss: () => {
              if (!settled) reject(new Error("Payment cancelled. You haven't been charged."));
            },
          },
        });
        rzp.on("payment.failed", (response: any) => {
          settled = true;
          reject(new Error(response?.error?.description || "The payment was declined. Please try another method."));
        });
        rzp.open();
      });

      await Promise.all([authStore.fetchProfile(), fetchSubscription(), fetchInvoices()]);
    } finally {
      isCheckingOut.value = false;
    }
  }

  async function cancel() {
    const res = await apiRequest<{ message: string }>("/api/v1/subscription/cancel", { method: "POST" });
    await fetchSubscription();
    return res.message;
  }

  async function downloadInvoice(invoice: Invoice) {
    const res = await apiFetch(`/api/v1/invoices/${invoice.id}/download`);
    if (!res.ok) throw await errorFromResponse(res);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `SmartSpace-Invoice-${invoice.id.slice(0, 8).toUpperCase()}.html`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  }

  return {
    plans,
    plansError,
    currentSubscription,
    invoices,
    isCheckingOut,
    fetchPlans,
    fetchSubscription,
    fetchInvoices,
    checkout,
    cancel,
    downloadInvoice,
  };
});

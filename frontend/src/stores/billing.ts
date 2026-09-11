import { defineStore } from "pinia";
import { ref } from "vue";
import { apiRequest } from "../lib/api";
import { useAuthStore } from "./auth";

export interface Plan {
  id: string;
  code: string;
  name: string;
  description: string;
  storage_bytes: number;
  price_monthly: number;
  price_yearly: number;
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
  amount: number;
  currency: string;
  status: string;
  issued_at: string;
}

export const useBillingStore = defineStore("billing", () => {
  const authStore = useAuthStore();
  const plans = ref<Plan[]>([]);
  const currentSubscription = ref<Subscription | null>(null);
  const invoices = ref<Invoice[]>([]);
  const isLoading = ref<boolean>(false);
  const selectedInterval = ref<"monthly" | "yearly">("monthly");

  async function fetchPlans() {
    try {
      const data = await apiRequest<Plan[] | { results: Plan[] }>("/api/v1/plans");
      plans.value = Array.isArray(data) ? data : data.results || [];
    } catch (err) {
      console.error("Failed to load plans", err);
    }
  }

  async function fetchSubscription() {
    try {
      const data = await apiRequest<Subscription>("/api/v1/subscription");
      currentSubscription.value = data.is_valid ? data : null;
      if (data.is_valid && !authStore.hasActiveSubscription) {
        await authStore.fetchProfile();
      }
    } catch {
      currentSubscription.value = null;
    }
  }

  async function fetchInvoices() {
    try {
      const data = await apiRequest<Invoice[] | { results: Invoice[] }>("/api/v1/invoices");
      invoices.value = Array.isArray(data) ? data : data.results || [];
    } catch (err) {
      console.error("Failed to fetch invoices", err);
    }
  }

  // Helper to guarantee checkout.js is loaded without adblock failure
  async function loadRazorpaySDK(): Promise<boolean> {
    if (typeof (window as any).Razorpay === "function") {
      return true;
    }
    return new Promise((resolve) => {
      const existing = document.querySelector('script[src*="checkout.razorpay.com"]');
      if (existing) {
        existing.addEventListener("load", () => resolve(true));
        existing.addEventListener("error", () => resolve(false));
        setTimeout(() => resolve(typeof (window as any).Razorpay === "function"), 1500);
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.head.appendChild(script);
    });
  }

  async function checkout(planCode: string, interval: "monthly" | "yearly" = selectedInterval.value): Promise<void> {
    isLoading.value = true;
    try {
      const order = await apiRequest<{
        provider: string;
        key_id: string;
        order_id: string;
        amount: number;
        currency: string;
        plan_name: string;
        prefill: { name: string; email: string };
      }>("/api/v1/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_code: planCode, billing_interval: interval }),
      });

      // Ensure Razorpay SDK script is loaded
      const isLoaded = await loadRazorpaySDK();
      if (!isLoaded || typeof (window as any).Razorpay !== "function") {
        // Only if offline with mock order and placeholder keys allow mock demo simulation
        if (order.order_id.startsWith("order_mock_") && (!order.key_id || order.key_id === "rzp_test_sample")) {
          await verifyPayment({
            plan_code: planCode,
            razorpay_payment_id: `pay_sim_${Date.now()}`,
            razorpay_order_id: order.order_id,
            razorpay_signature: "mock_signature_approved",
            billing_interval: interval,
          });
          return;
        }

        throw new Error(
          "Razorpay checkout failed to load. Please disable any ad-blockers or shields for this page and try again."
        );
      }

      return new Promise((resolve, reject) => {
        let isSettled = false;

        const options = {
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          name: "SpeedCloud Vault",
          description: `${order.plan_name} (${interval === "yearly" ? "Annual" : "Monthly"})`,
          image: "/logo.svg",
          order_id: order.order_id,
          prefill: order.prefill,
          theme: {
            color: "#2563eb",
          },
          handler: async (response: any) => {
            isSettled = true;
            try {
              await verifyPayment({
                plan_code: planCode,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id || order.order_id,
                razorpay_signature: response.razorpay_signature,
                billing_interval: interval,
              });
              resolve();
            } catch (e) {
              reject(e);
            }
          },
          modal: {
            ondismiss: () => {
              isLoading.value = false;
              if (!isSettled) {
                reject(new Error("Payment was cancelled. An active subscription is required to unlock your vault."));
              }
            },
          },
        };

        try {
          const rzp = new (window as any).Razorpay(options);
          rzp.on("payment.failed", (response: any) => {
            isSettled = true;
            isLoading.value = false;
            const detail = response?.error?.description || response?.error?.reason || "Payment was declined by bank or gateway.";
            reject(new Error(`Razorpay Error: ${detail}`));
          });
          rzp.open();
        } catch (err: any) {
          isLoading.value = false;
          reject(new Error(`Could not initialize Razorpay checkout: ${err.message}`));
        }
      });
    } finally {
      isLoading.value = false;
    }
  }

  async function verifyPayment(payload: {
    plan_code: string;
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
    billing_interval: string;
  }) {
    const res = await apiRequest<{ success: boolean; subscription: Subscription }>(
      "/api/v1/subscription/verify",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    );
    currentSubscription.value = res.subscription;
    await authStore.fetchProfile();
    await fetchInvoices();
  }

  async function cancel() {
    await apiRequest("/api/v1/subscription/cancel", { method: "POST" });
    await fetchSubscription();
  }

  return {
    plans,
    currentSubscription,
    invoices,
    isLoading,
    selectedInterval,
    fetchPlans,
    fetchSubscription,
    fetchInvoices,
    checkout,
    cancel,
  };
});

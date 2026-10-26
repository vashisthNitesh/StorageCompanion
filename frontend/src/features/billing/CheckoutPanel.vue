<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { CheckCircle2, XCircle, ShieldCheck } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore, PaymentCancelled, PaymentFailed, type Plan } from "../../stores/billing";
import { formatBytes, formatDate, formatMoney } from "../../lib/format";
import { normalizeApiError } from "../../lib/errors";
import { actionFor, priceFor, storageLabel, yearlyBreakdown } from "./planCatalog";

// Order summary and payment on the checkout page. It is deliberately not a dialog:
// Razorpay opens its own window, and a dialog underneath would trap it.
const props = defineProps<{ plan: Plan | null; interval: "monthly" | "yearly"; usedBytes?: number }>();
const interval = computed(() => props.interval);

const router = useRouter();
const authStore = useAuthStore();
const billing = useBillingStore();

type Phase = "idle" | "paying" | "verifying" | "success" | "failed";
const phase = ref<Phase>("idle");
const error = ref("");
const orderRef = ref("");
const paidPlan = ref<Plan | null>(null);
const paidUntil = ref("");

// A new choice starts a fresh order.
watch(
  () => props.plan?.code,
  () => {
    if (phase.value === "success" || phase.value === "failed") phase.value = "idle";
    error.value = "";
  }
);

const sub = computed(() => authStore.user?.subscription);
const currentCode = computed(() => (sub.value?.has_active_subscription ? sub.value.plan_code : null));
const action = computed(() => (props.plan ? actionFor(props.plan, currentCode.value, billing.plans) : "choose"));
const total = computed(() => (props.plan ? priceFor(props.plan, interval.value) : 0));
const yearly = computed(() => (props.plan ? yearlyBreakdown(props.plan) : null));
const days = computed(() => (interval.value === "yearly" ? 365 : 30));
const validUntil = computed(() => {
  const now = Date.now();
  const end = sub.value?.current_period_end ? new Date(sub.value.current_period_end).getTime() : 0;
  const start = action.value === "extend" && end > now ? end : now;
  return new Date(start + days.value * 86_400_000).toISOString();
});
const tooSmall = computed(() => !!props.plan && !!props.usedBytes && props.usedBytes > props.plan.storage_bytes);
const busy = computed(() => phase.value === "paying" || phase.value === "verifying");
const heading = "Order summary";

async function pay() {
  if (!props.plan || busy.value) return;
  phase.value = "paying";
  error.value = "";
  const plan = props.plan;
  const until = validUntil.value;
  try {
    await billing.checkout(plan.code, interval.value, { onVerifying: () => (phase.value = "verifying") });
    paidPlan.value = plan;
    paidUntil.value = until;
    phase.value = "success";
  } catch (err) {
    phase.value = "idle";
    if (err instanceof PaymentCancelled) {
      error.value = "Payment cancelled. You haven't been charged.";
    } else if (err instanceof PaymentFailed) {
      orderRef.value = err.orderId;
      phase.value = "failed";
    } else if (err instanceof Error && err.message === "razorpay_unavailable") {
      error.value = "The payment window couldn't load. Turn off ad blockers for this site and try again.";
    } else {
      const n = normalizeApiError(err);
      error.value = n.status === 503 ? "Online payments are unavailable right now. Please try again later." : n.message;
    }
  }
}
</script>

<template>
  <section class="rounded-2xl border border-line bg-surface shadow-xs" aria-labelledby="checkout-heading" aria-live="polite">
    <!-- Paid -->
    <div v-if="phase === 'success'" class="p-5 text-center sm:p-6">
      <CheckCircle2 :size="40" :stroke-width="1.5" class="mx-auto text-success" aria-hidden="true" />
      <h2 id="checkout-heading" class="mt-3 text-md font-semibold text-fg">Payment complete</h2>
      <p class="mt-1 text-base text-fg-muted">You're on {{ paidPlan?.name }} until {{ formatDate(paidUntil) }}. Your invoice is in Plan & billing.</p>
      <UiButton class="mt-5" variant="primary" block @click="router.push('/app/files')">Start uploading</UiButton>
      <UiButton class="mt-2" variant="ghost" block @click="router.push('/app/billing')">Back to Plan & billing</UiButton>
    </div>

    <!-- Declined -->
    <div v-else-if="phase === 'failed'" class="p-5 text-center sm:p-6">
      <XCircle :size="40" :stroke-width="1.5" class="mx-auto text-danger" aria-hidden="true" />
      <h2 id="checkout-heading" class="mt-3 text-md font-semibold text-fg">Payment didn't go through</h2>
      <p class="mt-1 text-base text-fg-muted">Your plan hasn't changed. Try again, or use a different payment method.</p>
      <p v-if="orderRef" class="mt-3 text-sm text-fg-subtle">Reference: <span class="font-mono">{{ orderRef }}</span></p>
      <UiButton class="mt-5" variant="primary" block @click="phase = 'idle'">Try again</UiButton>
    </div>

    <!-- Order summary -->
    <form v-else novalidate class="p-5 sm:p-6" @submit.prevent="pay">
      <h2 id="checkout-heading" class="text-md font-semibold text-fg">{{ heading }}</h2>

      <div v-if="!plan" class="mt-4 space-y-3" aria-busy="true">
        <UiSkeleton class="h-5 w-32" /><UiSkeleton class="h-4 w-full" /><UiSkeleton class="h-4 w-2/3" />
      </div>
      <template v-else>
        <div class="mt-4 flex items-baseline justify-between gap-3">
          <p class="font-medium text-fg">{{ plan.name }}</p>
          <p class="tabular text-sm text-fg-muted">{{ storageLabel(plan.storage_bytes) }} · {{ interval === "yearly" ? "Yearly" : "Monthly" }}</p>
        </div>

        <dl class="tabular mt-5 space-y-2 text-base">
          <div class="flex justify-between gap-3">
            <dt class="text-fg-muted">Billing period</dt>
            <dd class="text-fg">{{ interval === "yearly" ? "12 months" : "30 days" }}</dd>
          </div>
          <template v-if="interval === 'yearly' && yearly">
            <div class="flex justify-between gap-3">
              <dt class="text-fg-muted">12 months at {{ formatMoney(yearly.full / 12) }}</dt>
              <dd class="text-fg-subtle line-through">{{ formatMoney(yearly.full) }}</dd>
            </div>
            <div class="flex justify-between gap-3 text-success">
              <dt>2 months free</dt>
              <dd>−{{ formatMoney(yearly.saving) }}</dd>
            </div>
          </template>
          <div class="flex justify-between gap-3 border-t border-line pt-3 text-md font-semibold">
            <dt class="text-fg">Total</dt>
            <dd class="text-fg">{{ formatMoney(total) }}</dd>
          </div>
          <p class="text-xs text-fg-subtle">Inclusive of all taxes. No extra charges.</p>
          <div class="flex justify-between gap-3 pt-1 text-sm"><dt class="text-fg-subtle">Valid until</dt><dd class="text-fg-muted">{{ formatDate(validUntil) }}</dd></div>
        </dl>

        <UiAlert v-if="tooSmall" tone="warning" class="mt-4">You're using {{ formatBytes(usedBytes) }}. Pick a plan with more space, or delete files first.</UiAlert>
        <UiAlert v-else-if="!authStore.paymentsEnabled" tone="warning" class="mt-4">Online payments are unavailable right now. Please try again later.</UiAlert>
        <UiAlert v-if="error" class="mt-4">{{ error }}</UiAlert>

        <UiButton type="submit" class="mt-5" variant="primary" size="lg" block :loading="busy" :disabled="!authStore.paymentsEnabled || tooSmall">
          {{ phase === "verifying" ? "Confirming payment…" : phase === "paying" ? "Opening Razorpay…" : `Pay ${formatMoney(total)}` }}
        </UiButton>
        <p class="mt-3 flex items-center justify-center gap-1.5 text-sm text-fg-subtle">
          <ShieldCheck :size="14" aria-hidden="true" /> UPI, cards and net banking via Razorpay
        </p>
      </template>
    </form>
  </section>
</template>

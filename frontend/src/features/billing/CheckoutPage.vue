<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Check, ShieldCheck, Receipt, CalendarClock } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import CheckoutPanel from "./CheckoutPanel.vue";
import IntervalToggle from "./IntervalToggle.vue";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore } from "../../stores/billing";
import { formatDate } from "../../lib/format";
import { actionFor, audienceFor, checkoutHeading, planFeatures, storageLabel } from "./planCatalog";

// Checkout for one plan: what you're buying and what happens when you pay, next to payment.
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const billing = useBillingStore();

const interval = ref<"monthly" | "yearly">(route.query.interval === "monthly" ? "monthly" : "yearly");
watch(interval, (v) => void router.replace({ query: { ...route.query, interval: v } }));

const plan = computed(() => billing.plans.find((p) => p.code === route.query.plan) ?? null);
const sub = computed(() => authStore.user?.subscription);
const currentCode = computed(() => (sub.value?.has_active_subscription ? sub.value.plan_code : null));
const action = computed(() => (plan.value ? actionFor(plan.value, currentCode.value, billing.plans) : "choose"));
const period = computed(() => (interval.value === "yearly" ? "1 year" : "30 days"));

/** One sentence on what paying does, in the person's situation. */
const whatHappens = computed(() => {
  if (!plan.value) return "";
  switch (action.value) {
    case "extend":
      return sub.value?.can_upload
        ? `Adds ${period.value} to ${plan.value.name}, starting when your current period ends on ${formatDate(sub.value?.current_period_end)}. You keep every day you have left.`
        : `${plan.value.name} starts again as soon as you pay and lasts ${period.value}.`;
    case "upgrade":
    case "switch":
      return `${plan.value.name} starts as soon as you pay and lasts ${period.value}. Time left on ${sub.value?.plan_name} isn't carried over.`;
    default:
      return `${plan.value.name} starts as soon as you pay and lasts ${period.value}.`;
  }
});

onMounted(async () => {
  void authStore.fetchAuthConfig();
  await billing.ensurePlans();
  if (billing.plansLoaded && !plan.value) void router.replace({ name: "plans" });
});
</script>

<template>
  <div class="mx-auto max-w-6xl">
    <UiButton variant="ghost" size="sm" :icon="ArrowLeft" :to="{ name: 'plans', query: { interval } }" class="-ml-2">All plans</UiButton>

    <div v-if="!plan" class="mt-4 space-y-4" aria-busy="true">
      <UiSkeleton class="h-8 w-64" />
      <UiSkeleton class="h-64 w-full" />
    </div>
    <template v-else>
      <h1 class="mt-2 text-2xl font-semibold tracking-tight text-fg">{{ checkoutHeading(plan, action) }}</h1>

      <div class="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_400px]">
        <section class="rounded-2xl border border-line bg-surface p-5 shadow-xs sm:p-6" aria-labelledby="checkout-plan">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div class="flex items-center gap-2">
                <h2 id="checkout-plan" class="text-base font-semibold text-fg">{{ plan.name }}</h2>
                <UiBadge v-if="plan.code === currentCode" tone="success">Current plan</UiBadge>
              </div>
              <p class="mt-0.5 text-sm text-fg-muted">{{ audienceFor(plan) }}</p>
            </div>
            <p class="tabular text-3xl font-semibold tracking-tight text-fg">{{ storageLabel(plan.storage_bytes) }}</p>
          </div>

          <ul class="mt-5 grid gap-x-6 gap-y-2.5 border-t border-line pt-5 sm:grid-cols-2">
            <li v-for="f in planFeatures(plan)" :key="f" class="flex gap-2.5 text-sm text-fg">
              <Check :size="16" :stroke-width="2.25" class="mt-px shrink-0 text-primary" aria-hidden="true" />{{ f }}
            </li>
          </ul>

          <div class="mt-6 flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-base font-medium text-fg">Billing period</p>
            <IntervalToggle v-model="interval" />
          </div>

          <UiAlert :tone="action === 'upgrade' || action === 'switch' ? 'warning' : 'info'" class="mt-5">{{ whatHappens }}</UiAlert>

          <ul class="mt-6 grid gap-3 text-sm text-fg-muted sm:grid-cols-3">
            <li class="flex items-center gap-2"><ShieldCheck :size="16" class="shrink-0 text-fg-subtle" aria-hidden="true" /> UPI, cards and net banking via Razorpay</li>
            <li class="flex items-center gap-2"><Receipt :size="16" class="shrink-0 text-fg-subtle" aria-hidden="true" /> GST invoice for every payment</li>
            <li class="flex items-center gap-2"><CalendarClock :size="16" class="shrink-0 text-fg-subtle" aria-hidden="true" /> Never renews automatically</li>
          </ul>
        </section>

        <div class="lg:sticky lg:top-6">
          <CheckoutPanel :plan="plan" :interval="interval" :used-bytes="authStore.user?.quota?.bytes_used" />
        </div>
      </div>
    </template>
  </div>
</template>

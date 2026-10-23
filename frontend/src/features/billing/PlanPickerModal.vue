<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import UiModal from "../../components/ui/UiModal.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiButton from "../../components/ui/UiButton.vue";
import PlanList from "./PlanList.vue";
import IntervalToggle from "./IntervalToggle.vue";
import { useBillingStore } from "../../stores/billing";
import { useAuthStore } from "../../stores/auth";
import { onAppEvent } from "../../lib/events";
import { normalizeApiError } from "../../lib/errors";
import { formatMoney } from "../../lib/format";
import { priceFor, RECOMMENDED_CODE } from "./planCatalog";

// Quick plan chooser opened from upload limits and banners. Payment itself happens on
// the billing page: Razorpay must not open on top of a modal dialog.
const router = useRouter();
const billing = useBillingStore();
const authStore = useAuthStore();
const open = ref(false);
const reason = ref("");
const interval = ref<"monthly" | "yearly">("yearly");
const selected = ref("");

const sub = computed(() => authStore.user?.subscription);
const currentCode = computed(() => (sub.value?.has_active_subscription ? sub.value.plan_code : null));
const selectedPlan = computed(() => billing.plans.find((p) => p.code === selected.value) ?? null);

function goToCheckout(plan: string) {
  open.value = false;
  void router.push({ path: "/app/billing", query: { plan, interval: interval.value } });
}

let off: (() => void) | null = null;
onMounted(() => {
  off = onAppEvent("plan-picker", (payload) => {
    // "Extend" banners know the plan already.
    if (payload?.planCode) return goToCheckout(payload.planCode);
    reason.value = payload?.reason ?? "";
    void billing.ensurePlans().then(() => {
      if (!billing.plans.some((p) => p.code === selected.value)) selected.value = currentCode.value ?? RECOMMENDED_CODE;
    });
    open.value = true;
  });
});
onUnmounted(() => off?.());
</script>

<template>
  <UiModal v-model:open="open" title="Choose a plan" description="Prepaid, GST included. Plans don't renew automatically." size="lg">
    <div class="space-y-4">
      <UiAlert v-if="reason" tone="info">{{ reason }}</UiAlert>
      <IntervalToggle v-model="interval" />
      <UiAlert v-if="billing.plansError">
        {{ normalizeApiError(billing.plansError).message }}
        <template #action><UiButton size="sm" @click="billing.fetchPlans()">Retry</UiButton></template>
      </UiAlert>
      <PlanList
        v-else
        v-model="selected"
        :plans="billing.plans"
        :interval="interval"
        :current-code="currentCode"
        :used-bytes="authStore.user?.quota?.bytes_used"
        :loading="!billing.plansLoaded"
      />
    </div>
    <template #footer>
      <UiButton @click="open = false">Not now</UiButton>
      <UiButton variant="primary" :disabled="!selectedPlan" @click="selectedPlan && goToCheckout(selectedPlan.code)">
        {{ selectedPlan ? `Continue · ${formatMoney(priceFor(selectedPlan, interval))}` : "Continue" }}
      </UiButton>
    </template>
  </UiModal>
</template>

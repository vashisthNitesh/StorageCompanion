<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import UiModal from "../../components/ui/UiModal.vue";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiButton from "../../components/ui/UiButton.vue";
import PlanCards from "./PlanCards.vue";
import CheckoutDialog from "./CheckoutDialog.vue";
import { useBillingStore, type Plan } from "../../stores/billing";
import { useAuthStore } from "../../stores/auth";
import { onAppEvent } from "../../lib/events";
import { normalizeApiError } from "../../lib/errors";
import { yearlySavingsPercent } from "./planCatalog";

const billing = useBillingStore();
const authStore = useAuthStore();
const open = ref(false);
const reason = ref("");
const interval = ref<"monthly" | "yearly">("yearly");
const checkoutOpen = ref(false);
const chosen = ref<Plan | null>(null);

const currentCode = computed(() => (authStore.user?.subscription?.has_active_subscription ? authStore.user.subscription.plan_code : null));
const savings = computed(() => yearlySavingsPercent(billing.plans));

let off: (() => void) | null = null;
onMounted(() => {
  off = onAppEvent("plan-picker", (payload) => {
    reason.value = payload?.reason ?? "";
    void authStore.fetchAuthConfig();
    // "Extend" banners jump straight to checkout for the current plan.
    if (payload?.planCode) {
      void billing.ensurePlans().then(() => {
        const plan = billing.plans.find((p) => p.code === payload.planCode);
        if (plan) select(plan);
        else open.value = true;
      });
      return;
    }
    open.value = true;
    void billing.ensurePlans();
  });
});
onUnmounted(() => off?.());

function select(plan: Plan) {
  chosen.value = plan;
  open.value = false;
  checkoutOpen.value = true;
}
</script>

<template>
  <UiModal v-model:open="open" title="Choose a plan" description="Prepaid, GST included. Plans don't renew automatically." size="xl">
    <div class="space-y-5">
      <UiAlert v-if="reason" tone="info">{{ reason }}</UiAlert>
      <div class="flex justify-center">
        <UiSegmented
          v-model="interval"
          label="Billing period"
          :options="[
            { value: 'monthly', label: 'Monthly' },
            { value: 'yearly', label: 'Yearly', badge: savings ? `Save ${savings}%` : undefined },
          ]"
        />
      </div>
      <UiAlert v-if="billing.plansError">
        {{ normalizeApiError(billing.plansError).message }}
        <template #action><UiButton size="sm" @click="billing.fetchPlans()">Retry</UiButton></template>
      </UiAlert>
      <PlanCards :plans="billing.plans" :interval="interval" :current-code="currentCode" :loading="!billing.plansLoaded && !billing.plansError" @select="select" />
    </div>
  </UiModal>
  <CheckoutDialog v-model:open="checkoutOpen" v-model:interval="interval" :plan="chosen" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useBillingStore, type Plan } from "../../stores/billing";
import { useAuthStore } from "../../stores/auth";
import { normalizeApiError } from "../../lib/errors";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiButton from "../../components/ui/UiButton.vue";
import PlanCards from "../../features/billing/PlanCards.vue";
import CompareTable from "../../features/billing/CompareTable.vue";
import { yearlySavingsPercent } from "../../features/billing/planCatalog";

// Same plan cards as the app, so marketing and in-app pricing never disagree.
defineProps<{ compare?: boolean }>();
const router = useRouter();
const billing = useBillingStore();
const authStore = useAuthStore();
const interval = ref<"monthly" | "yearly">("yearly");
const savings = computed(() => yearlySavingsPercent(billing.plans));

function choose(p: Plan) {
  void router.push(authStore.isAuthenticated ? { path: "/app/billing", query: { plan: p.code } } : { path: "/register", query: { plan: p.code } });
}

onMounted(() => void billing.ensurePlans());
</script>

<template>
  <div>
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
    <UiAlert v-if="billing.plansError" class="mx-auto mt-8 max-w-md">
      {{ normalizeApiError(billing.plansError).message }}
      <template #action><UiButton size="sm" @click="billing.fetchPlans()">Retry</UiButton></template>
    </UiAlert>
    <div class="mt-8">
      <PlanCards :plans="billing.plans" :interval="interval" :loading="!billing.plansLoaded && !billing.plansError" @select="choose" />
    </div>
    <p class="mt-6 text-center text-base text-fg-muted">Prices in INR, GST included. Pay with UPI, cards or net banking.</p>
    <details v-if="compare && billing.plans.length" class="mt-10">
      <summary class="mx-auto w-fit cursor-pointer select-none rounded text-base font-medium text-primary hover:underline">Compare all features</summary>
      <div class="mt-4"><CompareTable :plans="billing.plans" /></div>
    </details>
  </div>
</template>

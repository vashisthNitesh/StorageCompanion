<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ChevronDown } from "lucide-vue-next";
import { useBillingStore, type Plan } from "../../stores/billing";
import { useAuthStore } from "../../stores/auth";
import { normalizeApiError } from "../../lib/errors";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiButton from "../../components/ui/UiButton.vue";
import PlanCards from "../../features/billing/PlanCards.vue";
import IntervalToggle from "../../features/billing/IntervalToggle.vue";
import CompareTable from "../../features/billing/CompareTable.vue";

// Same plan cards as the app, so marketing and in-app pricing never disagree.
defineProps<{ compare?: boolean }>();
const router = useRouter();
const billing = useBillingStore();
const authStore = useAuthStore();
const interval = ref<"monthly" | "yearly">("yearly");

function choose(plan: Plan) {
  const query = { plan: plan.code, interval: interval.value };
  void router.push(authStore.isAuthenticated ? { name: "checkout", query } : { path: "/register", query });
}

onMounted(() => void billing.ensurePlans());
</script>

<template>
  <div>
    <div class="flex justify-center"><IntervalToggle v-model="interval" /></div>
    <UiAlert v-if="billing.plansError" class="mx-auto mt-6 max-w-xl">
      {{ normalizeApiError(billing.plansError).message }}
      <template #action><UiButton size="sm" @click="billing.fetchPlans()">Retry</UiButton></template>
    </UiAlert>
    <div v-else class="mt-8">
      <PlanCards :plans="billing.plans" :interval="interval" :loading="!billing.plansLoaded" public-cta="Get started" @select="choose" />
    </div>
    <p class="mt-6 text-center text-sm text-fg-muted">Prices in INR, GST included. Pay with UPI, cards or net banking. Plans never renew automatically.</p>
    <details v-if="compare && billing.plans.length" class="group mt-8">
      <summary class="mx-auto flex w-fit cursor-pointer select-none items-center gap-1.5 rounded text-base font-medium text-primary hover:underline">
        Compare all plans <ChevronDown :size="16" class="transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div class="mt-4"><CompareTable :plans="billing.plans" /></div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ArrowRight, Check } from "lucide-vue-next";
import { useBillingStore } from "../../stores/billing";
import { useAuthStore } from "../../stores/auth";
import { normalizeApiError } from "../../lib/errors";
import { formatMoney } from "../../lib/format";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiButton from "../../components/ui/UiButton.vue";
import PlanList from "../../features/billing/PlanList.vue";
import IntervalToggle from "../../features/billing/IntervalToggle.vue";
import CompareTable from "../../features/billing/CompareTable.vue";
import { INCLUDED_IN_ALL, priceFor, RECOMMENDED_CODE } from "../../features/billing/planCatalog";

// Same plan list as the app, so marketing and in-app pricing never disagree.
defineProps<{ compare?: boolean }>();
const router = useRouter();
const billing = useBillingStore();
const authStore = useAuthStore();
const interval = ref<"monthly" | "yearly">("yearly");
const selected = ref(RECOMMENDED_CODE);
const selectedPlan = computed(() => billing.plans.find((p) => p.code === selected.value) ?? null);

function continueWith() {
  if (!selectedPlan.value) return;
  const query = { plan: selectedPlan.value.code, interval: interval.value };
  void router.push(authStore.isAuthenticated ? { path: "/app/billing", query } : { path: "/register", query });
}

onMounted(() => void billing.ensurePlans());
</script>

<template>
  <div class="mx-auto grid max-w-5xl items-start gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
    <div>
      <div class="flex justify-center lg:justify-start"><IntervalToggle v-model="interval" /></div>
      <UiAlert v-if="billing.plansError" class="mt-6">
        {{ normalizeApiError(billing.plansError).message }}
        <template #action><UiButton size="sm" @click="billing.fetchPlans()">Retry</UiButton></template>
      </UiAlert>
      <PlanList v-else v-model="selected" class="mt-6" :plans="billing.plans" :interval="interval" :loading="!billing.plansLoaded" />
    </div>

    <aside class="rounded-lg border border-line bg-surface p-5 shadow-xs sm:p-6 lg:sticky lg:top-24 lg:mt-14">
      <p class="text-base font-semibold text-fg">Every plan includes</p>
      <ul class="mt-3 space-y-2">
        <li v-for="item in INCLUDED_IN_ALL" :key="item" class="flex gap-2 text-base text-fg">
          <Check :size="18" :stroke-width="2" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />{{ item }}
        </li>
      </ul>
      <UiButton class="mt-6" variant="primary" size="lg" block :icon-right="ArrowRight" :disabled="!selectedPlan" @click="continueWith">
        {{ selectedPlan ? `Continue with ${selectedPlan.name}` : "Continue" }}
      </UiButton>
      <p v-if="selectedPlan" class="tabular mt-2 text-center text-sm text-fg-subtle">
        {{ formatMoney(priceFor(selectedPlan, interval)) }} {{ interval === "yearly" ? "per year" : "per month" }}, GST included
      </p>
      <p class="mt-4 border-t border-line pt-4 text-sm text-fg-muted">Pay with UPI, cards or net banking. Plans don't renew automatically.</p>
    </aside>

    <details v-if="compare && billing.plans.length" class="lg:col-span-2">
      <summary class="mx-auto w-fit cursor-pointer select-none rounded text-base font-medium text-primary hover:underline">Compare all features</summary>
      <div class="mt-4"><CompareTable :plans="billing.plans" /></div>
    </details>
  </div>
</template>

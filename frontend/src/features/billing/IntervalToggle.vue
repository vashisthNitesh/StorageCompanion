<script setup lang="ts">
import { computed } from "vue";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import { useBillingStore } from "../../stores/billing";
import { yearlySavingsPercent } from "./planCatalog";

const interval = defineModel<"monthly" | "yearly">({ required: true });
const billing = useBillingStore();
const savings = computed(() => yearlySavingsPercent(billing.plans));
</script>

<template>
  <UiSegmented
    v-model="interval"
    label="Billing period"
    :options="[
      { value: 'monthly', label: 'Monthly' },
      { value: 'yearly', label: 'Yearly', badge: savings ? `Save ${savings}%` : undefined },
    ]"
  />
</template>

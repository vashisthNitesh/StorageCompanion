<script setup lang="ts">
import { computed } from "vue";
import { RadioGroupRoot, RadioGroupItem, RadioGroupIndicator } from "reka-ui";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import type { Plan } from "../../stores/billing";
import { formatBytes, formatMoney } from "../../lib/format";
import { audienceFor, priceFor, RECOMMENDED_CODE, storageLabel } from "./planCatalog";

// One selectable list of plans, used in the app, the plan picker and the pricing page.
const selected = defineModel<string>();
const props = defineProps<{
  plans: Plan[];
  interval: "monthly" | "yearly";
  currentCode?: string | null;
  /** Bytes already stored; plans smaller than this can't be chosen. */
  usedBytes?: number;
  loading?: boolean;
}>();

const rows = computed(() =>
  props.plans.map((plan) => {
    const price = priceFor(plan, props.interval);
    return {
      plan,
      price,
      perMonth: props.interval === "yearly" ? Math.round(price / 12) : null,
      tooSmall: !!props.usedBytes && props.usedBytes > plan.storage_bytes,
    };
  })
);
</script>

<template>
  <div v-if="loading" class="space-y-3" aria-busy="true">
    <div v-for="i in 5" :key="i" class="flex items-start gap-3 rounded-lg border border-line bg-surface p-4">
      <UiSkeleton class="mt-1 h-4 w-4 rounded-full" />
      <div class="flex-1 space-y-2"><UiSkeleton class="h-5 w-24" /><UiSkeleton class="h-3.5 w-48" /></div>
      <UiSkeleton class="h-5 w-16" />
    </div>
  </div>
  <RadioGroupRoot v-else v-model="selected" aria-label="Plans" class="space-y-3">
    <RadioGroupItem
      v-for="r in rows"
      :key="r.plan.code"
      :value="r.plan.code"
      :disabled="r.tooSmall"
      class="group grid w-full grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-x-3 rounded-lg border border-line bg-surface p-4 text-left transition-colors duration-fast hover:border-line-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:border-line data-[state=checked]:border-primary data-[state=checked]:bg-primary-soft/40 data-[state=checked]:ring-1 data-[state=checked]:ring-primary sm:p-5"
    >
      <span class="mt-1 flex h-[18px] w-[18px] items-center justify-center rounded-full border-2 border-line-strong bg-surface group-data-[state=checked]:border-primary">
        <RadioGroupIndicator class="h-2 w-2 rounded-full bg-primary" />
      </span>
      <span class="min-w-0">
        <span class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span class="tabular text-lg font-semibold text-fg">{{ storageLabel(r.plan.storage_bytes) }}</span>
          <span class="text-base font-medium text-fg-muted">{{ r.plan.name }}</span>
          <UiBadge v-if="r.plan.code === currentCode" tone="success">Current</UiBadge>
          <UiBadge v-else-if="r.plan.code === RECOMMENDED_CODE" tone="primary">Most popular</UiBadge>
        </span>
        <span class="mt-0.5 block text-sm text-fg-muted">{{ audienceFor(r.plan) }}</span>
        <span class="mt-2 flex flex-col gap-1 text-sm text-fg-subtle sm:flex-row sm:gap-3">
          <span>Files up to {{ storageLabel(r.plan.max_file_size) }}</span>
          <span class="hidden sm:inline" aria-hidden="true">·</span>
          <span>{{ r.plan.version_retention_days }}-day version history</span>
        </span>
        <span v-if="r.tooSmall" class="mt-2 block text-sm text-warning">You're using {{ formatBytes(usedBytes) }}, more than this plan holds.</span>
      </span>
      <span class="tabular text-right">
        <span class="block text-lg font-semibold text-fg">{{ formatMoney(r.price) }}</span>
        <span class="block text-sm text-fg-subtle">{{ interval === "yearly" ? "per year" : "per month" }}</span>
        <span v-if="r.perMonth" class="mt-0.5 hidden text-xs text-fg-subtle sm:block">{{ formatMoney(r.perMonth) }}/month</span>
      </span>
    </RadioGroupItem>
  </RadioGroupRoot>
</template>

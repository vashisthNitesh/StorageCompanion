<script setup lang="ts">
import { computed } from "vue";
import { Check } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import type { Plan } from "../../stores/billing";
import { formatBytes, formatMoney } from "../../lib/format";
import { RECOMMENDED_CODE, actionFor, audienceFor, ctaLabel, monthlyEquivalent, planFeatures, priceFor, storageLabel } from "./planCatalog";

// Plan cards used on the plans page and the public pricing page, so they never disagree.
const props = withDefaults(
  defineProps<{
    plans: Plan[];
    interval: "monthly" | "yearly";
    currentCode?: string | null;
    /** Bytes already stored; smaller plans can't be chosen. */
    usedBytes?: number;
    loading?: boolean;
    /** Public pages: every button reads the same ("Get started"). */
    publicCta?: string;
  }>(),
  { currentCode: null, usedBytes: 0 }
);
const emit = defineEmits<{ select: [plan: Plan] }>();

const cards = computed(() =>
  props.plans.map((plan) => {
    const action = actionFor(plan, props.currentCode, props.plans);
    const tooSmall = !!props.usedBytes && props.usedBytes > plan.storage_bytes;
    return {
      plan,
      action,
      current: plan.code === props.currentCode,
      recommended: plan.code === RECOMMENDED_CODE,
      perMonth: monthlyEquivalent(plan, props.interval),
      total: priceFor(plan, props.interval),
      label: props.publicCta ?? ctaLabel(plan, action),
      tooSmall,
    };
  })
);
</script>

<template>
  <div class="grid items-stretch gap-4 pt-3 sm:grid-cols-2 lg:grid-cols-3 min-[1380px]:grid-cols-5" role="list" aria-label="Plans">
    <template v-if="loading">
      <div v-for="i in 5" :key="i" class="space-y-4 rounded-2xl border border-line bg-surface p-5">
        <UiSkeleton class="h-4 w-24" />
        <UiSkeleton class="h-3 w-40" />
        <UiSkeleton class="h-9 w-28" />
        <UiSkeleton class="h-10 w-full" />
        <UiSkeleton class="h-24 w-full" />
      </div>
    </template>
    <article
      v-for="c in cards"
      v-else
      :key="c.plan.code"
      role="listitem"
      class="relative flex flex-col rounded-2xl border bg-surface p-5 transition-shadow duration-base"
      :class="c.recommended && !c.current ? 'border-primary shadow-md ring-1 ring-primary' : 'border-line shadow-xs hover:shadow-md'"
      :aria-label="`${c.plan.name}: ${storageLabel(c.plan.storage_bytes)}, ${formatMoney(c.total)} ${interval === 'yearly' ? 'per year' : 'per month'}`"
    >
      <span
        v-if="c.recommended && !c.current"
        class="absolute -top-3 left-5 rounded-full bg-primary px-2.5 py-0.5 text-xs font-semibold text-primary-fg shadow-sm"
      >
        Most popular
      </span>

      <header>
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-base font-semibold text-fg">{{ c.plan.name }}</h3>
          <UiBadge v-if="c.current" tone="success">Current plan</UiBadge>
        </div>
        <p class="mt-1 text-sm text-fg-muted lg:min-h-[40px]">{{ audienceFor(c.plan) }}</p>
      </header>

      <p class="tabular mt-4 text-3xl font-semibold tracking-tight text-fg">{{ storageLabel(c.plan.storage_bytes) }}</p>
      <p class="tabular mt-1 flex items-baseline gap-1">
        <span class="text-lg font-semibold text-fg">{{ formatMoney(c.perMonth) }}</span>
        <span class="text-sm text-fg-subtle">/ month</span>
      </p>
      <p class="tabular text-xs text-fg-subtle">{{ interval === "yearly" ? `${formatMoney(c.total)} billed yearly` : "Billed monthly" }}</p>

      <UiButton
        class="mt-5"
        block
        :variant="c.current ? 'secondary' : c.recommended || c.action === 'upgrade' ? 'primary' : 'secondary'"
        :disabled="c.tooSmall"
        @click="emit('select', c.plan)"
      >
        {{ c.label }}
      </UiButton>
      <p v-if="c.tooSmall" class="mt-2 text-xs text-warning">Your files ({{ formatBytes(usedBytes) }}) don't fit in this plan.</p>

      <ul class="mt-5 space-y-2.5 border-t border-line pt-5">
        <li v-for="f in planFeatures(c.plan)" :key="f" class="flex gap-2.5 text-sm text-fg">
          <Check :size="16" :stroke-width="2.25" class="mt-px shrink-0 text-primary" aria-hidden="true" />
          {{ f }}
        </li>
      </ul>
    </article>
  </div>
</template>

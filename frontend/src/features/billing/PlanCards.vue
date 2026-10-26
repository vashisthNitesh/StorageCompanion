<script setup lang="ts">
import { computed } from "vue";
import { Check } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import type { Plan } from "../../stores/billing";
import { formatBytes, formatMoney } from "../../lib/format";
import { RECOMMENDED_CODE, actionFor, audienceFor, ctaLabel, monthlyPrice, planFeatures, priceFor, storageLabel, yearlyBreakdown } from "./planCatalog";

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
      monthly: monthlyPrice(plan),
      yearly: yearlyBreakdown(plan),
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
      <!-- Fixed height so switching Monthly / Yearly never shifts the layout -->
      <div class="relative mt-2 h-[84px]">
        <Transition
          enter-active-class="transition-opacity duration-base ease-out"
          leave-active-class="absolute inset-x-0 top-0 transition-opacity duration-fast ease-in"
          enter-from-class="opacity-0"
          leave-to-class="opacity-0"
        >
          <div v-if="interval === 'yearly'" key="yearly" class="tabular">
            <p class="text-sm text-fg-subtle"><s aria-label="Full price">{{ formatMoney(c.yearly.full) }}</s></p>
            <p class="flex items-baseline gap-x-1.5 whitespace-nowrap">
              <span class="text-2xl font-semibold tracking-tight text-fg">{{ formatMoney(c.yearly.price) }}</span>
              <span class="text-sm text-fg-subtle">/ year</span>
            </p>
            <p class="mt-0.5 text-xs text-fg-muted">Effectively {{ formatMoney(c.yearly.perMonth) }}/month</p>
            <p class="text-xs font-medium text-success">You save {{ formatMoney(c.yearly.saving) }}</p>
          </div>
          <div v-else key="monthly" class="tabular">
            <p class="text-sm text-transparent" aria-hidden="true">&nbsp;</p>
            <p class="flex items-baseline gap-x-1.5 whitespace-nowrap">
              <span class="text-2xl font-semibold tracking-tight text-fg">{{ formatMoney(c.monthly) }}</span>
              <span class="text-sm text-fg-subtle">/ month</span>
            </p>
            <p class="mt-0.5 text-xs text-fg-muted">Billed every month</p>
          </div>
        </Transition>
      </div>

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

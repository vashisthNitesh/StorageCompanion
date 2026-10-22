<script setup lang="ts">
import { computed } from "vue";
import { Check } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import type { Plan } from "../../stores/billing";
import { formatMoney } from "../../lib/format";
import { ACTION_LABEL, actionFor, audienceFor, planHighlights, priceFor, storageLabel } from "./planCatalog";

const props = withDefaults(
  defineProps<{
    plans: Plan[];
    interval: "monthly" | "yearly";
    currentCode?: string | null;
    recommendedCode?: string;
    loading?: boolean;
    disabled?: boolean;
    disabledReason?: string;
  }>(),
  { recommendedCode: "value" }
);
const emit = defineEmits<{ select: [plan: Plan] }>();

const cards = computed(() =>
  props.plans.map((plan, i) => {
    const price = priceFor(plan, props.interval);
    const monthlyEquivalent = props.interval === "yearly" ? price / 12 : null;
    const action = actionFor(plan, props.currentCode, props.plans);
    return { plan, price, monthlyEquivalent, action, highlights: planHighlights(plan, props.plans[i - 1]) };
  })
);
</script>

<template>
  <div
    class="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2 pt-3 scrollbar-thin md:mx-0 md:grid md:grid-cols-3 md:gap-x-4 md:gap-y-6 md:overflow-visible md:px-0 lg:grid-cols-5"
    role="list"
    aria-label="Plans"
  >
    <template v-if="loading">
      <div v-for="i in 5" :key="i" class="w-[78%] shrink-0 snap-start space-y-4 rounded-lg border border-line bg-surface p-5 md:w-auto">
        <UiSkeleton class="h-4 w-20" />
        <UiSkeleton class="h-8 w-24" />
        <UiSkeleton class="h-6 w-28" />
        <UiSkeleton class="h-16 w-full" />
        <UiSkeleton class="h-9 w-full" />
      </div>
    </template>
    <article
      v-for="c in cards"
      v-else
      :key="c.plan.code"
      role="listitem"
      class="relative flex w-[78%] shrink-0 snap-start flex-col rounded-lg border bg-surface p-5 md:row-span-6 md:grid md:w-auto md:grid-rows-subgrid md:gap-0"
      :class="c.plan.code === recommendedCode ? 'border-primary ring-1 ring-primary' : 'border-line'"
      :aria-label="`${c.plan.name}, ${storageLabel(c.plan.storage_bytes)}`"
    >
      <div class="flex items-center justify-between gap-2">
        <h3 class="text-base font-semibold text-fg">{{ c.plan.name }}</h3>
        <UiBadge v-if="c.plan.code === currentCode" tone="success">Current</UiBadge>
      </div>
      <span
        v-if="c.plan.code === recommendedCode"
        class="absolute -top-2.5 left-5 rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-fg"
      >Recommended</span>
      <p class="tabular mt-2 text-2xl font-semibold text-fg">{{ storageLabel(c.plan.storage_bytes) }}</p>
      <div class="mt-3">
        <p class="tabular">
          <span class="text-lg font-semibold text-fg">{{ formatMoney(c.price) }}</span>
          <span class="text-sm text-fg-subtle"> / {{ interval === "yearly" ? "year" : "month" }}</span>
        </p>
        <p class="tabular mt-0.5 h-4 text-xs text-fg-subtle">
          <template v-if="c.monthlyEquivalent">{{ formatMoney(Math.round(c.monthlyEquivalent)) }}/month, billed yearly</template>
        </p>
      </div>
      <p class="mt-3 text-sm text-fg-muted">{{ audienceFor(c.plan) }}</p>
      <div class="mt-4 border-t border-line pt-4">
        <p class="text-xs font-medium text-fg-subtle">{{ c.highlights.lead }}</p>
        <ul class="mt-2 space-y-2">
          <li v-for="item in c.highlights.items" :key="item" class="flex gap-2 text-sm text-fg">
            <Check :size="16" :stroke-width="2" class="mt-px shrink-0 text-primary" aria-hidden="true" />
            {{ item }}
          </li>
        </ul>
      </div>
      <UiButton
        class="mt-5 self-end"
        block
        :variant="c.plan.code === recommendedCode || c.action === 'extend' ? 'primary' : 'secondary'"
        :disabled="disabled"
        :tooltip="disabled ? disabledReason : undefined"
        @click="emit('select', c.plan)"
      >
        {{ ACTION_LABEL[c.action] }}
      </UiButton>
    </article>
  </div>
</template>

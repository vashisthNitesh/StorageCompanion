<script setup lang="ts">
import { ToggleGroupRoot, ToggleGroupItem } from "reka-ui";

// Monthly | Yearly pill. The active option is filled with the brand colour; yearly carries the
// "2 months free" badge (12 months for the price of 10).
const interval = defineModel<"monthly" | "yearly">({ required: true });

function onUpdate(v: unknown) {
  if (v === "monthly" || v === "yearly") interval.value = v;
}
</script>

<template>
  <ToggleGroupRoot
    type="single"
    :model-value="interval"
    aria-label="Billing period"
    class="inline-flex items-center gap-1 rounded-full border border-line bg-surface p-1 shadow-xs"
    @update:model-value="onUpdate"
  >
    <ToggleGroupItem
      value="monthly"
      class="h-9 rounded-full px-4 text-base font-medium text-fg-muted transition-colors duration-base hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary data-[state=on]:bg-primary data-[state=on]:text-primary-fg data-[state=on]:shadow-sm"
    >
      Monthly
    </ToggleGroupItem>
    <ToggleGroupItem
      value="yearly"
      class="flex h-9 items-center gap-2 whitespace-nowrap rounded-full pl-4 pr-1.5 text-base font-medium text-fg-muted transition-colors duration-base hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary data-[state=on]:bg-primary data-[state=on]:text-primary-fg data-[state=on]:shadow-sm"
    >
      Yearly
      <span class="rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-accent-fg">2 months free</span>
    </ToggleGroupItem>
  </ToggleGroupRoot>
</template>

<script setup lang="ts" generic="T extends string">
import type { Component } from "vue";
import { ToggleGroupRoot, ToggleGroupItem } from "reka-ui";
import UiTooltip from "./UiTooltip.vue";

const model = defineModel<T>({ required: true });
withDefaults(
  defineProps<{
    options: { value: T; label: string; icon?: Component; badge?: string; hideLabel?: boolean }[];
    label: string;
    size?: "sm" | "md";
  }>(),
  { size: "md" }
);

function onUpdate(v: unknown) {
  // Single toggle groups emit "" when the active item is clicked again; keep a value selected.
  if (typeof v === "string" && v) model.value = v as T;
}
</script>

<template>
  <ToggleGroupRoot
    type="single"
    :model-value="model"
    :aria-label="label"
    class="inline-flex items-center gap-0.5 rounded border border-line bg-canvas-subtle p-0.5"
    @update:model-value="onUpdate"
  >
    <UiTooltip v-for="o in options" :key="o.value" :content="o.hideLabel ? o.label : undefined">
      <ToggleGroupItem
        :value="o.value"
        :aria-label="o.hideLabel ? o.label : undefined"
        class="inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm font-medium text-fg-muted transition-colors duration-fast hover:text-fg data-[state=on]:bg-surface data-[state=on]:text-fg data-[state=on]:shadow-xs"
        :class="size === 'sm' ? 'h-7 px-2 text-sm' : 'h-8 px-3 text-base'"
      >
        <component :is="o.icon" v-if="o.icon" :size="16" :stroke-width="1.75" aria-hidden="true" />
        <span v-if="!o.hideLabel">{{ o.label }}</span>
        <span v-if="o.badge" class="rounded-full bg-success-soft px-1.5 text-xs font-semibold text-success">{{ o.badge }}</span>
      </ToggleGroupItem>
    </UiTooltip>
  </ToggleGroupRoot>
</template>

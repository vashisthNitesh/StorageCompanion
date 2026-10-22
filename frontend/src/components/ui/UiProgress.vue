<script setup lang="ts">
import { computed } from "vue";
import { ProgressRoot, ProgressIndicator } from "reka-ui";

const props = withDefaults(
  defineProps<{ value: number | null; max?: number; tone?: "primary" | "success" | "warning" | "danger" | "neutral"; size?: "sm" | "md"; label?: string }>(),
  { max: 100, tone: "primary", size: "md" }
);
const pct = computed(() => (props.value == null ? null : Math.max(0, Math.min(100, (props.value / props.max) * 100))));
</script>

<template>
  <ProgressRoot
    :model-value="value"
    :max="max"
    :aria-label="label"
    class="relative w-full overflow-hidden rounded-full bg-canvas-subtle"
    :class="size === 'sm' ? 'h-1.5' : 'h-2'"
  >
    <ProgressIndicator
      class="h-full rounded-full transition-[width] duration-slow ease-out"
      :class="[
        { primary: 'bg-primary', success: 'bg-success', warning: 'bg-warning', danger: 'bg-danger', neutral: 'bg-fg-subtle' }[tone],
        pct == null ? 'w-1/3 animate-shimmer' : '',
      ]"
      :style="pct == null ? undefined : { width: `${pct}%` }"
    />
  </ProgressRoot>
</template>

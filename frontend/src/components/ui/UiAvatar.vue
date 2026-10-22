<script setup lang="ts">
import { computed } from "vue";
const props = withDefaults(defineProps<{ name?: string; email?: string; size?: "sm" | "md" | "lg" }>(), { size: "md" });
const initials = computed(() => {
  const source = (props.name || props.email || "?").trim();
  const parts = source.split(/[\s@._-]+/).filter(Boolean);
  return ((parts[0]?.[0] || "?") + (props.name && parts[1] ? parts[1][0] : "")).toUpperCase();
});
// Stable hue per person so avatars are distinguishable without photos.
const hue = computed(() => {
  let h = 0;
  for (const c of props.email || props.name || "") h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
});
</script>

<template>
  <span
    class="inline-flex shrink-0 select-none items-center justify-center rounded-full font-semibold text-white"
    :class="{ sm: 'h-6 w-6 text-xs', md: 'h-8 w-8 text-sm', lg: 'h-10 w-10 text-base' }[size]"
    :style="{ backgroundColor: `hsl(${hue} 55% 42%)` }"
    aria-hidden="true"
  >{{ initials }}</span>
</template>

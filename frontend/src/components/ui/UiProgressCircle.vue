<script setup lang="ts">
import { computed } from "vue";
const props = withDefaults(defineProps<{ value: number; size?: number; stroke?: number; label?: string }>(), { size: 20, stroke: 2.5 });
const r = computed(() => (props.size - props.stroke) / 2);
const c = computed(() => 2 * Math.PI * r.value);
const offset = computed(() => c.value * (1 - Math.max(0, Math.min(100, props.value)) / 100));
</script>

<template>
  <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" role="progressbar" :aria-valuenow="Math.round(value)" aria-valuemin="0" aria-valuemax="100" :aria-label="label" class="-rotate-90">
    <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" stroke="currentColor" stroke-opacity="0.18" :stroke-width="stroke" />
    <circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" stroke="currentColor" :stroke-width="stroke" stroke-linecap="round" :stroke-dasharray="c" :stroke-dashoffset="offset" class="transition-[stroke-dashoffset] duration-slow ease-out" />
  </svg>
</template>

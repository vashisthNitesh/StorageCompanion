<script setup lang="ts">
import UiBanner from "./UiBanner.vue";
defineProps<{ tone?: "info" | "warning" | "danger" | "success" }>();
</script>

<template>
  <UiBanner :tone="tone ?? 'danger'" inline>
    <slot />
    <template v-if="$slots.action" #action><slot name="action" /></template>
  </UiBanner>
</template>

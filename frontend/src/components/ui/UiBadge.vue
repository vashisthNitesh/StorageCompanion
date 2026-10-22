<script setup lang="ts">
import type { Component } from "vue";
withDefaults(defineProps<{ tone?: "neutral" | "primary" | "success" | "warning" | "danger" | "info"; icon?: Component; dot?: boolean }>(), {
  tone: "neutral",
});
</script>

<template>
  <span
    class="inline-flex h-5 shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 text-xs font-medium"
    :class="{
      neutral: 'bg-canvas-subtle text-fg-muted ring-1 ring-inset ring-line',
      primary: 'bg-primary-soft text-primary-soft-fg',
      success: 'bg-success-soft text-success',
      warning: 'bg-warning-soft text-warning',
      danger: 'bg-danger-soft text-danger',
      info: 'bg-info-soft text-info',
    }[tone]"
  >
    <span v-if="dot" class="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
    <component :is="icon" v-if="icon" :size="12" :stroke-width="2" aria-hidden="true" />
    <slot />
  </span>
</template>

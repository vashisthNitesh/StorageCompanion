<script setup lang="ts">
import type { Component } from "vue";
withDefaults(defineProps<{ icon: Component; title: string; description?: string; tone?: "neutral" | "primary" | "danger"; compact?: boolean }>(), {
  tone: "primary",
});
</script>

<template>
  <div class="flex flex-col items-center text-center" :class="compact ? 'px-4 py-10' : 'px-6 py-16'">
    <span
      class="flex h-12 w-12 items-center justify-center rounded-xl ring-1 ring-inset"
      :class="{
        neutral: 'bg-canvas-subtle text-fg-subtle ring-line',
        primary: 'bg-primary-soft text-primary ring-primary/15',
        danger: 'bg-danger-soft text-danger ring-danger/15',
      }[tone]"
    >
      <component :is="icon" :size="22" :stroke-width="1.75" aria-hidden="true" />
    </span>
    <h3 class="mt-4 text-md font-semibold text-fg">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-sm text-base text-fg-muted">{{ description }}</p>
    <div v-if="$slots.default" class="mt-5 flex flex-wrap justify-center gap-2">
      <slot />
    </div>
  </div>
</template>

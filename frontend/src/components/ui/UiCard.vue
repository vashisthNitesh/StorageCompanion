<script setup lang="ts">
import type { Component } from "vue";

withDefaults(
  defineProps<{
    padded?: boolean;
    title?: string;
    description?: string;
    /** Icon shown in a tinted square beside the title. */
    icon?: Component;
    iconTone?: "primary" | "success" | "warning" | "danger" | "neutral";
  }>(),
  { padded: true, iconTone: "primary" }
);

const TONES = {
  primary: "bg-primary-soft text-primary",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  neutral: "bg-canvas-subtle text-fg-muted",
};
</script>

<template>
  <section class="rounded-xl border border-line bg-surface shadow-xs">
    <div v-if="title || $slots.actions" class="flex flex-col gap-3 px-5 pt-5 sm:flex-row sm:items-start sm:justify-between">
      <div class="flex min-w-0 items-start gap-3">
        <span v-if="icon" class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" :class="TONES[iconTone]">
          <component :is="icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
        </span>
        <div class="min-w-0">
          <h2 v-if="title" class="text-md font-semibold text-fg">{{ title }}</h2>
          <p v-if="description" class="mt-0.5 text-base text-fg-muted">{{ description }}</p>
        </div>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 flex-wrap items-center gap-2"><slot name="actions" /></div>
    </div>
    <div :class="padded ? 'px-5 pb-5 pt-4' : ''"><slot /></div>
  </section>
</template>

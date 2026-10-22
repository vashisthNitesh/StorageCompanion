<script setup lang="ts">
import type { Component } from "vue";
import AppLogo from "./AppLogo.vue";

// Full-page message used for the 404 page and the global error boundary.
defineProps<{ icon: Component; code?: string; title: string; description: string }>();
</script>

<template>
  <div class="flex min-h-[100dvh] flex-col bg-canvas px-4">
    <header class="flex h-14 items-center">
      <router-link to="/" aria-label="SmartSpace home"><AppLogo /></router-link>
    </header>
    <main class="mx-auto flex max-w-md flex-1 flex-col items-center justify-center pb-20 text-center">
      <span class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-sunken text-fg-muted">
        <component :is="icon" :size="24" :stroke-width="1.75" aria-hidden="true" />
      </span>
      <p v-if="code" class="tabular mt-5 text-sm font-medium text-fg-subtle">{{ code }}</p>
      <h1 class="mt-2 text-xl font-semibold text-fg">{{ title }}</h1>
      <p class="mt-2 text-base text-fg-muted">{{ description }}</p>
      <div class="mt-6 flex flex-wrap justify-center gap-2"><slot /></div>
    </main>
  </div>
</template>

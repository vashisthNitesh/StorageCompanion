<script setup lang="ts">
import AppLogo from "../../components/AppLogo.vue";
import ThemeToggle from "../../components/ThemeToggle.vue";

defineProps<{ title: string; subtitle?: string }>();
</script>

<template>
  <div class="relative flex min-h-[100dvh] flex-col bg-canvas px-4 py-10">
    <div class="absolute right-3 top-3"><ThemeToggle /></div>
    <div class="mx-auto flex w-full max-w-[400px] flex-1 flex-col justify-center">
      <router-link to="/" class="mx-auto mb-8" aria-label="SmartSpace home"><AppLogo size="lg" /></router-link>
      <main class="rounded-xl border border-line bg-surface p-6 shadow-sm sm:p-8">
        <h1 class="text-xl font-semibold text-fg">{{ title }}</h1>
        <p v-if="subtitle" class="mt-1.5 text-base text-fg-muted">{{ subtitle }}</p>
        <div class="mt-6"><slot /></div>
      </main>
      <div v-if="$slots.footer" class="mt-6 text-center text-base text-fg-muted"><slot name="footer" /></div>
    </div>
    <nav class="mt-10 flex justify-center gap-5 text-sm text-fg-subtle" aria-label="Legal">
      <router-link to="/security" class="hover:text-fg">Security</router-link>
      <router-link to="/legal" class="hover:text-fg">Terms & privacy</router-link>
    </nav>
  </div>
</template>

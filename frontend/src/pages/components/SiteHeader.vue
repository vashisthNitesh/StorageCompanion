<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Menu, X } from "lucide-vue-next";
import AppLogo from "../../components/AppLogo.vue";
import UiButton from "../../components/ui/UiButton.vue";
import { useAuthStore } from "../../stores/auth";
import { homeFor } from "../../router";

const route = useRoute();
const authStore = useAuthStore();
const open = ref(false);
const links = [
  { to: "/#features", label: "Features" },
  { to: "/pricing", label: "Pricing" },
  { to: "/security", label: "Security" },
  { to: "/#faq", label: "FAQ" },
];
watch(() => route.fullPath, () => (open.value = false));
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-line/70 bg-canvas/85 backdrop-blur">
    <div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
      <router-link to="/" aria-label="SmartSpace home"><AppLogo /></router-link>
      <nav class="hidden items-center gap-8 text-base font-medium text-fg-muted md:flex" aria-label="Main">
        <router-link v-for="l in links" :key="l.to" :to="l.to" class="hover:text-fg">{{ l.label }}</router-link>
      </nav>
      <div class="hidden items-center gap-2 md:flex">
        <UiButton v-if="authStore.isAuthenticated" variant="primary" :to="homeFor(authStore.isMasterAdmin)">
          {{ authStore.isMasterAdmin ? "Open admin console" : "Open my files" }}
        </UiButton>
        <template v-else>
          <UiButton variant="ghost" to="/login">Sign in</UiButton>
          <UiButton variant="primary" to="/register">Get started</UiButton>
        </template>
      </div>
      <UiButton
        class="md:hidden"
        variant="ghost"
        icon-only
        :icon="open ? X : Menu"
        :aria-label="open ? 'Close menu' : 'Open menu'"
        :aria-expanded="open"
        aria-controls="mobile-nav"
        @click="open = !open"
      />
    </div>
    <div v-if="open" id="mobile-nav" class="border-t border-line bg-surface px-4 pb-5 pt-2 md:hidden">
      <nav class="flex flex-col" aria-label="Mobile">
        <router-link v-for="l in links" :key="l.to" :to="l.to" class="rounded px-3 py-3 text-md font-medium text-fg hover:bg-canvas-subtle" @click="open = false">
          {{ l.label }}
        </router-link>
      </nav>
      <div class="mt-3 grid gap-2">
        <UiButton v-if="authStore.isAuthenticated" variant="primary" size="lg" block :to="homeFor(authStore.isMasterAdmin)">
          {{ authStore.isMasterAdmin ? "Open admin console" : "Open my files" }}
        </UiButton>
        <template v-else>
          <UiButton variant="primary" size="lg" block to="/register">Get started</UiButton>
          <UiButton size="lg" block to="/login">Sign in</UiButton>
        </template>
      </div>
    </div>
  </header>
</template>

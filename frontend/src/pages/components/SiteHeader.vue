<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Menu, X } from "lucide-vue-next";
import AppLogo from "../../components/AppLogo.vue";
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
  <header class="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur">
    <div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
      <router-link to="/" aria-label="SmartSpace home"><AppLogo /></router-link>
      <nav class="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex" aria-label="Main">
        <router-link v-for="l in links" :key="l.to" :to="l.to" class="hover:text-slate-900">{{ l.label }}</router-link>
      </nav>
      <div class="hidden items-center gap-2 md:flex">
        <template v-if="authStore.isAuthenticated">
          <router-link :to="homeFor(authStore.isMasterAdmin)" class="btn-primary">Open my files</router-link>
        </template>
        <template v-else>
          <router-link to="/login" class="btn-ghost">Sign in</router-link>
          <router-link to="/register" class="btn-primary">Get started</router-link>
        </template>
      </div>
      <button class="icon-btn md:hidden" :aria-expanded="open" :aria-label="open ? 'Close menu' : 'Open menu'" @click="open = !open">
        <X v-if="open" class="h-5 w-5" />
        <Menu v-else class="h-5 w-5" />
      </button>
    </div>
    <div v-if="open" class="border-t border-slate-200 bg-white px-4 pb-5 pt-2 md:hidden">
      <nav class="flex flex-col" aria-label="Mobile">
        <router-link v-for="l in links" :key="l.to" :to="l.to" class="rounded-lg px-3 py-3 text-base font-medium text-slate-700 hover:bg-slate-50" @click="open = false">
          {{ l.label }}
        </router-link>
      </nav>
      <div class="mt-3 grid gap-2">
        <template v-if="authStore.isAuthenticated">
          <router-link :to="homeFor(authStore.isMasterAdmin)" class="btn-primary btn-lg">Open my files</router-link>
        </template>
        <template v-else>
          <router-link to="/register" class="btn-primary btn-lg">Get started</router-link>
          <router-link to="/login" class="btn-secondary btn-lg">Sign in</router-link>
        </template>
      </div>
    </div>
  </header>
</template>

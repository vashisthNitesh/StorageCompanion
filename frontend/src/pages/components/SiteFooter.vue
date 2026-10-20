<script setup lang="ts">
import AppLogo from "../../components/AppLogo.vue";
</script>

<template>
  <footer class="border-t border-slate-200 bg-white">
    <div class="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
      <div>
        <AppLogo size="sm" />
        <p class="mt-2 text-sm text-slate-500">Private, end-to-end encrypted cloud storage.</p>
      </div>
      <nav class="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600" aria-label="Footer">
        <router-link to="/pricing" class="hover:text-slate-900">Pricing</router-link>
        <router-link to="/security" class="hover:text-slate-900">Security</router-link>
        <router-link to="/legal" class="hover:text-slate-900">Terms & privacy</router-link>
      </nav>
      <p class="text-xs text-slate-400">© {{ new Date().getFullYear() }} SmartSpace · smartspacedata.com</p>
    </div>
  </footer>
</template>

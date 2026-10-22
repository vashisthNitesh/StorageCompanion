<script setup lang="ts">
import AppLogo from "../../components/AppLogo.vue";
</script>

<template>
  <footer class="border-t border-line bg-surface">
    <div class="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
      <div>
        <AppLogo size="sm" />
        <p class="mt-2 text-base text-fg-muted">Private, end-to-end encrypted cloud storage.</p>
      </div>
      <nav class="flex flex-wrap gap-x-6 gap-y-2 text-base text-fg-muted" aria-label="Footer">
        <router-link to="/pricing" class="hover:text-fg">Pricing</router-link>
        <router-link to="/security" class="hover:text-fg">Security</router-link>
        <router-link to="/legal" class="hover:text-fg">Terms & privacy</router-link>
      </nav>
      <p class="text-sm text-fg-subtle">© {{ new Date().getFullYear() }} SmartSpace · smartspacedata.com</p>
    </div>
  </footer>
</template>

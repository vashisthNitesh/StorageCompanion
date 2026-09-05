<script setup lang="ts">
import { onMounted } from "vue";
import { useAuthStore } from "./stores/auth";
import UploadTray from "./features/files/UploadTray.vue";

const authStore = useAuthStore();

onMounted(async () => {
  await authStore.fetchProfile();
});
</script>

<template>
  <div class="min-h-screen bg-[#080E1A] text-slate-100 flex flex-col font-sans">
    <router-view />
    <UploadTray />
  </div>
</template>

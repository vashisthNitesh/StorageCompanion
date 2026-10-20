<script setup lang="ts">
import UploadTray from "./features/files/UploadTray.vue";
import ToastHost from "./components/ToastHost.vue";
</script>

<template>
  <router-view />
  <UploadTray />
  <ToastHost />
</template>

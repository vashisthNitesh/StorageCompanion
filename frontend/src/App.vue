<script setup lang="ts">
import { TooltipProvider } from "reka-ui";
import UploadTray from "./features/files/UploadTray.vue";
import AppToaster from "./components/AppToaster.vue";
import UiConfirmHost from "./components/ui/UiConfirmHost.vue";
import ToastHost from "./components/ToastHost.vue";
</script>

<template>
  <TooltipProvider :delay-duration="300" :skip-delay-duration="200">
    <router-view />
    <UploadTray />
    <UiConfirmHost />
    <AppToaster />
    <ToastHost />
  </TooltipProvider>
</template>

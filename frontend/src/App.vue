<script setup lang="ts">
import { TooltipProvider } from "reka-ui";
import UploadPanel from "./features/files/UploadPanel.vue";
import AppToaster from "./components/AppToaster.vue";
import UiConfirmHost from "./components/ui/UiConfirmHost.vue";
</script>

<template>
  <TooltipProvider :delay-duration="300" :skip-delay-duration="200">
    <router-view />
    <UploadPanel />
    <UiConfirmHost />
    <AppToaster />
  </TooltipProvider>
</template>

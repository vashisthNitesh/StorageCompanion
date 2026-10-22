<script setup lang="ts">
import { onErrorCaptured, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { TooltipProvider } from "reka-ui";
import { RefreshCw, TriangleAlert } from "lucide-vue-next";
import UploadPanel from "./features/files/UploadPanel.vue";
import AppToaster from "./components/AppToaster.vue";
import OfflineBanner from "./components/OfflineBanner.vue";
import StatusScreen from "./components/StatusScreen.vue";
import UiButton from "./components/ui/UiButton.vue";
import UiConfirmHost from "./components/ui/UiConfirmHost.vue";
import { useAuthStore } from "./stores/auth";
import { homeFor } from "./router";
import { logger } from "./lib/logger";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// Error boundary: a crashing screen shows a friendly page instead of a blank app.
const crash = ref<null | "render" | "chunk">(null);
onErrorCaptured((err) => {
  logger.error(err);
  crash.value = "render";
  return false;
});
// A lazily-loaded page failed to download, usually after a new release or a dropped connection.
router.onError((err) => {
  logger.error(err);
  crash.value = "chunk";
});
watch(() => route.fullPath, () => (crash.value = null));

const reload = () => window.location.reload();

function goHome() {
  crash.value = null;
  void router.push(authStore.isAuthenticated ? homeFor(authStore.isMasterAdmin) : "/");
}
</script>

<template>
  <TooltipProvider :delay-duration="300" :skip-delay-duration="200">
    <div class="sticky top-0 z-[60]"><OfflineBanner /></div>
    <StatusScreen
      v-if="crash"
      :icon="TriangleAlert"
      :title="crash === 'chunk' ? 'This page didn’t load' : 'Something went wrong'"
      :description="
        crash === 'chunk'
          ? 'Check your connection, then reload. If SmartSpace was just updated, reloading gets the latest version.'
          : 'This screen hit an unexpected problem. Your files are safe. Reload to try again.'
      "
    >
      <UiButton variant="primary" :icon="RefreshCw" @click="reload">Reload</UiButton>
      <UiButton @click="goHome">{{ authStore.isAuthenticated && !authStore.isMasterAdmin ? "Go to My files" : "Go to home page" }}</UiButton>
    </StatusScreen>
    <router-view v-else />
    <UploadPanel />
    <UiConfirmHost />
    <AppToaster />
  </TooltipProvider>
</template>

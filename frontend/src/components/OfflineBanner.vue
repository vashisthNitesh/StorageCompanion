<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { WifiOff } from "lucide-vue-next";

const offline = ref(typeof navigator !== "undefined" && !navigator.onLine);
const set = () => (offline.value = !navigator.onLine);
onMounted(() => {
  window.addEventListener("online", set);
  window.addEventListener("offline", set);
});
onUnmounted(() => {
  window.removeEventListener("online", set);
  window.removeEventListener("offline", set);
});
</script>

<template>
  <div
    v-if="offline"
    class="flex items-center justify-center gap-2 bg-fg px-4 py-1.5 text-sm font-medium text-canvas"
    role="status"
    aria-live="polite"
  >
    <WifiOff :size="14" :stroke-width="2" aria-hidden="true" />
    You're offline. Uploads will resume when you reconnect.
  </div>
</template>

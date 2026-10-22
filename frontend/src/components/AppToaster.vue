<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { Toaster } from "vue-sonner";
import "vue-sonner/style.css";
import { useThemeStore } from "../stores/theme";
import { useUploadStore } from "../stores/upload";

const theme = useThemeStore();
const uploads = useUploadStore();
// On desktop, toasts stack above the upload panel when it's open.
const offset = computed(() =>
  isMobile.value ? 12 : { right: 24, bottom: uploads.panelHeight ? uploads.panelHeight + 32 : 24 }
);
const isMobile = ref(false);
let mq: MediaQueryList | null = null;
const update = () => (isMobile.value = !!mq?.matches);
onMounted(() => {
  mq = window.matchMedia("(max-width: 639px)");
  update();
  mq.addEventListener("change", update);
});
onUnmounted(() => mq?.removeEventListener("change", update));

// Map sonner's colour variables onto our tokens so toasts follow light/dark themes.
const style = computed(() => ({
  "--normal-bg": "rgb(var(--surface-raised))",
  "--normal-border": "rgb(var(--border))",
  "--normal-text": "rgb(var(--text))",
  "--success-bg": "rgb(var(--surface-raised))",
  "--success-border": "rgb(var(--border))",
  "--success-text": "rgb(var(--text))",
  "--error-bg": "rgb(var(--surface-raised))",
  "--error-border": "rgb(var(--danger) / 0.35)",
  "--error-text": "rgb(var(--text))",
  "--info-bg": "rgb(var(--surface-raised))",
  "--info-border": "rgb(var(--border))",
  "--info-text": "rgb(var(--text))",
  "--border-radius": "10px",
  fontFamily: "inherit",
}));
</script>

<template>
  <Toaster
    :position="isMobile ? 'top-center' : 'bottom-right'"
    :visible-toasts="3"
    :theme="theme.preference"
    :close-button="true"
    :style="style"
    :toast-options="{ class: 'sc-toast' }"
    :offset="offset"
  />
</template>

<style>
.sc-toast {
  font-size: 14px !important;
  box-shadow: 0 6px 16px -4px rgb(var(--shadow-color) / 0.16) !important;
}
.sc-toast [data-icon] svg { width: 18px; height: 18px; }
.sc-toast[data-type="success"] [data-icon] { color: rgb(var(--success)); }
.sc-toast[data-type="error"] [data-icon] { color: rgb(var(--danger)); }
.sc-toast[data-type="info"] [data-icon] { color: rgb(var(--primary)); }
.sc-toast [data-description] { color: rgb(var(--text-muted)) !important; }
.sc-toast [data-button] {
  background: rgb(var(--primary-soft)) !important;
  color: rgb(var(--primary-soft-fg)) !important;
  font-weight: 600 !important;
  border-radius: 6px !important;
}
</style>

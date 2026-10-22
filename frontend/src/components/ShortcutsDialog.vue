<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import UiModal from "./ui/UiModal.vue";
import UiKbd from "./ui/UiKbd.vue";
import { onAppEvent } from "../lib/events";
import { modKey } from "../composables/useMediaQuery";

const open = ref(false);
let off: (() => void) | null = null;
onMounted(() => (off = onAppEvent("shortcuts-help", () => (open.value = true))));
onUnmounted(() => off?.());

const groups = [
  {
    title: "Anywhere",
    items: [
      { keys: [modKey, "K"], label: "Search and commands" },
      { keys: ["/"], label: "Search files" },
      { keys: ["U"], label: "Upload files" },
      { keys: ["N"], label: "New folder" },
      { keys: ["?"], label: "Show keyboard shortcuts" },
    ],
  },
  {
    title: "In a file list",
    items: [
      { keys: ["↑", "↓"], label: "Move between items" },
      { keys: ["Enter"], label: "Open folder / download file" },
      { keys: ["Space"], label: "Select item" },
      { keys: ["Shift", "↑↓"], label: "Extend selection" },
      { keys: [modKey, "A"], label: "Select all" },
      { keys: ["F2"], label: "Rename" },
      { keys: ["Shift", "F10"], label: "Open item menu" },
      { keys: ["Delete"], label: "Move to trash" },
      { keys: ["Esc"], label: "Clear selection" },
    ],
  },
];
</script>

<template>
  <UiModal v-model:open="open" title="Keyboard shortcuts" size="md">
    <div class="space-y-6">
      <section v-for="g in groups" :key="g.title">
        <h3 class="text-sm font-medium text-fg-subtle">{{ g.title }}</h3>
        <ul class="mt-2 divide-y divide-line">
          <li v-for="item in g.items" :key="item.label" class="flex items-center justify-between py-2 text-base text-fg">
            {{ item.label }}
            <span class="flex gap-1"><UiKbd v-for="k in item.keys" :key="k">{{ k }}</UiKbd></span>
          </li>
        </ul>
      </section>
    </div>
  </UiModal>
</template>

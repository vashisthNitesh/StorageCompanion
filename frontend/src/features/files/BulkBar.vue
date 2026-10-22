<script setup lang="ts">
import { Download, FolderInput, Pencil, Trash2, X } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";

defineProps<{ count: number; canDownload: boolean }>();
const emit = defineEmits<{ download: []; move: []; rename: []; trash: []; clear: [] }>();
</script>

<template>
  <Transition enter-active-class="animate-slide-up" leave-active-class="animate-fade-out">
    <div
      v-if="count > 0"
      class="fixed inset-x-0 bottom-0 z-30 flex items-center gap-1 border-t border-line bg-surface-raised px-3 py-2 shadow-xl sm:inset-x-auto sm:bottom-6 sm:left-1/2 sm:-translate-x-1/2 sm:rounded-xl sm:border"
      role="toolbar"
      aria-label="Selection actions"
    >
      <span class="tabular px-2 text-base font-medium text-fg" aria-live="polite">{{ count }} selected</span>
      <span class="mx-1 h-5 w-px bg-line" aria-hidden="true" />
      <UiButton v-if="canDownload" variant="ghost" size="sm" :icon="Download" aria-label="Download selected" @click="emit('download')"><span class="hidden sm:inline">Download</span></UiButton>
      <UiButton variant="ghost" size="sm" :icon="FolderInput" aria-label="Move selected" @click="emit('move')"><span class="hidden sm:inline">Move</span></UiButton>
      <UiButton v-if="count === 1" variant="ghost" size="sm" :icon="Pencil" aria-label="Rename" tooltip="Rename" shortcut="F2" @click="emit('rename')"><span class="hidden sm:inline">Rename</span></UiButton>
      <UiButton variant="danger-ghost" size="sm" :icon="Trash2" aria-label="Move selected to trash" @click="emit('trash')"><span class="hidden sm:inline">Move to trash</span></UiButton>
      <span class="mx-1 h-5 w-px bg-line" aria-hidden="true" />
      <UiButton variant="ghost" size="sm" icon-only :icon="X" aria-label="Clear selection" shortcut="Esc" @click="emit('clear')" />
    </div>
  </Transition>
</template>

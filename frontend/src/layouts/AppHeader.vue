<script setup lang="ts">
import { computed } from "vue";
import { Menu, Search, HelpCircle } from "lucide-vue-next";
import UiButton from "../components/ui/UiButton.vue";
import UiKbd from "../components/ui/UiKbd.vue";
import UiProgressCircle from "../components/ui/UiProgressCircle.vue";
import UiTooltip from "../components/ui/UiTooltip.vue";
import UserMenu from "./UserMenu.vue";
import { useAuthStore } from "../stores/auth";
import { useUploadStore } from "../stores/upload";
import { emitAppEvent } from "../lib/events";
import { modKey } from "../composables/useMediaQuery";

defineProps<{ showMenuButton: boolean }>();
const emit = defineEmits<{ openNav: []; signOut: [] }>();
const authStore = useAuthStore();
const uploadStore = useUploadStore();
const uploading = computed(() => uploadStore.activeCount > 0);
</script>

<template>
  <header class="flex h-14 shrink-0 items-center gap-2 border-b border-line bg-surface px-3 sm:px-5">
    <UiButton v-if="showMenuButton" variant="ghost" icon-only :icon="Menu" aria-label="Open navigation" @click="emit('openNav')" />

    <div class="min-w-0 flex-1">
      <button
        v-if="!authStore.isMasterAdmin"
        type="button"
        class="group flex h-9 w-full max-w-md items-center gap-2.5 rounded border border-transparent bg-canvas-subtle px-3 text-left text-base text-fg-subtle transition-colors hover:border-line hover:bg-surface"
        aria-label="Search files and commands"
        aria-keyshortcuts="Meta+K Control+K"
        @click="emitAppEvent('command-palette')"
      >
        <Search :size="16" :stroke-width="1.75" aria-hidden="true" />
        <span class="flex-1 truncate">Search files and folders</span>
        <span class="hidden gap-0.5 sm:flex"><UiKbd>{{ modKey }}</UiKbd><UiKbd>K</UiKbd></span>
      </button>
    </div>

    <UiTooltip v-if="uploading" :content="`Uploading ${uploadStore.activeCount} ${uploadStore.activeCount === 1 ? 'file' : 'files'} · ${uploadStore.totalProgress}%`">
      <button
        type="button"
        class="flex h-9 items-center gap-2 rounded px-2 text-sm font-medium text-primary hover:bg-canvas-subtle"
        :aria-label="`Uploads ${uploadStore.totalProgress}% complete. Show uploads`"
        @click="uploadStore.showPanel()"
      >
        <UiProgressCircle :value="uploadStore.totalProgress" :size="18" />
        <span class="tabular hidden sm:inline">{{ uploadStore.totalProgress }}%</span>
      </button>
    </UiTooltip>
    <UiButton variant="ghost" icon-only :icon="HelpCircle" aria-label="Keyboard shortcuts and help" shortcut="?" @click="emitAppEvent('shortcuts-help')" />
    <UserMenu @sign-out="emit('signOut')" />
  </header>
</template>

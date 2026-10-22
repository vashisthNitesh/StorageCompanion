<script setup lang="ts">
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription, DialogClose } from "reka-ui";
import { X } from "lucide-vue-next";

const open = defineModel<boolean>("open", { default: false });
withDefaults(defineProps<{ title: string; description?: string; side?: "right" | "left"; width?: string }>(), {
  side: "right",
  width: "max-w-md",
});
</script>

<template>
  <DialogRoot v-model:open="open">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-overlay/40 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
      <DialogContent
        class="fixed inset-y-0 z-50 flex w-full flex-col border-line bg-surface-raised shadow-xl focus:outline-none"
        :class="[side === 'right' ? 'right-0 border-l data-[state=open]:animate-slide-in-right' : 'left-0 border-r data-[state=open]:animate-slide-in-left', width]"
      >
        <div class="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div class="min-w-0">
            <DialogTitle class="truncate text-md font-semibold text-fg">{{ title }}</DialogTitle>
            <DialogDescription v-if="description" class="mt-0.5 text-sm text-fg-muted">{{ description }}</DialogDescription>
          </div>
          <DialogClose class="flex h-8 w-8 shrink-0 items-center justify-center rounded text-fg-subtle hover:bg-canvas-subtle hover:text-fg" aria-label="Close">
            <X :size="18" :stroke-width="1.75" />
          </DialogClose>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5 scrollbar-thin">
          <slot />
        </div>
        <div v-if="$slots.footer" class="flex gap-2 border-t border-line px-5 py-4">
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

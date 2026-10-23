<script setup lang="ts">
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "reka-ui";
import { X } from "lucide-vue-next";
import { cn } from "./cn";

const open = defineModel<boolean>("open", { default: false });
withDefaults(
  defineProps<{
    title: string;
    description?: string;
    size?: "sm" | "md" | "lg" | "xl";
    /** When false, Esc / outside click don't close (e.g. while an action is running). */
    dismissible?: boolean;
    hideTitle?: boolean;
    bodyClass?: string;
  }>(),
  { size: "md", dismissible: true }
);
const emit = defineEmits<{ close: [] }>();

// Focus the first field (or an [autofocus] element) instead of the close button.
function focusFirstField(e: Event) {
  const root = e.target as HTMLElement | null;
  const target =
    root?.querySelector<HTMLElement>("[autofocus]") ??
    root?.querySelector<HTMLElement>("[data-modal-body] input:not([type=hidden]):not([disabled]), [data-modal-body] textarea, [data-modal-body] [role=combobox]");
  if (target) {
    e.preventDefault();
    target.focus();
  }
}

function onOpenChange(value: boolean) {
  open.value = value;
  if (!value) emit("close");
}
</script>

<template>
  <DialogRoot :open="open" @update:open="onOpenChange">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-overlay/50 backdrop-blur-[1px] data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
      <DialogContent
        :class="
          cn(
            'fixed z-50 flex max-h-[92dvh] w-full flex-col border border-line bg-surface-raised shadow-xl focus:outline-none',
            'inset-x-0 bottom-0 rounded-t-xl data-[state=open]:animate-slide-up',
            'sm:inset-x-auto sm:bottom-auto sm:left-1/2 sm:top-[12vh] sm:max-h-[80dvh] sm:-translate-x-1/2 sm:rounded-xl sm:data-[state=open]:animate-scale-in',
            { sm: 'sm:max-w-sm', md: 'sm:max-w-md', lg: 'sm:max-w-xl', xl: 'sm:max-w-3xl' }[size]
          )
        "
        @open-auto-focus="focusFirstField"
        @escape-key-down="(e: Event) => !dismissible && e.preventDefault()"
        @pointer-down-outside="(e: Event) => !dismissible && e.preventDefault()"
        @interact-outside="(e: Event) => !dismissible && e.preventDefault()"
      >
        <div class="flex items-start justify-between gap-4 px-5 pb-2 pt-5" :class="{ 'sr-only': hideTitle }">
          <div class="min-w-0">
            <DialogTitle class="text-md font-semibold text-fg">{{ title }}</DialogTitle>
            <DialogDescription v-if="description" class="mt-1 text-base text-fg-muted">{{ description }}</DialogDescription>
          </div>
          <DialogClose
            v-if="dismissible"
            class="-mr-1.5 -mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded text-fg-subtle hover:bg-canvas-subtle hover:text-fg"
            aria-label="Close"
          >
            <X :size="18" :stroke-width="1.75" />
          </DialogClose>
        </div>
        <div data-modal-body :class="cn('min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-2 scrollbar-thin', bodyClass)">
          <slot />
        </div>
        <div v-if="$slots.footer" class="flex flex-col-reverse gap-2 border-t border-line px-5 py-4 sm:flex-row sm:justify-end">
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

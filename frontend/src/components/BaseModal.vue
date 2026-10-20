<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick, watch } from "vue";
import { X } from "lucide-vue-next";

const props = withDefaults(defineProps<{ open: boolean; title: string; size?: "sm" | "md" | "lg"; dismissible?: boolean }>(), {
  size: "md",
  dismissible: true,
});
const emit = defineEmits<{ close: [] }>();
const panel = ref<HTMLElement | null>(null);

function onKey(e: KeyboardEvent) {
  if (props.open && props.dismissible && e.key === "Escape") emit("close");
}

watch(
  () => props.open,
  async (open) => {
    if (!open) return;
    await nextTick();
    const focusable = panel.value?.querySelector<HTMLElement>("[autofocus], input, select, textarea, button:not([data-close])");
    focusable?.focus();
  },
  { immediate: true }
);

onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-900/50 p-0 sm:p-4" @click.self="dismissible && emit('close')">
        <div
          ref="panel"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          class="w-full bg-white shadow-pop rounded-t-2xl sm:rounded-2xl max-h-[92vh] flex flex-col"
          :class="size === 'sm' ? 'sm:max-w-sm' : size === 'lg' ? 'sm:max-w-2xl' : 'sm:max-w-md'"
        >
          <div class="flex items-center justify-between gap-4 px-5 pt-5 pb-3">
            <h2 class="text-base font-semibold text-slate-900">{{ title }}</h2>
            <button v-if="dismissible" type="button" data-close class="icon-btn -mr-2" aria-label="Close" @click="emit('close')">
              <X class="h-5 w-5" />
            </button>
          </div>
          <div class="px-5 pb-5 overflow-y-auto">
            <slot />
          </div>
          <div v-if="$slots.footer" class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 border-t border-slate-100 px-5 py-4">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

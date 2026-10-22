<script setup lang="ts">
import { computed, ref } from "vue";
import { Search, X } from "lucide-vue-next";
import UiKbd from "./UiKbd.vue";
import { inputClasses } from "./inputClasses";

defineOptions({ inheritAttrs: false });
const model = defineModel<string>({ default: "" });
const props = withDefaults(defineProps<{ placeholder?: string; shortcut?: boolean; size?: "sm" | "md" | "lg" }>(), {
  placeholder: "Search",
  size: "md",
});
const emit = defineEmits<{ clear: [] }>();
const el = ref<HTMLInputElement | null>(null);
const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);
const hint = computed(() => (isMac ? "⌘K" : "Ctrl K"));

function clear() {
  model.value = "";
  emit("clear");
  el.value?.focus();
}
defineExpose({ focus: () => el.value?.focus() });
</script>

<template>
  <div class="relative" :class="$attrs.class as string">
    <Search :size="16" :stroke-width="1.75" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle" aria-hidden="true" />
    <input
      ref="el"
      v-model="model"
      v-bind="{ ...$attrs, class: undefined }"
      type="search"
      :placeholder="placeholder"
      :class="inputClasses({ size: props.size, extra: 'pl-9 pr-16 bg-canvas-subtle hover:bg-surface focus:bg-surface border-transparent hover:border-line' })"
      @keydown.esc="model ? clear() : ($event.target as HTMLInputElement).blur()"
    />
    <div class="absolute inset-y-0 right-2 flex items-center gap-1">
      <button
        v-if="model"
        type="button"
        class="rounded p-1 text-fg-subtle hover:bg-canvas-subtle hover:text-fg"
        aria-label="Clear search"
        @click="clear"
      >
        <X :size="14" :stroke-width="2" />
      </button>
      <UiKbd v-else-if="shortcut" aria-hidden="true">{{ hint }}</UiKbd>
    </div>
  </div>
</template>

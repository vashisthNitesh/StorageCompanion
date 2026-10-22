<script setup lang="ts">
import { computed } from "vue";
import { ChevronRight, MoreHorizontal, Folder } from "lucide-vue-next";
import UiDropdownMenu from "./UiDropdownMenu.vue";
import type { MenuEntry } from "./menuTypes";

export interface Crumb {
  key: string;
  label: string;
}
const props = withDefaults(defineProps<{ items: Crumb[]; maxVisible?: number }>(), { maxVisible: 4 });
const emit = defineEmits<{ navigate: [index: number] }>();

// Keep the root and the last two levels visible; tuck the middle into an overflow menu.
const layout = computed(() => {
  const items = props.items.map((c, index) => ({ ...c, index }));
  if (items.length <= props.maxVisible) return { head: items, hidden: [], tail: [] as typeof items };
  return { head: items.slice(0, 1), hidden: items.slice(1, -2), tail: items.slice(-2) };
});
const hiddenMenu = computed<MenuEntry[]>(() =>
  layout.value.hidden.map((c) => ({ label: c.label, icon: Folder, onSelect: () => emit("navigate", c.index) }))
);
const visible = computed(() => [...layout.value.head, ...layout.value.tail]);
</script>

<template>
  <nav aria-label="Folder path" class="min-w-0">
    <ol class="flex min-w-0 items-center gap-0.5 text-lg font-semibold text-fg">
      <template v-for="(c, i) in visible" :key="c.key">
        <li v-if="i === layout.head.length && layout.hidden.length" class="flex items-center gap-0.5">
          <ChevronRight :size="16" class="shrink-0 text-fg-subtle" aria-hidden="true" />
          <UiDropdownMenu :items="hiddenMenu" align="start">
            <button class="flex h-8 w-8 items-center justify-center rounded text-fg-muted hover:bg-canvas-subtle" aria-label="Show hidden folders">
              <MoreHorizontal :size="18" :stroke-width="1.75" />
            </button>
          </UiDropdownMenu>
        </li>
        <li class="flex min-w-0 items-center gap-0.5">
          <ChevronRight v-if="i > 0" :size="16" class="shrink-0 text-fg-subtle" aria-hidden="true" />
          <button
            v-if="c.index < items.length - 1"
            class="max-w-[14rem] truncate rounded px-1.5 py-0.5 text-fg-muted hover:bg-canvas-subtle hover:text-fg"
            @click="emit('navigate', c.index)"
          >
            {{ c.label }}
          </button>
          <span v-else class="min-w-0 truncate px-1.5" aria-current="page">{{ c.label }}</span>
        </li>
      </template>
    </ol>
  </nav>
</template>

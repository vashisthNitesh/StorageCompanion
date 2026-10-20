<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from "vue";
import { Download, FolderOpen, Pencil, FolderInput, History, Trash2, FileUp } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";

export type ItemAction = "open" | "download" | "rename" | "move" | "versions" | "new-version" | "trash";

const props = defineProps<{ node: FileNode | null; x: number; y: number }>();
const emit = defineEmits<{ select: [action: ItemAction]; close: [] }>();
const menu = ref<HTMLElement | null>(null);
const pos = ref({ left: 0, top: 0 });

const items = computed(() => {
  if (!props.node) return [];
  const isFile = props.node.type === "file";
  return [
    isFile
      ? { action: "download" as const, label: "Download", icon: Download }
      : { action: "open" as const, label: "Open", icon: FolderOpen },
    { action: "rename" as const, label: "Rename", icon: Pencil },
    { action: "move" as const, label: "Move to…", icon: FolderInput },
    ...(isFile
      ? [
          { action: "new-version" as const, label: "Upload new version", icon: FileUp },
          { action: "versions" as const, label: "Version history", icon: History },
        ]
      : []),
    { action: "trash" as const, label: "Move to trash", icon: Trash2, danger: true },
  ];
});

watch(
  () => [props.node, props.x, props.y],
  async () => {
    if (!props.node) return;
    await nextTick();
    const el = menu.value;
    const w = el?.offsetWidth || 220;
    const h = el?.offsetHeight || 240;
    pos.value = {
      left: Math.max(8, Math.min(props.x, window.innerWidth - w - 8)),
      top: props.y + h > window.innerHeight - 8 ? Math.max(8, props.y - h) : props.y,
    };
    el?.querySelector<HTMLElement>("button")?.focus();
  },
  { immediate: true }
);

function onKey(e: KeyboardEvent) {
  if (!props.node) return;
  if (e.key === "Escape") emit("close");
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const buttons = Array.from(menu.value?.querySelectorAll<HTMLElement>("button") || []);
    const i = buttons.indexOf(document.activeElement as HTMLElement);
    buttons[(i + (e.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus();
  }
}
function onPointer(e: Event) {
  if (props.node && !menu.value?.contains(e.target as Node)) emit("close");
}
const onResize = () => emit("close");
onMounted(() => {
  window.addEventListener("keydown", onKey);
  window.addEventListener("pointerdown", onPointer, true);
  window.addEventListener("resize", onResize);
});
onUnmounted(() => {
  window.removeEventListener("keydown", onKey);
  window.removeEventListener("pointerdown", onPointer, true);
  window.removeEventListener("resize", onResize);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="node"
      ref="menu"
      role="menu"
      class="fixed z-50 w-56 rounded-xl border border-slate-200 bg-white p-1.5 shadow-pop"
      :style="{ left: `${pos.left}px`, top: `${pos.top}px` }"
    >
      <button
        v-for="item in items"
        :key="item.action"
        role="menuitem"
        class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm focus:outline-none"
        :class="'danger' in item ? 'text-rose-600 hover:bg-rose-50 focus:bg-rose-50' : 'text-slate-700 hover:bg-slate-100 focus:bg-slate-100'"
        @click="emit('select', item.action)"
      >
        <component :is="item.icon" class="h-4 w-4" />
        {{ item.label }}
      </button>
    </div>
  </Teleport>
</template>

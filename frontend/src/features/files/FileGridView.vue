<script setup lang="ts">
import { MoreHorizontal } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiDropdownMenu from "../../components/ui/UiDropdownMenu.vue";
import UiContextMenu from "../../components/ui/UiContextMenu.vue";
import UiProgressCircle from "../../components/ui/UiProgressCircle.vue";
import type { MenuEntry } from "../../components/ui/menuTypes";
import { formatBytes, formatRelative } from "../../lib/format";
import FileThumb from "../preview/FileThumb.vue";
import { useFileDownload } from "./useFileDownload";

defineProps<{
  items: FileNode[];
  selected: Set<string>;
  focusedId: string | null;
  highlightIds: Set<string>;
  menuFor: (node: FileNode) => MenuEntry[];
  listLabel: string;
}>();
const emit = defineEmits<{
  click: [node: FileNode, e: MouseEvent];
  toggle: [node: FileNode];
  open: [node: FileNode];
  keydown: [e: KeyboardEvent];
}>();
/** Right-clicking an unselected item selects it first, like a desktop file manager. */
function selectForMenu(node: FileNode) {
  emit("click", node, new MouseEvent("click"));
}
const { isDownloading, progressOf } = useFileDownload();
</script>

<template>
  <div
    role="listbox"
    aria-multiselectable="true"
    :aria-label="listLabel"
    :aria-activedescendant="focusedId ? `row-${focusedId}` : undefined"
    tabindex="0"
    class="grid grid-cols-2 gap-3 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-4 focus-visible:ring-offset-canvas sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
    @keydown="emit('keydown', $event)"
  >
    <UiContextMenu v-for="node in items" :key="node.id" :items="menuFor(node)" @open="!selected.has(node.id) && selectForMenu(node)">
      <div
        :id="`row-${node.id}`"
        role="option"
        :aria-selected="selected.has(node.id)"
        class="group relative flex cursor-default select-none flex-col rounded-lg border bg-surface p-2 transition-[border-color,box-shadow] duration-fast"
        :class="[
          selected.has(node.id) ? 'border-primary ring-1 ring-primary' : 'border-line hover:border-line-strong hover:shadow-sm',
          focusedId === node.id && !selected.has(node.id) ? 'border-line-strong' : '',
          highlightIds.has(node.id) ? 'animate-row-flash' : '',
        ]"
        @click="emit('click', node, $event)"
        @dblclick="emit('open', node)"
      >
        <div class="relative aspect-[4/3] overflow-hidden rounded">
          <FileThumb :node="node" variant="card" />
          <span v-if="isDownloading(node)" class="absolute bottom-2 right-2 rounded-full bg-surface p-1 text-primary shadow-sm" role="status" :aria-label="`Downloading ${progressOf(node)}%`">
            <UiProgressCircle :value="progressOf(node)" :size="18" />
          </span>
          <UiCheckbox
            :model-value="selected.has(node.id)"
            :aria-label="`Select ${node.name}`"
            class="absolute left-2 top-2 rounded-sm bg-surface opacity-0 group-hover:opacity-100 focus-within:opacity-100"
            :class="{ '!opacity-100': selected.size > 0 }"
            @update:model-value="emit('toggle', node)"
          />
        </div>
        <div class="mt-2 flex items-start gap-1 px-1">
          <div class="min-w-0 flex-1">
            <p class="line-clamp-2 break-words text-base leading-5 text-fg">{{ node.name }}</p>
            <p class="tabular mt-0.5 truncate text-xs text-fg-subtle">
              {{ node.type === "folder" ? "Folder" : formatBytes(node.size_bytes) }} · {{ formatRelative(node.updated_at) }}
            </p>
          </div>
          <UiDropdownMenu :items="menuFor(node)">
            <UiButton
              variant="ghost"
              size="sm"
              icon-only
              :icon="MoreHorizontal"
              :aria-label="`More actions for ${node.name}`"
              class="-mr-1 shrink-0 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:data-[state=open]:opacity-100"
              @click.stop
              @dblclick.stop
            />
          </UiDropdownMenu>
        </div>
      </div>
    </UiContextMenu>
  </div>
</template>

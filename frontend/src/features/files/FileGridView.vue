<script setup lang="ts">
import { computed } from "vue";
import { MoreVertical, Folder } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiDropdownMenu from "../../components/ui/UiDropdownMenu.vue";
import UiContextMenu from "../../components/ui/UiContextMenu.vue";
import UiProgressCircle from "../../components/ui/UiProgressCircle.vue";
import type { MenuEntry } from "../../components/ui/menuTypes";
import { formatBytes, formatRelative } from "../../lib/format";
import FileThumb from "../preview/FileThumb.vue";
import { extensionOf } from "../preview/previewTypes";
import { kindIconColor, kindInfo, kindOf } from "./fileTypes";
import { useFileDownload } from "./useFileDownload";

const props = defineProps<{
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

// Folders sit in a compact row of tiles above the file cards, like most file managers.
// Both groups share one listbox so keyboard navigation runs through every item.
const folders = computed(() => props.items.filter((n) => n.type === "folder"));
const files = computed(() => props.items.filter((n) => n.type !== "folder"));
const selecting = computed(() => props.selected.size > 0);
/** Short stagger on first paint; capped so long folders don't wait. */
const delay = (i: number) => ({ animationDelay: `${Math.min(i, 12) * 20}ms` });
/** "PDF", "MP4"… or the kind ("Document") when there's no short extension. */
const typeLabel = (node: FileNode) => {
  const ext = extensionOf(node.name).toUpperCase();
  return ext && ext.length <= 5 ? ext : kindInfo(kindOf(node)).label;
};

const GRID = "grid grid-cols-2 gap-3 sm:grid-cols-[repeat(auto-fill,minmax(210px,1fr))] sm:gap-4";
// Folder tiles are just a name, so narrow phones list them in one column to keep names readable.
const FOLDER_GRID = "grid grid-cols-1 gap-2 min-[420px]:grid-cols-2 sm:grid-cols-[repeat(auto-fill,minmax(210px,1fr))] sm:gap-4";
const TILE = "group relative cursor-default select-none rounded-xl transition-[background-color,box-shadow] duration-fast";
const tileState = (node: FileNode) => [
  props.selected.has(node.id) ? "bg-primary-soft ring-1 ring-primary/40" : "bg-tile hover:bg-tile-hover",
  props.focusedId === node.id ? "ring-2 ring-primary/60" : "",
  props.highlightIds.has(node.id) ? "animate-row-flash" : "",
];
// The type icon turns into the checkbox on hover, and stays one while anything is selected.
const iconSlot = "flex h-5 w-5 shrink-0 items-center justify-center";
const showCheck = (node: FileNode) => selecting.value || props.selected.has(node.id);
</script>

<template>
  <div
    role="listbox"
    aria-multiselectable="true"
    :aria-label="listLabel"
    :aria-activedescendant="focusedId ? `row-${focusedId}` : undefined"
    tabindex="0"
    class="space-y-6 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-4 focus-visible:ring-offset-canvas"
    @keydown="emit('keydown', $event)"
  >
    <!-- Folders -->
    <section v-if="folders.length" role="group" aria-labelledby="grid-folders">
      <h2 id="grid-folders" class="mb-2.5 text-sm font-medium text-fg-muted">Folders</h2>
      <div :class="FOLDER_GRID" data-grid>
        <UiContextMenu v-for="(node, i) in folders" :key="node.id" :items="menuFor(node)" @open="!selected.has(node.id) && selectForMenu(node)">
          <div
            :id="`row-${node.id}`"
            role="option"
            :aria-selected="selected.has(node.id)"
            :class="[TILE, tileState(node), 'flex h-12 animate-card-in items-center gap-3 pl-3.5 pr-1']"
            :style="delay(i)"
            @click="emit('click', node, $event)"
            @dblclick="emit('open', node)"
          >
            <span :class="iconSlot">
              <Folder
                v-if="!showCheck(node)"
                :size="20"
                :stroke-width="1.75"
                class="text-amber-500 group-hover:hidden"
                fill="currentColor"
                fill-opacity="0.3"
                aria-hidden="true"
              />
              <UiCheckbox
                :model-value="selected.has(node.id)"
                :aria-label="`Select ${node.name}`"
                class="[&>button]:mt-0"
                :class="showCheck(node) ? '' : 'hidden focus-within:flex group-hover:flex'"
                @update:model-value="emit('toggle', node)"
              />
            </span>
            <p class="min-w-0 flex-1 truncate text-base font-medium text-fg">{{ node.name }}</p>
            <UiDropdownMenu :items="menuFor(node)">
              <UiButton
                variant="ghost"
                size="sm"
                icon-only
                :icon="MoreVertical"
                :aria-label="`More actions for ${node.name}`"
                class="shrink-0 rounded-full md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:data-[state=open]:opacity-100"
                @click.stop
                @dblclick.stop
              />
            </UiDropdownMenu>
          </div>
        </UiContextMenu>
      </div>
    </section>

    <!-- Files -->
    <section v-if="files.length" role="group" aria-labelledby="grid-files">
      <h2 v-if="folders.length" id="grid-files" class="mb-2.5 text-sm font-medium text-fg-muted">Files</h2>
      <h2 v-else id="grid-files" class="sr-only">Files</h2>
      <div :class="GRID" data-grid>
        <UiContextMenu v-for="(node, i) in files" :key="node.id" :items="menuFor(node)" @open="!selected.has(node.id) && selectForMenu(node)">
          <div
            :id="`row-${node.id}`"
            role="option"
            :aria-selected="selected.has(node.id)"
            :class="[TILE, tileState(node), 'flex animate-card-in flex-col px-1.5 pb-1.5']"
            :style="delay(folders.length + i)"
            @click="emit('click', node, $event)"
            @dblclick="emit('open', node)"
          >
            <!-- Header: type icon (checkbox on hover), name, menu -->
            <div class="flex h-11 items-center gap-2.5 pl-2">
              <span :class="iconSlot">
                <component
                  :is="kindInfo(kindOf(node)).icon"
                  v-if="!showCheck(node)"
                  :size="18"
                  :stroke-width="1.85"
                  class="group-hover:hidden"
                  :class="kindIconColor(kindOf(node))"
                  aria-hidden="true"
                />
                <UiCheckbox
                  :model-value="selected.has(node.id)"
                  :aria-label="`Select ${node.name}`"
                  class="[&>button]:mt-0"
                  :class="showCheck(node) ? '' : 'hidden focus-within:flex group-hover:flex'"
                  @update:model-value="emit('toggle', node)"
                />
              </span>
              <p class="min-w-0 flex-1 truncate text-base font-medium text-fg">{{ node.name }}</p>
              <UiDropdownMenu :items="menuFor(node)">
                <UiButton
                  variant="ghost"
                  size="sm"
                  icon-only
                  :icon="MoreVertical"
                  :aria-label="`More actions for ${node.name}`"
                  class="shrink-0 rounded-full md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:data-[state=open]:opacity-100"
                  @click.stop
                  @dblclick.stop
                />
              </UiDropdownMenu>
            </div>

            <!-- Preview -->
            <div class="relative aspect-[4/3] overflow-hidden rounded-lg bg-surface-sunken">
              <FileThumb :node="node" variant="card" />
              <span v-if="isDownloading(node)" class="absolute right-2 top-2 rounded-full bg-surface p-1 text-primary shadow-sm" role="status" :aria-label="`Downloading ${progressOf(node)}%`">
                <UiProgressCircle :value="progressOf(node)" :size="18" />
              </span>
            </div>

            <!-- Footer -->
            <p class="tabular flex items-center justify-between gap-2 px-1.5 pt-2 text-xs text-fg-subtle">
              <span class="truncate">{{ typeLabel(node) }} · {{ formatBytes(node.size_bytes) }}</span>
              <span class="hidden shrink-0 sm:inline">{{ formatRelative(node.updated_at) }}</span>
            </p>
          </div>
        </UiContextMenu>
      </div>
    </section>
  </div>
</template>

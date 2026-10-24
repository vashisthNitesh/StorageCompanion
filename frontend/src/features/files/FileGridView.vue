<script setup lang="ts">
import { computed } from "vue";
import { MoreHorizontal, Folder } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiDropdownMenu from "../../components/ui/UiDropdownMenu.vue";
import UiContextMenu from "../../components/ui/UiContextMenu.vue";
import UiProgressCircle from "../../components/ui/UiProgressCircle.vue";
import type { MenuEntry } from "../../components/ui/menuTypes";
import { formatBytes, formatRelative } from "../../lib/format";
import FileThumb from "../preview/FileThumb.vue";
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
/** Short stagger on first paint; capped so long folders don't wait. */
const delay = (i: number) => ({ animationDelay: `${Math.min(i, 12) * 25}ms` });
const GRID = "grid gap-3 grid-cols-2 sm:grid-cols-[repeat(auto-fill,minmax(200px,1fr))]";
const FOLDER_GRID = "grid gap-2 grid-cols-1 min-[420px]:grid-cols-2 sm:grid-cols-[repeat(auto-fill,minmax(200px,1fr))] sm:gap-3";
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
      <h2 id="grid-folders" class="mb-2 text-sm font-medium text-fg-muted">Folders</h2>
      <div :class="FOLDER_GRID" data-grid>
        <UiContextMenu v-for="(node, i) in folders" :key="node.id" :items="menuFor(node)" @open="!selected.has(node.id) && selectForMenu(node)">
          <div
            :id="`row-${node.id}`"
            role="option"
            :aria-selected="selected.has(node.id)"
            class="group relative flex h-14 animate-card-in cursor-default select-none items-center gap-3 rounded-lg border bg-surface pl-3 pr-1 transition-[border-color,box-shadow,background-color] duration-fast"
            :class="[
              selected.has(node.id) ? 'border-primary bg-primary-soft/60 ring-1 ring-primary' : 'border-line hover:border-line-strong hover:bg-canvas-subtle hover:shadow-sm',
              focusedId === node.id && !selected.has(node.id) ? 'border-line-strong' : '',
              highlightIds.has(node.id) ? 'animate-row-flash' : '',
            ]"
            :style="delay(i)"
            @click="emit('click', node, $event)"
            @dblclick="emit('open', node)"
          >
            <span class="relative flex h-8 w-8 shrink-0 items-center justify-center">
              <Folder
                :size="22"
                :stroke-width="1.75"
                class="text-amber-500 transition-opacity group-hover:opacity-0"
                :class="{ 'opacity-0': selected.size > 0 }"
                fill="currentColor"
                fill-opacity="0.18"
                aria-hidden="true"
              />
              <UiCheckbox
                :model-value="selected.has(node.id)"
                :aria-label="`Select ${node.name}`"
                class="absolute inset-0 m-auto h-fit w-fit opacity-0 focus-within:opacity-100 group-hover:opacity-100"
                :class="{ '!opacity-100': selected.size > 0 }"
                @update:model-value="emit('toggle', node)"
              />
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-base font-medium text-fg">{{ node.name }}</p>
              <p class="tabular truncate text-xs text-fg-subtle">{{ formatRelative(node.updated_at) }}</p>
            </div>
            <UiDropdownMenu :items="menuFor(node)">
              <UiButton
                variant="ghost"
                size="sm"
                icon-only
                :icon="MoreHorizontal"
                :aria-label="`More actions for ${node.name}`"
                class="shrink-0 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:data-[state=open]:opacity-100"
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
      <h2 v-if="folders.length" id="grid-files" class="mb-2 text-sm font-medium text-fg-muted">Files</h2>
      <h2 v-else id="grid-files" class="sr-only">Files</h2>
      <div :class="GRID" data-grid>
        <UiContextMenu v-for="(node, i) in files" :key="node.id" :items="menuFor(node)" @open="!selected.has(node.id) && selectForMenu(node)">
          <div
            :id="`row-${node.id}`"
            role="option"
            :aria-selected="selected.has(node.id)"
            class="group relative flex animate-card-in cursor-default select-none flex-col overflow-hidden rounded-xl border bg-surface transition-[border-color,box-shadow,transform] duration-base ease-out hover:-translate-y-0.5"
            :class="[
              selected.has(node.id) ? 'border-primary ring-2 ring-primary/70' : 'border-line hover:border-line-strong hover:shadow-md',
              focusedId === node.id && !selected.has(node.id) ? 'border-line-strong shadow-sm' : '',
              highlightIds.has(node.id) ? 'animate-row-flash' : '',
            ]"
            :style="delay(folders.length + i)"
            @click="emit('click', node, $event)"
            @dblclick="emit('open', node)"
          >
            <div class="relative aspect-[4/3] overflow-hidden border-b border-line bg-canvas-subtle [&_img]:transition-transform [&_img]:duration-slow group-hover:[&_img]:scale-[1.04]">
              <FileThumb :node="node" variant="card" />
              <!-- Selection tint and checkbox -->
              <span class="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/25 to-transparent to-40% opacity-0 transition-opacity group-hover:opacity-100" :class="{ 'opacity-100': selected.size > 0 }" aria-hidden="true" />
              <UiCheckbox
                :model-value="selected.has(node.id)"
                :aria-label="`Select ${node.name}`"
                class="absolute left-2.5 top-2.5 rounded-sm bg-surface opacity-0 shadow-sm focus-within:opacity-100 group-hover:opacity-100"
                :class="{ '!opacity-100': selected.size > 0 }"
                @update:model-value="emit('toggle', node)"
              />
              <span v-if="isDownloading(node)" class="absolute bottom-2 right-2 rounded-full bg-surface p-1 text-primary shadow-sm" role="status" :aria-label="`Downloading ${progressOf(node)}%`">
                <UiProgressCircle :value="progressOf(node)" :size="18" />
              </span>
            </div>
            <div class="flex items-center gap-2 py-2 pl-3 pr-1">
              <component :is="kindInfo(kindOf(node)).icon" :size="16" :stroke-width="1.75" class="shrink-0" :class="kindIconColor(kindOf(node))" aria-hidden="true" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-base font-medium leading-5 text-fg">{{ node.name }}</p>
                <p class="tabular truncate text-xs text-fg-subtle">{{ formatBytes(node.size_bytes) }} · {{ formatRelative(node.updated_at) }}</p>
              </div>
              <UiDropdownMenu :items="menuFor(node)">
                <UiButton
                  variant="ghost"
                  size="sm"
                  icon-only
                  :icon="MoreHorizontal"
                  :aria-label="`More actions for ${node.name}`"
                  class="shrink-0 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:data-[state=open]:opacity-100"
                  @click.stop
                  @dblclick.stop
                />
              </UiDropdownMenu>
            </div>
          </div>
        </UiContextMenu>
      </div>
    </section>
  </div>
</template>

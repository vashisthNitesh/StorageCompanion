<script setup lang="ts">
import { computed, inject, nextTick, onMounted, ref, watch, type Ref } from "vue";
import { useVirtualizer } from "@tanstack/vue-virtual";
import { MoreHorizontal, Download, ArrowUp, ArrowDown } from "lucide-vue-next";
import type { FileNode, SearchResult, SortDir, SortField } from "../../stores/files";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiDropdownMenu from "../../components/ui/UiDropdownMenu.vue";
import UiContextMenu from "../../components/ui/UiContextMenu.vue";
import UiTooltip from "../../components/ui/UiTooltip.vue";
import UiProgressCircle from "../../components/ui/UiProgressCircle.vue";
import type { MenuEntry } from "../../components/ui/menuTypes";
import { formatBytes, formatDateTime, formatRelative } from "../../lib/format";
import { useMediaQuery } from "../../composables/useMediaQuery";
import FileThumb from "../preview/FileThumb.vue";
import { validateName } from "./nameValidation";
import FileName from "./FileName.vue";
import { useFileDownload } from "./useFileDownload";

const props = defineProps<{
  items: (FileNode | SearchResult)[];
  selected: Set<string>;
  focusedId: string | null;
  renamingId: string | null;
  showLocation?: boolean;
  highlightIds: Set<string>;
  menuFor: (node: FileNode) => MenuEntry[];
  sort?: { field: SortField; dir: SortDir };
  listLabel: string;
}>();
const emit = defineEmits<{
  click: [node: FileNode, e: MouseEvent];
  toggle: [node: FileNode];
  toggleAll: [];
  open: [node: FileNode];
  renameCommit: [node: FileNode, name: string];
  renameCancel: [];
  sort: [field: SortField];
  keydown: [e: KeyboardEvent];
}>();
/** Right-clicking an unselected item selects it first, like a desktop file manager. */
function selectForMenu(node: FileNode) {
  emit("click", node, new MouseEvent("click"));
}

const { downloadFile, isDownloading, progressOf } = useFileDownload();
const isWide = useMediaQuery("(min-width: 768px)");
const ROW = computed(() => (isWide.value ? 44 : 56));

// --- Virtualisation for long folders ------------------------------------------
const VIRTUALISE_FROM = 200;
const scrollEl = inject<Ref<HTMLElement | null>>("scrollContainer", ref(null));
const listEl = ref<HTMLElement | null>(null);
const scrollMargin = ref(0);
const virtual = computed(() => props.items.length > VIRTUALISE_FROM);
function measureMargin() {
  if (!listEl.value || !scrollEl.value) return;
  const top = listEl.value.getBoundingClientRect().top - scrollEl.value.getBoundingClientRect().top + scrollEl.value.scrollTop;
  scrollMargin.value = top;
}
onMounted(measureMargin);
watch(() => props.items.length, () => nextTick(measureMargin));
const virtualizer = useVirtualizer(
  computed(() => ({
    count: props.items.length,
    getScrollElement: () => scrollEl.value,
    estimateSize: () => ROW.value,
    overscan: 12,
    scrollMargin: scrollMargin.value,
  }))
);
const rows = computed(() =>
  virtual.value
    ? virtualizer.value.getVirtualItems().map((v) => ({ node: props.items[v.index], index: v.index, offset: v.start - scrollMargin.value }))
    : props.items.map((node, index) => ({ node, index, offset: 0 }))
);
const totalHeight = computed(() => (virtual.value ? virtualizer.value.getTotalSize() : undefined));

/** Keeps the keyboard-focused row in view (works for virtualised lists too). */
function scrollToIndex(index: number) {
  if (virtual.value) virtualizer.value.scrollToIndex(index, { align: "auto" });
  else document.getElementById(`row-${props.items[index]?.id}`)?.scrollIntoView({ block: "nearest" });
}
defineExpose({ scrollToIndex, focus: () => listEl.value?.focus() });

// --- Select-all checkbox -------------------------------------------------------
const allState = computed<boolean | "indeterminate">(() => {
  if (!props.items.length || !props.selected.size) return false;
  return props.items.every((n) => props.selected.has(n.id)) ? true : "indeterminate";
});

// --- Inline rename (F2) --------------------------------------------------------
const draft = ref("");
const draftError = ref<string | null>(null);
watch(
  () => props.renamingId,
  async (id) => {
    const node = props.items.find((n) => n.id === id);
    if (!node) return;
    draft.value = node.name;
    draftError.value = null;
    await nextTick();
    const input = document.getElementById(`rename-${id}`) as HTMLInputElement | null;
    if (input) {
      input.focus();
      const dot = node.type === "file" ? node.name.lastIndexOf(".") : -1;
      input.setSelectionRange(0, dot > 0 ? dot : node.name.length);
    }
  }
);
function commitRename(node: FileNode) {
  if (props.renamingId !== node.id) return;
  const value = draft.value.trim();
  if (value === node.name) return emit("renameCancel");
  draftError.value = validateName(value, { parentId: node.parent, exceptId: node.id, type: node.type });
  if (draftError.value) return;
  emit("renameCommit", node, value);
}

const sortIcon = (field: SortField) => (props.sort?.field === field ? (props.sort.dir === "asc" ? ArrowUp : ArrowDown) : null);
const ariaSort = (field: SortField) => (props.sort?.field === field ? (props.sort.dir === "asc" ? "ascending" : "descending") : "none");
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-line bg-surface">
    <!-- Sticky column header -->
    <div
      class="sticky top-0 z-10 grid h-10 items-center gap-3 border-b border-line bg-surface-sunken/95 px-3 text-sm font-medium text-fg-muted backdrop-blur"
      :class="isWide ? 'grid-cols-[24px_minmax(0,1fr)_140px_96px_76px]' : 'grid-cols-[24px_minmax(0,1fr)_40px]'"
      role="presentation"
    >
      <UiCheckbox :model-value="allState" aria-label="Select all" @update:model-value="emit('toggleAll')" />
      <button class="flex items-center gap-1 justify-self-start hover:text-fg" :aria-sort="ariaSort('name')" @click="emit('sort', 'name')">
        Name <component :is="sortIcon('name')" v-if="sortIcon('name')" :size="14" />
      </button>
      <template v-if="isWide">
        <button class="flex items-center gap-1 justify-self-start hover:text-fg" :aria-sort="ariaSort('modified')" @click="emit('sort', 'modified')">
          Modified <component :is="sortIcon('modified')" v-if="sortIcon('modified')" :size="14" />
        </button>
        <button class="flex items-center gap-1 justify-self-end hover:text-fg" :aria-sort="ariaSort('size')" @click="emit('sort', 'size')">
          Size <component :is="sortIcon('size')" v-if="sortIcon('size')" :size="14" />
        </button>
      </template>
      <span class="sr-only">Actions</span>
    </div>

    <div
      ref="listEl"
      role="listbox"
      aria-multiselectable="true"
      :aria-label="listLabel"
      :aria-activedescendant="focusedId ? `row-${focusedId}` : undefined"
      tabindex="0"
      class="relative outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40"
      :style="totalHeight ? { height: `${totalHeight}px` } : undefined"
      @keydown="emit('keydown', $event)"
    >
      <UiContextMenu v-for="row in rows" :key="row.node.id" :items="menuFor(row.node)" @open="!selected.has(row.node.id) && selectForMenu(row.node)">
        <div
          :id="`row-${row.node.id}`"
          role="option"
          :aria-selected="selected.has(row.node.id)"
          class="group grid cursor-default select-none items-center gap-3 border-b border-line px-3 last:border-b-0"
          :class="[
            isWide ? 'grid-cols-[24px_minmax(0,1fr)_140px_96px_76px]' : 'grid-cols-[24px_minmax(0,1fr)_40px]',
            selected.has(row.node.id) ? 'bg-primary-soft/70' : 'hover:bg-canvas-subtle',
            focusedId === row.node.id ? 'shadow-[inset_2px_0_0_rgb(var(--primary))]' : '',
            highlightIds.has(row.node.id) ? 'animate-row-flash' : '',
            virtual ? 'absolute inset-x-0' : '',
          ]"
          :style="{ height: `${ROW}px`, ...(virtual ? { transform: `translateY(${row.offset}px)` } : {}) }"
          @click="emit('click', row.node, $event)"
          @dblclick="emit('open', row.node)"
        >
          <UiCheckbox
            :model-value="selected.has(row.node.id)"
            :aria-label="`Select ${row.node.name}`"
            class="opacity-0 group-hover:opacity-100 focus-within:opacity-100"
            :class="{ '!opacity-100': selected.size > 0 }"
            @update:model-value="emit('toggle', row.node)"
          />
          <div class="flex min-w-0 items-center gap-3">
            <FileThumb :node="row.node" variant="row" />
            <div class="min-w-0 flex-1">
              <div v-if="renamingId === row.node.id" class="relative" @click.stop @dblclick.stop>
                <input
                  :id="`rename-${row.node.id}`"
                  v-model="draft"
                  class="h-8 w-full rounded border bg-surface px-2 text-base text-fg outline-none focus:ring-4"
                  :class="draftError ? 'border-danger focus:ring-danger/15' : 'border-primary focus:ring-primary/15'"
                  :aria-label="`Rename ${row.node.name}`"
                  :aria-invalid="!!draftError || undefined"
                  :aria-describedby="draftError ? `rename-err-${row.node.id}` : undefined"
                  @input="draftError = null"
                  @keydown.enter.prevent.stop="commitRename(row.node)"
                  @keydown.esc.prevent.stop="emit('renameCancel')"
                  @keydown.stop
                  @blur="draftError ? emit('renameCancel') : commitRename(row.node)"
                />
                <p v-if="draftError" :id="`rename-err-${row.node.id}`" role="alert" class="absolute left-0 top-full z-20 mt-1 whitespace-nowrap rounded bg-danger px-2 py-1 text-xs text-danger-fg shadow-md">
                  {{ draftError }}
                </p>
              </div>
              <template v-else>
                <FileName :name="row.node.name" :is-folder="row.node.type === 'folder'" class="text-base text-fg" />
                <p v-if="showLocation && 'location' in row.node" class="truncate text-xs text-fg-subtle">{{ row.node.location }}</p>
                <p v-else-if="!isWide" class="tabular truncate text-xs text-fg-subtle">
                  {{ row.node.type === "folder" ? "Folder" : formatBytes(row.node.size_bytes) }} · {{ formatRelative(row.node.updated_at) }}
                </p>
              </template>
            </div>
          </div>
          <template v-if="isWide">
            <UiTooltip :content="formatDateTime(row.node.updated_at)">
              <span class="tabular truncate text-sm text-fg-muted">{{ formatRelative(row.node.updated_at) }}</span>
            </UiTooltip>
            <span class="tabular justify-self-end text-sm text-fg-muted">{{ row.node.type === "folder" ? "—" : formatBytes(row.node.size_bytes) }}</span>
          </template>
          <div class="flex items-center justify-end gap-0.5" @dblclick.stop>
            <span v-if="isDownloading(row.node)" class="flex h-8 w-8 items-center justify-center text-primary" role="status" :aria-label="`Downloading ${progressOf(row.node)}%`">
              <UiProgressCircle :value="progressOf(row.node)" :size="18" />
            </span>
            <UiButton
              v-else-if="row.node.type === 'file' && isWide"
              variant="ghost"
              size="sm"
              icon-only
              :icon="Download"
              :aria-label="`Download ${row.node.name}`"
              class="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 group-aria-selected:opacity-100"
              @click.stop="downloadFile(row.node)"
            />
            <UiDropdownMenu :items="menuFor(row.node)">
              <UiButton
                variant="ghost"
                size="sm"
                icon-only
                :icon="MoreHorizontal"
                :aria-label="`More actions for ${row.node.name}`"
                class="opacity-100 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:data-[state=open]:opacity-100"
                @click.stop
              />
            </UiDropdownMenu>
          </div>
        </div>
      </UiContextMenu>
    </div>
  </div>
</template>

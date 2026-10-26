<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  FolderPlus,
  Upload,
  List,
  LayoutGrid,
  ArrowUpNarrowWide,
  ArrowDownWideNarrow,
  Download,
  FolderOpen,
  Pencil,
  FolderInput,
  FileUp,
  Info,
  Trash2,
  UploadCloud,
  SearchX,
  CreditCard,
  FolderClosed,
  Filter,
  Clock,
  CloudOff,
  Eye,
  Share2,
} from "lucide-vue-next";
import UiBreadcrumbs from "../../components/ui/UiBreadcrumbs.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiSelect from "../../components/ui/UiSelect.vue";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiEmptyState from "../../components/ui/UiEmptyState.vue";
import type { MenuEntry } from "../../components/ui/menuTypes";
import { useFilesStore, compareNodes, type FileNode, type SearchResult, type SortField } from "../../stores/files";
import { useAuthStore } from "../../stores/auth";
import { useUploadStore } from "../../stores/upload";
import { useUploader } from "../../composables/useUploader";
import { useShortcuts } from "../../composables/useShortcuts";
import { emitAppEvent, onAppEvent } from "../../lib/events";
import { normalizeApiError } from "../../lib/errors";
import { formatBytes } from "../../lib/format";
import { FILTERS, kindOf, type FilterKey } from "./fileTypes";
import { useFileActions } from "./useFileActions";
import FileListView from "./FileListView.vue";
import FileGridView from "./FileGridView.vue";
import NameDialog from "./NameDialog.vue";
import MoveDialog from "./MoveDialog.vue";
import DetailsDrawer from "./DetailsDrawer.vue";
import BulkBar from "./BulkBar.vue";
import FilePreview from "../preview/FilePreview.vue";
import ShareDialog from "../sharing/ShareDialog.vue";

const route = useRoute();
const files = useFilesStore();
const authStore = useAuthStore();
const uploadStore = useUploadStore();
const uploader = useUploader();
const actions = useFileActions();

const isRecent = computed(() => route.meta.view === "recent");
const searching = computed(() => !isRecent.value && files.isSearchActive);
const filter = ref<FilterKey>("all");

// --- Data per mode ------------------------------------------------------------
const recent = ref<SearchResult[]>([]);
const recentLoading = ref(false);
const recentError = ref<unknown>(null);
async function loadRecent() {
  recentLoading.value = true;
  recentError.value = null;
  try {
    recent.value = await files.recentFiles(100);
  } catch (err) {
    recentError.value = err;
  } finally {
    recentLoading.value = false;
  }
}

function applyFilter<T extends FileNode>(list: T[]): T[] {
  const kinds = FILTERS.find((f) => f.key === filter.value)?.kinds ?? [];
  return kinds.length ? list.filter((n) => kinds.includes(kindOf(n))) : list;
}
const source = computed<FileNode[]>(() => (isRecent.value ? recent.value : searching.value ? files.searchResults : files.nodes));
const items = computed(() => {
  const list = applyFilter([...source.value]);
  return isRecent.value ? list : list.sort(compareNodes(files.prefs.sort, files.prefs.dir));
});
const loading = computed(() =>
  isRecent.value ? recentLoading.value && !recent.value.length : searching.value ? files.isSearching && !files.searchResults.length : files.isLoading && !files.loaded
);
const error = computed(() => (isRecent.value ? recentError.value : searching.value ? files.searchError : files.loadError));
const totalSize = computed(() => items.value.reduce((s, n) => s + (n.type === "file" ? n.size_bytes : 0), 0));
const noPlan = computed(() => !authStore.user?.subscription?.has_active_subscription);
const crumbs = computed(() => files.breadcrumbs.map((c, i) => ({ key: c.id ?? `root-${i}`, label: c.name })));
const currentFolderName = computed(() => files.breadcrumbs.at(-1)?.name ?? "My files");

// --- Selection & keyboard -------------------------------------------------------
const selected = ref<Set<string>>(new Set());
const focusedId = ref<string | null>(null);
const anchorId = ref<string | null>(null);
const renamingId = ref<string | null>(null);
const listRef = ref<InstanceType<typeof FileListView> | null>(null);
const selectedNodes = computed(() => items.value.filter((n) => selected.value.has(n.id)));

function clearSelection() {
  selected.value = new Set();
  anchorId.value = null;
}
watch([() => files.currentParentId, searching, isRecent, filter], () => {
  clearSelection();
  focusedId.value = null;
  renamingId.value = null;
});
// Revealed items (command palette) get focused and selected.
watch(
  () => [files.revealId, items.value.length] as const,
  ([id]) => {
    if (!id) return;
    const index = items.value.findIndex((n) => n.id === id);
    if (index < 0) return;
    selected.value = new Set([id]);
    focusedId.value = id;
    files.revealId = null;
    nextTick(() => listRef.value?.scrollToIndex(index));
  }
);

function rangeIds(fromId: string | null, toId: string) {
  const ids = items.value.map((n) => n.id);
  const a = fromId ? ids.indexOf(fromId) : -1;
  const b = ids.indexOf(toId);
  if (a < 0) return [toId];
  return ids.slice(Math.min(a, b), Math.max(a, b) + 1);
}

function onItemClick(node: FileNode, e: MouseEvent) {
  focusedId.value = node.id;
  if (e.shiftKey) {
    selected.value = new Set(rangeIds(anchorId.value, node.id));
  } else if (e.metaKey || e.ctrlKey) {
    toggle(node);
  } else {
    selected.value = new Set([node.id]);
    anchorId.value = node.id;
  }
}
function toggle(node: FileNode) {
  const next = new Set(selected.value);
  if (next.has(node.id)) next.delete(node.id);
  else next.add(node.id);
  selected.value = next;
  anchorId.value = node.id;
  focusedId.value = node.id;
}
function toggleAll() {
  selected.value = selected.value.size === items.value.length ? new Set() : new Set(items.value.map((n) => n.id));
}

function openContextMenuFor(id: string) {
  const row = document.getElementById(`row-${id}`);
  if (!row) return;
  const r = row.getBoundingClientRect();
  row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: r.left + Math.min(240, r.width / 2), clientY: r.top + r.height / 2 }));
}

function onListKey(e: KeyboardEvent) {
  if (renamingId.value) return;
  const list = items.value;
  if (!list.length) return;
  const index = Math.max(0, list.findIndex((n) => n.id === focusedId.value));
  const grid = useGrid.value;
  // In the grid, up/down jump a row: count the columns of the group (folders or files) holding the focus.
  const gridEl = grid ? document.getElementById(`row-${list[index]?.id}`)?.closest("[data-grid]") : null;
  const step = gridEl ? Math.max(1, getComputedStyle(gridEl).gridTemplateColumns.split(" ").length) : 1;
  const move = (to: number) => {
    e.preventDefault();
    const next = list[Math.max(0, Math.min(list.length - 1, to))];
    focusedId.value = next.id;
    if (e.shiftKey) selected.value = new Set(rangeIds(anchorId.value ?? list[index].id, next.id));
    else if (!e.metaKey && !e.ctrlKey) {
      selected.value = new Set([next.id]);
      anchorId.value = next.id;
    }
    listRef.value?.scrollToIndex(list.indexOf(next));
    if (grid) document.getElementById(`row-${next.id}`)?.scrollIntoView({ block: "nearest" });
  };
  const focused = list.find((n) => n.id === focusedId.value);
  switch (e.key) {
    case "ArrowDown":
      return move(focusedId.value ? index + step : 0);
    case "ArrowUp":
      return move(index - step);
    case "ArrowRight":
      return grid ? move(index + 1) : undefined;
    case "ArrowLeft":
      return grid ? move(index - 1) : undefined;
    case "Home":
      return move(0);
    case "End":
      return move(list.length - 1);
    case "Enter":
      e.preventDefault();
      if (focused) open(focused);
      return;
    case " ":
      e.preventDefault();
      if (focused) toggle(focused);
      return;
    case "F2":
      e.preventDefault();
      if (selectedNodes.value.length === 1) startRename(selectedNodes.value[0]);
      return;
    case "Delete":
    case "Backspace":
      e.preventDefault();
      if (selectedNodes.value.length) void trash(selectedNodes.value);
      return;
    case "Escape":
      return clearSelection();
    case "ContextMenu":
    case "F10":
      // Shift+F10 / the Menu key open the row's context menu, as in desktop file managers.
      if (e.key === "F10" && !e.shiftKey) return;
      e.preventDefault();
      if (focused) openContextMenuFor(focused.id);
      return;
    case "a":
      if (e.metaKey || e.ctrlKey) {
        e.preventDefault();
        selected.value = new Set(list.map((n) => n.id));
      }
  }
}

// --- Actions ----------------------------------------------------------------------
const nameDialog = ref<{ open: boolean; mode: "create" | "rename"; node?: FileNode }>({ open: false, mode: "create" });
const moveDialog = ref<{ open: boolean; nodes: FileNode[] }>({ open: false, nodes: [] });
const details = ref<{ open: boolean; node: FileNode | null }>({ open: false, node: null });
const shareDialog = ref<{ open: boolean; node: FileNode | null }>({ open: false, node: null });
function share(node: FileNode) {
  if (node.type === "file") shareDialog.value = { open: true, node };
}
const preview = ref({ open: false, index: 0 });
/** Files in the current listing, in display order: what previous / next steps through. */
const previewItems = computed(() => items.value.filter((n) => n.type === "file"));
const versionInput = ref<HTMLInputElement | null>(null);
const versionFor = ref<FileNode | null>(null);

function open(node: FileNode) {
  if (node.type === "folder") {
    if (searching.value || isRecent.value) void files.openFolderFromSearch(node.id);
    else void files.openFolder(node.id, node.name);
  } else {
    preview.value = { open: true, index: Math.max(0, previewItems.value.findIndex((n) => n.id === node.id)) };
  }
}
function startRename(node: FileNode) {
  if (useGrid.value) nameDialog.value = { open: true, mode: "rename", node };
  else renamingId.value = node.id;
}
async function commitRename(node: FileNode, name: string) {
  renamingId.value = null;
  await actions.rename(node, name);
  nextTick(() => listRef.value?.focus());
}
async function trash(nodes: FileNode[]) {
  const done = await actions.trash(nodes);
  if (done.length) clearSelection();
  if (isRecent.value) recent.value = recent.value.filter((n) => !done.includes(n));
}
function newFolder() {
  if (searching.value) files.clearSearch();
  nameDialog.value = { open: true, mode: "create" };
}
async function submitName(name: string) {
  const d = nameDialog.value;
  if (d.mode === "create") await files.createFolder(name);
  else if (d.node) await actions.rename(d.node, name, { rethrow: true });
}
function uploadNewVersion(node: FileNode) {
  if (!uploader.ensureCanUpload()) return;
  versionFor.value = node;
  versionInput.value?.click();
}
function onVersionPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file && versionFor.value) uploadStore.uploadNewVersion(file, versionFor.value);
  input.value = "";
  versionFor.value = null;
}
async function moveTo(dest: { id: string | null; name: string }) {
  await actions.move(moveDialog.value.nodes, dest);
  clearSelection();
}

function menuFor(node: FileNode): MenuEntry[] {
  const targets = selected.value.has(node.id) && selected.value.size > 1 ? selectedNodes.value : [node];
  const many = targets.length > 1;
  const entries: MenuEntry[] = [];
  if (!many) {
    entries.push(
      node.type === "folder"
        ? { label: "Open", icon: FolderOpen, shortcut: "↵", onSelect: () => open(node) }
        : { label: "Open", icon: Eye, shortcut: "↵", onSelect: () => open(node) }
    );
    if (node.type === "file") {
      entries.push({ label: "Download", icon: Download, onSelect: () => void actions.download([node]) });
      entries.push({ label: "Share", icon: Share2, onSelect: () => share(node) });
    }
  } else if (targets.some((n) => n.type === "file")) {
    const count = targets.filter((n) => n.type === "file").length;
    entries.push({ label: `Download ${count} ${count === 1 ? "file" : "files"}`, icon: Download, onSelect: () => void actions.download(targets) });
  }
  if (!many) entries.push({ label: "Rename", icon: Pencil, shortcut: "F2", onSelect: () => startRename(node) });
  entries.push({ label: "Move to…", icon: FolderInput, onSelect: () => (moveDialog.value = { open: true, nodes: targets }) });
  if (!many && node.type === "file") entries.push({ label: "Upload new version", icon: FileUp, onSelect: () => uploadNewVersion(node) });
  if (!many) entries.push({ label: "Details", icon: Info, onSelect: () => (details.value = { open: true, node }) });
  entries.push(
    { separator: true },
    { label: many ? `Move ${targets.length} items to trash` : "Move to trash", icon: Trash2, danger: true, shortcut: "Del", onSelect: () => void trash(targets) }
  );
  return entries;
}

// --- Toolbar options -----------------------------------------------------------------
const typeOptions = FILTERS.map((f) => ({ value: f.key, label: f.label }));
const sortOptions: { value: SortField; label: string }[] = [
  { value: "name", label: "Name" },
  { value: "modified", label: "Modified" },
  { value: "size", label: "Size" },
];
function sortBy(field: SortField) {
  if (files.prefs.sort === field) files.prefs = { ...files.prefs, dir: files.prefs.dir === "asc" ? "desc" : "asc" };
  else files.prefs = { ...files.prefs, sort: field, dir: field === "name" ? "asc" : "desc" };
}
function toggleDir() {
  files.prefs = { ...files.prefs, dir: files.prefs.dir === "asc" ? "desc" : "asc" };
}
const viewOptions = [
  { value: "list" as const, label: "List view", icon: List, hideLabel: true },
  { value: "grid" as const, label: "Grid view", icon: LayoutGrid, hideLabel: true },
];
const useGrid = computed(() => files.prefs.view === "grid" && !searching.value && !isRecent.value);
const filterLabel = computed(() => FILTERS.find((f) => f.key === filter.value)?.label.toLowerCase() ?? "items");

// --- Drag and drop ------------------------------------------------------------------
const dragDepth = ref(0);
function onDragEnter(e: DragEvent) {
  if (!isRecent.value && e.dataTransfer?.types.includes("Files")) dragDepth.value++;
}
function onDrop(e: DragEvent) {
  dragDepth.value = 0;
  const dropped = e.dataTransfer?.files;
  if (dropped?.length && !isRecent.value) uploader.upload(Array.from(dropped), files.currentParentId);
}

// --- Lifecycle ---------------------------------------------------------------------
function load() {
  if (!authStore.masterKey) return;
  if (isRecent.value) void loadRecent();
  else void files.fetchNodes(files.currentParentId);
}
function retry() {
  if (searching.value) void files.search(files.searchQuery);
  else load();
}
let off: (() => void) | null = null;
onMounted(() => {
  load();
  off = onAppEvent("new-folder", newFolder);
});
onUnmounted(() => off?.());
watch(() => authStore.masterKey, (k) => k && load());
watch(isRecent, load);

useShortcuts(() => [{ keys: "escape", handler: clearSelection }]);
</script>

<template>
  <div
    class="relative"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent
    @dragleave="dragDepth = Math.max(0, dragDepth - 1)"
    @drop.prevent="onDrop"
  >
    <input ref="versionInput" type="file" class="hidden" tabindex="-1" aria-hidden="true" @change="onVersionPicked" />

    <!-- Page header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="min-w-0">
        <h1 v-if="isRecent" class="text-xl font-semibold text-fg">Recent</h1>
        <template v-else-if="searching">
          <h1 class="text-xl font-semibold text-fg">Search results</h1>
          <p class="mt-1 truncate text-base text-fg-muted" aria-live="polite">
            <template v-if="files.isSearching">Searching for “{{ files.searchQuery }}”…</template>
            <template v-else>{{ items.length }} {{ items.length === 1 ? "result" : "results" }} for “{{ files.searchQuery }}”</template>
          </p>
        </template>
        <template v-else>
          <h1 class="sr-only">My files</h1>
          <UiBreadcrumbs class="-ml-1.5" :items="crumbs" @navigate="files.navigateToCrumb" />
        </template>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <UiButton v-if="searching" @click="files.clearSearch()">Clear search</UiButton>
        <template v-else-if="!isRecent">
          <UiButton :icon="FolderPlus" shortcut="N" tooltip="New folder" @click="newFolder">New folder</UiButton>
          <UiButton variant="primary" :icon="Upload" shortcut="U" tooltip="Upload files to this folder" @click="emitAppEvent('upload-files')">Upload</UiButton>
        </template>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="mt-4 flex flex-wrap items-center gap-2">
      <UiSelect v-model="filter" :options="typeOptions" aria-label="Filter by type" size="sm" :searchable="false" :block="false" trigger-class="min-w-[136px]" />
      <template v-if="!isRecent">
        <UiSelect
          :model-value="files.prefs.sort"
          :options="sortOptions"
          prefix="Sort:"
          aria-label="Sort by"
          size="sm"
          :searchable="false"
          :block="false"
          trigger-class="min-w-[148px]"
          @update:model-value="(v) => sortBy(v as SortField)"
        />
        <UiButton
          size="sm"
          icon-only
          :icon="files.prefs.dir === 'asc' ? ArrowUpNarrowWide : ArrowDownWideNarrow"
          :aria-label="files.prefs.dir === 'asc' ? 'Sorted ascending. Switch to descending' : 'Sorted descending. Switch to ascending'"
          @click="toggleDir"
        />
      </template>
      <span v-if="items.length && !loading" class="tabular hidden text-sm text-fg-subtle md:inline">
        {{ items.length }} {{ items.length === 1 ? "item" : "items" }}<template v-if="totalSize"> · {{ formatBytes(totalSize) }}</template>
      </span>
      <div v-if="!searching && !isRecent" class="ml-auto">
        <UiSegmented
          :model-value="files.prefs.view"
          :options="viewOptions"
          label="View"
          size="sm"
          @update:model-value="(v) => (files.prefs = { ...files.prefs, view: v })"
        />
      </div>
    </div>

    <!-- Content -->
    <div class="mt-4">
      <!-- Waiting for the vault / loading: skeleton of the real layout -->
      <div v-if="!authStore.masterKey || loading" aria-busy="true" aria-label="Loading files">
        <div v-if="useGrid" class="grid grid-cols-2 gap-3 sm:grid-cols-[repeat(auto-fill,minmax(210px,1fr))] sm:gap-4">
          <div v-for="i in 12" :key="i" class="rounded-xl bg-tile px-1.5 pb-1.5">
            <div class="flex h-11 items-center gap-2.5 pl-2"><UiSkeleton class="h-4 w-4" /><UiSkeleton class="h-3.5 w-2/3" /></div>
            <UiSkeleton class="aspect-[4/3] w-full rounded-lg" />
            <div class="flex justify-between px-1.5 pt-2.5"><UiSkeleton class="h-3 w-1/3" /><UiSkeleton class="h-3 w-1/5" /></div>
          </div>
        </div>
        <div v-else class="overflow-hidden rounded-lg border border-line bg-surface">
          <div class="h-10 border-b border-line bg-surface-sunken" />
          <div v-for="i in 8" :key="i" class="flex h-11 items-center gap-3 border-b border-line px-3 last:border-0">
            <UiSkeleton class="h-4 w-4" />
            <UiSkeleton class="h-8 w-8" />
            <UiSkeleton class="h-3.5" :class="i % 3 ? 'w-1/3' : 'w-1/4'" />
            <UiSkeleton class="ml-auto hidden h-3 w-16 md:block" />
            <UiSkeleton class="hidden h-3 w-12 md:block" />
          </div>
        </div>
      </div>

      <div v-else-if="error" class="rounded-lg border border-line bg-surface">
        <UiEmptyState :icon="CloudOff" tone="danger" title="Couldn't load your files" :description="normalizeApiError(error).message">
          <UiButton @click="retry">Try again</UiButton>
        </UiEmptyState>
      </div>

      <div v-else-if="!items.length" class="rounded-lg border border-dashed border-line-strong bg-surface">
        <UiEmptyState v-if="searching" :icon="SearchX" tone="neutral" :title="`No results for “${files.searchQuery}”`" description="Check the spelling or try part of the file name.">
          <UiButton @click="files.clearSearch()">Clear search</UiButton>
        </UiEmptyState>
        <UiEmptyState v-else-if="source.length && filter !== 'all'" :icon="Filter" tone="neutral" title="Nothing matches this filter" :description="`There are no ${filterLabel} here.`">
          <UiButton @click="filter = 'all'">Show all types</UiButton>
        </UiEmptyState>
        <UiEmptyState v-else-if="isRecent" :icon="Clock" tone="neutral" title="No recent files" description="Files you upload or change appear here." />
        <UiEmptyState v-else-if="noPlan && !files.currentParentId" :icon="CreditCard" title="Welcome to SmartSpace" description="Choose a plan to start uploading. Your files are encrypted on this device before they leave it.">
          <UiButton variant="primary" @click="emitAppEvent('plan-picker', {})">Choose a plan</UiButton>
        </UiEmptyState>
        <UiEmptyState v-else-if="files.currentParentId" :icon="FolderClosed" tone="neutral" :title="`“${currentFolderName}” is empty`" description="Drop files here, or upload from your device.">
          <UiButton variant="primary" :icon="Upload" @click="emitAppEvent('upload-files')">Upload files</UiButton>
          <UiButton :icon="FolderPlus" @click="newFolder">New folder</UiButton>
        </UiEmptyState>
        <UiEmptyState v-else :icon="UploadCloud" title="Drop files here or click Upload" description="Everything is encrypted on your device before it's uploaded.">
          <UiButton variant="primary" :icon="Upload" @click="emitAppEvent('upload-files')">Upload files</UiButton>
          <UiButton :icon="FolderPlus" @click="newFolder">New folder</UiButton>
        </UiEmptyState>
      </div>

      <FileGridView
        v-else-if="useGrid"
        :items="items"
        :selected="selected"
        :focused-id="focusedId"
        :highlight-ids="files.highlightIds"
        :menu-for="menuFor"
        :list-label="`Contents of ${currentFolderName}`"
        @click="onItemClick"
        @toggle="toggle"
        @open="open"
        @keydown="onListKey"
      />
      <FileListView
        v-else
        ref="listRef"
        :items="items"
        :selected="selected"
        :focused-id="focusedId"
        :renaming-id="renamingId"
        :show-location="searching || isRecent"
        :highlight-ids="files.highlightIds"
        :menu-for="menuFor"
        :sort="isRecent ? undefined : { field: files.prefs.sort, dir: files.prefs.dir }"
        :list-label="isRecent ? 'Recent files' : searching ? 'Search results' : `Contents of ${currentFolderName}`"
        @click="onItemClick"
        @toggle="toggle"
        @toggle-all="toggleAll"
        @share="share"
        @open="open"
        @rename-commit="commitRename"
        @rename-cancel="renamingId = null"
        @sort="sortBy"
        @keydown="onListKey"
      />
    </div>

    <!-- Drop overlay -->
    <div v-if="dragDepth > 0" class="pointer-events-none fixed inset-0 z-40 flex items-center justify-center bg-primary/5 p-6 backdrop-blur-[1px]">
      <div class="flex flex-col items-center rounded-xl border-2 border-dashed border-primary bg-surface-raised px-12 py-10 text-center shadow-xl">
        <UploadCloud :size="36" :stroke-width="1.5" class="text-primary" aria-hidden="true" />
        <p class="mt-3 text-md font-semibold text-fg">Drop to upload to “{{ currentFolderName }}”</p>
        <p class="mt-1 text-base text-fg-muted">Files are encrypted before they leave your device.</p>
      </div>
    </div>

    <BulkBar
      :count="selected.size"
      :can-download="selectedNodes.some((n) => n.type === 'file')"
      @download="actions.download(selectedNodes)"
      @move="moveDialog = { open: true, nodes: selectedNodes }"
      @rename="selectedNodes[0] && startRename(selectedNodes[0])"
      @trash="trash(selectedNodes)"
      @clear="clearSelection"
    />

    <NameDialog
      v-model:open="nameDialog.open"
      :mode="nameDialog.mode"
      :type="nameDialog.node?.type ?? 'folder'"
      :initial="nameDialog.node?.name"
      :parent-id="nameDialog.node ? nameDialog.node.parent : files.currentParentId"
      :except-id="nameDialog.node?.id"
      :submit="submitName"
    />
    <MoveDialog v-model:open="moveDialog.open" :nodes="moveDialog.nodes" @move="moveTo" />
    <DetailsDrawer v-model:open="details.open" :node="details.node" @share="share" />
    <FilePreview v-model:open="preview.open" v-model:index="preview.index" :items="previewItems" @details="(n) => (details = { open: true, node: n })" @share="share" />
    <ShareDialog v-model:open="shareDialog.open" :node="shareDialog.node" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import {
  ChevronRight,
  FolderPlus,
  Upload,
  FolderUp,
  LayoutGrid,
  List,
  RefreshCw,
  SearchX,
  UploadCloud,
  AlertCircle,
  Loader2,
  CreditCard,
} from "lucide-vue-next";
import { useFilesStore, type FileNode } from "../../stores/files";
import { useAuthStore } from "../../stores/auth";
import { useUploadStore } from "../../stores/upload";
import { useToastStore } from "../../stores/toast";
import { useFilePicker } from "../../composables/useFilePicker";
import { FILTERS, kindOf, type FilterKey } from "./fileTypes";
import { useFileDownload } from "./useFileDownload";
import { formatBytes } from "../../lib/format";
import FileListView from "./FileListView.vue";
import FileGridView from "./FileGridView.vue";
import ItemMenu, { type ItemAction } from "./ItemMenu.vue";
import NameDialog from "./NameDialog.vue";
import MoveDialog from "./MoveDialog.vue";
import VersionsDialog from "./VersionsDialog.vue";

const filesStore = useFilesStore();
const authStore = useAuthStore();
const uploadStore = useUploadStore();
const toast = useToastStore();
const picker = useFilePicker();
const { downloadFile } = useFileDownload();

const filter = ref<FilterKey>("all");
const sort = ref<"name" | "-name" | "-updated" | "-size">("name");
const selectedId = ref<string | null>(null);
const dragDepth = ref(0);

const menu = ref<{ node: FileNode | null; x: number; y: number }>({ node: null, x: 0, y: 0 });
const nameDialog = ref<null | { mode: "create" } | { mode: "rename"; node: FileNode }>(null);
const moveTarget = ref<FileNode | null>(null);
const versionsTarget = ref<FileNode | null>(null);
const versionInput = ref<HTMLInputElement | null>(null);
const versionFor = ref<FileNode | null>(null);

const SORTS = [
  { key: "name", label: "Name (A–Z)" },
  { key: "-name", label: "Name (Z–A)" },
  { key: "-updated", label: "Last modified" },
  { key: "-size", label: "Largest first" },
] as const;

function applyFilterAndSort<T extends FileNode>(list: T[]): T[] {
  const kinds = FILTERS.find((f) => f.key === filter.value)?.kinds || [];
  const filtered = kinds.length ? list.filter((n) => kinds.includes(kindOf(n))) : [...list];
  const cmp: Record<typeof sort.value, (a: T, b: T) => number> = {
    name: (a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" }),
    "-name": (a, b) => b.name.localeCompare(a.name, undefined, { numeric: true, sensitivity: "base" }),
    "-updated": (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    "-size": (a, b) => (b.size_bytes || 0) - (a.size_bytes || 0),
  };
  // Folders always first, like every desktop file manager.
  return filtered.sort((a, b) => (a.type === b.type ? cmp[sort.value](a, b) : a.type === "folder" ? -1 : 1));
}

const items = computed(() => applyFilterAndSort(filesStore.nodes));
const results = computed(() => applyFilterAndSort(filesStore.searchResults));
const searching = computed(() => filesStore.isSearchActive);
const visible = computed(() => (searching.value ? results.value : items.value));
const totalSize = computed(() => items.value.reduce((s, n) => s + (n.type === "file" ? n.size_bytes : 0), 0));

const canUpload = computed(() => authStore.canUpload);
const noPlan = computed(() => !authStore.user?.subscription?.has_active_subscription);

function open(node: FileNode) {
  if (node.type === "folder") {
    selectedId.value = null;
    if (searching.value) void filesStore.openFolderFromSearch(node.id);
    else void filesStore.openFolder(node.id, node.name);
  } else {
    void downloadFile(node);
  }
}

function openMenu(node: FileNode, x: number, y: number) {
  selectedId.value = node.id;
  menu.value = { node, x, y };
}

async function onMenu(action: ItemAction) {
  const node = menu.value.node;
  menu.value = { node: null, x: 0, y: 0 };
  if (!node) return;
  switch (action) {
    case "open":
    case "download":
      return open(node);
    case "rename":
      nameDialog.value = { mode: "rename", node };
      return;
    case "move":
      moveTarget.value = node;
      return;
    case "versions":
      versionsTarget.value = node;
      return;
    case "new-version":
      if (!canUpload.value) {
        toast.info("Choose a plan to upload files.");
        return;
      }
      versionFor.value = node;
      versionInput.value?.click();
      return;
    case "trash":
      try {
        await filesStore.trashNode(node.id);
        toast.success(`“${node.name}” moved to trash.`);
      } catch (err: any) {
        toast.error(err.message || "Couldn't move to trash.");
      }
  }
}

async function submitName(name: string) {
  const dialog = nameDialog.value;
  if (!dialog) return;
  if (dialog.mode === "create") {
    await filesStore.createFolder(name);
    toast.success(`Folder “${name}” created.`);
  } else {
    await filesStore.renameNode(dialog.node.id, name);
  }
}

function onVersionPicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file && versionFor.value) {
    uploadStore.uploadNewVersion(file, versionFor.value);
    toast.info(`Uploading a new version of “${versionFor.value.name}”.`);
  }
  input.value = "";
  versionFor.value = null;
}

function onDrop(e: DragEvent) {
  dragDepth.value = 0;
  const files = e.dataTransfer?.files;
  if (!files?.length) return;
  if (!canUpload.value) {
    toast.info("Choose a plan to start uploading files.");
    return;
  }
  void uploadStore.uploadFiles(files, filesStore.currentParentId);
}

function onDragEnter(e: DragEvent) {
  if (e.dataTransfer?.types.includes("Files")) dragDepth.value++;
}

function load() {
  if (authStore.masterKey) void filesStore.fetchNodes(filesStore.currentParentId);
}

onMounted(load);
watch(() => authStore.masterKey, (key) => key && load());
watch(() => filesStore.currentParentId, () => (selectedId.value = null));
</script>

<template>
  <div
    class="relative min-h-[60vh]"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent
    @dragleave="dragDepth = Math.max(0, dragDepth - 1)"
    @drop.prevent="onDrop"
  >
    <input ref="versionInput" type="file" class="hidden" @change="onVersionPicked" />

    <!-- Header: breadcrumbs + actions -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <nav v-if="!searching" aria-label="Folder path" class="min-w-0">
        <ol class="flex flex-wrap items-center gap-1 text-lg font-semibold text-slate-900 sm:text-xl">
          <li v-for="(crumb, i) in filesStore.breadcrumbs" :key="crumb.id ?? 'root'" class="flex min-w-0 items-center gap-1">
            <ChevronRight v-if="i > 0" class="h-4 w-4 shrink-0 text-slate-400" />
            <button
              v-if="i < filesStore.breadcrumbs.length - 1"
              class="max-w-[12rem] truncate rounded-md px-1.5 py-0.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              @click="filesStore.navigateToCrumb(i)"
            >
              {{ crumb.name }}
            </button>
            <span v-else class="max-w-[16rem] truncate px-1.5" aria-current="page">{{ crumb.name }}</span>
          </li>
        </ol>
      </nav>
      <div v-else class="min-w-0">
        <h1 class="page-title">Search results</h1>
        <p class="page-subtitle truncate">
          <template v-if="filesStore.isSearching">Searching for “{{ filesStore.searchQuery }}”…</template>
          <template v-else>{{ results.length }} {{ results.length === 1 ? "match" : "matches" }} for “{{ filesStore.searchQuery }}”</template>
        </p>
      </div>

      <div v-if="!searching" class="flex flex-wrap items-center gap-2">
        <button class="btn-secondary" title="Create a new folder here" @click="nameDialog = { mode: 'create' }">
          <FolderPlus class="h-4 w-4" /> New folder
        </button>
        <button class="btn-secondary hidden sm:inline-flex" title="Upload a whole folder" @click="picker.pickFolder()">
          <FolderUp class="h-4 w-4" /> Upload folder
        </button>
        <button class="btn-primary" title="Upload files to this folder" @click="picker.pickFiles()">
          <Upload class="h-4 w-4" /> Upload
        </button>
      </div>
      <button v-else class="btn-secondary self-start sm:self-auto" @click="filesStore.clearSearch()">Clear search</button>
    </div>

    <!-- Filter / sort / view -->
    <div class="mt-5 flex flex-wrap items-center gap-2">
      <label class="sr-only" for="filter">Show</label>
      <select id="filter" v-model="filter" class="input h-9 w-auto pr-8">
        <option v-for="f in FILTERS" :key="f.key" :value="f.key">{{ f.label }}</option>
      </select>
      <label class="sr-only" for="sort">Sort by</label>
      <select id="sort" v-model="sort" class="input h-9 w-auto pr-8">
        <option v-for="s in SORTS" :key="s.key" :value="s.key">Sort: {{ s.label }}</option>
      </select>
      <span v-if="!searching && items.length" class="hidden text-sm text-slate-500 md:inline">
        {{ items.length }} {{ items.length === 1 ? "item" : "items" }}<template v-if="totalSize"> · {{ formatBytes(totalSize) }}</template>
      </span>
      <div class="ml-auto flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-0.5" role="group" aria-label="View">
        <button
          class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm"
          :class="filesStore.viewMode === 'list' ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-900'"
          :aria-pressed="filesStore.viewMode === 'list'"
          title="List view"
          @click="filesStore.setViewMode('list')"
        >
          <List class="h-4 w-4" /><span class="hidden sm:inline">List</span>
        </button>
        <button
          class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm"
          :class="filesStore.viewMode === 'grid' ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-900'"
          :aria-pressed="filesStore.viewMode === 'grid'"
          title="Grid view"
          @click="filesStore.setViewMode('grid')"
        >
          <LayoutGrid class="h-4 w-4" /><span class="hidden sm:inline">Grid</span>
        </button>
      </div>
    </div>

    <div class="mt-4">
      <!-- Vault locked / opening -->
      <div v-if="!authStore.masterKey" class="card card-body flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
        <Loader2 class="h-4 w-4 animate-spin" /> Waiting for your vault to unlock…
      </div>

      <!-- Search states -->
      <template v-else-if="searching">
        <div v-if="filesStore.isSearching && !results.length" class="card card-body flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
          <Loader2 class="h-4 w-4 animate-spin" /> Searching all your folders…
        </div>
        <div v-else-if="filesStore.searchError" class="card card-body py-12 text-center">
          <AlertCircle class="mx-auto h-8 w-8 text-rose-500" />
          <p class="mt-3 text-sm text-slate-700">{{ filesStore.searchError }}</p>
          <button class="btn-secondary mt-4" @click="filesStore.search(filesStore.searchQuery)"><RefreshCw class="h-4 w-4" /> Try again</button>
        </div>
        <div v-else-if="!results.length" class="card card-body py-16 text-center">
          <SearchX class="mx-auto h-10 w-10 text-slate-300" />
          <p class="mt-3 font-medium text-slate-900">No matches</p>
          <p class="mt-1 text-sm text-slate-500">Try a different word or part of the file name.</p>
        </div>
        <FileListView v-else :items="results" :selected-id="selectedId" show-location @select="selectedId = $event.id" @open="open" @menu="openMenu" />
      </template>

      <!-- Folder states -->
      <div v-else-if="filesStore.isLoading && !items.length" class="card overflow-hidden" aria-busy="true">
        <div v-for="i in 6" :key="i" class="flex items-center gap-3 border-b border-slate-100 px-4 py-3 last:border-0">
          <div class="h-9 w-9 animate-pulse rounded-lg bg-slate-100"></div>
          <div class="h-3 w-1/3 animate-pulse rounded bg-slate-100"></div>
        </div>
      </div>
      <div v-else-if="filesStore.loadError" class="card card-body py-12 text-center">
        <AlertCircle class="mx-auto h-8 w-8 text-rose-500" />
        <p class="mt-3 text-sm text-slate-700">{{ filesStore.loadError }}</p>
        <button class="btn-secondary mt-4" @click="load"><RefreshCw class="h-4 w-4" /> Try again</button>
      </div>
      <div v-else-if="!filesStore.nodes.length" class="card card-body flex flex-col items-center py-16 text-center">
        <span class="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-600"><UploadCloud class="h-7 w-7" /></span>
        <template v-if="noPlan">
          <p class="mt-4 font-medium text-slate-900">Welcome to SmartSpace</p>
          <p class="mt-1 max-w-sm text-sm text-slate-500">Choose a plan to start uploading. Your files are encrypted on this device before they leave it.</p>
          <router-link to="/app/billing" class="btn-primary mt-5"><CreditCard class="h-4 w-4" /> See plans</router-link>
        </template>
        <template v-else>
          <p class="mt-4 font-medium text-slate-900">{{ filesStore.currentParentId ? "This folder is empty" : "No files yet" }}</p>
          <p class="mt-1 max-w-sm text-sm text-slate-500">Drag files here, or use the buttons below.</p>
          <div class="mt-5 flex flex-wrap justify-center gap-2">
            <button class="btn-primary" @click="picker.pickFiles()"><Upload class="h-4 w-4" /> Upload files</button>
            <button class="btn-secondary" @click="nameDialog = { mode: 'create' }"><FolderPlus class="h-4 w-4" /> New folder</button>
          </div>
        </template>
      </div>
      <div v-else-if="!items.length" class="card card-body py-12 text-center text-sm text-slate-500">
        Nothing here matches “{{ FILTERS.find((f) => f.key === filter)?.label }}”.
        <button class="ml-1 font-medium text-brand-600 hover:underline" @click="filter = 'all'">Show everything</button>
      </div>
      <template v-else>
        <FileListView v-if="filesStore.viewMode === 'list'" :items="visible" :selected-id="selectedId" @select="selectedId = $event.id" @open="open" @menu="openMenu" />
        <FileGridView v-else :items="visible" :selected-id="selectedId" @select="selectedId = $event.id" @open="open" @menu="openMenu" />
        <p class="mt-3 text-xs text-slate-400 hidden sm:block">Tip: double-click a folder to open it or a file to download it. Right-click for more options.</p>
      </template>
    </div>

    <!-- Drop overlay -->
    <div
      v-if="dragDepth > 0"
      class="pointer-events-none fixed inset-0 z-40 flex items-center justify-center bg-brand-600/10 p-6 backdrop-blur-[1px]"
    >
      <div class="rounded-2xl border-2 border-dashed border-brand-500 bg-white px-10 py-8 text-center shadow-pop">
        <UploadCloud class="mx-auto h-10 w-10 text-brand-600" />
        <p class="mt-3 font-medium text-slate-900">Drop to upload to “{{ filesStore.breadcrumbs.at(-1)?.name }}”</p>
        <p class="mt-1 text-sm text-slate-500">Files are encrypted before they're uploaded.</p>
      </div>
    </div>

    <ItemMenu :node="menu.node" :x="menu.x" :y="menu.y" @select="onMenu" @close="menu = { node: null, x: 0, y: 0 }" />
    <NameDialog
      :open="!!nameDialog"
      :title="nameDialog?.mode === 'rename' ? 'Rename' : 'New folder'"
      :label="nameDialog?.mode === 'rename' ? 'New name' : 'Folder name'"
      :initial="nameDialog?.mode === 'rename' ? nameDialog.node.name : 'Untitled folder'"
      :confirm-label="nameDialog?.mode === 'rename' ? 'Rename' : 'Create'"
      :submit="submitName"
      @close="nameDialog = null"
    />
    <MoveDialog :open="!!moveTarget" :node="moveTarget" @close="moveTarget = null" @moved="toast.success('Moved.')" />
    <VersionsDialog :open="!!versionsTarget" :node="versionsTarget" @close="versionsTarget = null" />
  </div>
</template>

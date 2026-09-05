<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useFilesStore, type FileNode } from "../../stores/files";
import { useUploadStore } from "../../stores/upload";
import PreviewModal from "./PreviewModal.vue";
import ShareModal from "../sharing/ShareModal.vue";
import {
  Folder,
  FileText,
  LayoutGrid,
  List,
  FolderPlus,
  UploadCloud,
  MoreVertical,
  Download,
  Share2,
  Trash2,
  Edit2,
  AlertCircle,
  Clock,
  HardDrive,
  File,
} from "lucide-vue-next";

const filesStore = useFilesStore();
const uploadStore = useUploadStore();

const isDraggingOver = ref(false);
const showCreateFolderModal = ref(false);
const newFolderName = ref("");
const showRenameModal = ref(false);
const renameTargetNode = ref<FileNode | null>(null);
const renameInput = ref("");

// Modals
const previewNode = ref<FileNode | null>(null);
const isPreviewOpen = ref(false);
const shareTargetNode = ref<FileNode | null>(null);
const isShareOpen = ref(false);

// Context menu
const contextMenu = ref<{ x: number; y: number; node: FileNode | null; visible: boolean }>({
  x: 0,
  y: 0,
  node: null,
  visible: false,
});

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function handleNodeClick(node: FileNode, event: MouseEvent) {
  if (node.type === "folder") {
    filesStore.navigateToFolder(node.id, node.name);
  } else {
    // Open preview
    previewNode.value = node;
    isPreviewOpen.value = true;
  }
}

function openContextMenu(event: MouseEvent, node: FileNode) {
  event.preventDefault();
  contextMenu.value = {
    x: event.clientX,
    y: event.clientY,
    node,
    visible: true,
  };
}

function closeContextMenu() {
  contextMenu.value.visible = false;
}

function triggerCreateFolder() {
  newFolderName.value = "";
  showCreateFolderModal.value = true;
}

async function submitCreateFolder() {
  if (!newFolderName.value.trim()) return;
  await filesStore.createFolder(newFolderName.value.trim());
  showCreateFolderModal.value = false;
}

function triggerRename(node: FileNode) {
  renameTargetNode.value = node;
  renameInput.value = node.name;
  showRenameModal.value = true;
  closeContextMenu();
}

async function submitRename() {
  if (renameTargetNode.value && renameInput.value.trim()) {
    await filesStore.renameNode(renameTargetNode.value.id, renameInput.value.trim());
    showRenameModal.value = false;
  }
}

function triggerShare(node: FileNode) {
  shareTargetNode.value = node;
  isShareOpen.value = true;
  closeContextMenu();
}

async function triggerTrash(node: FileNode) {
  await filesStore.trashNode(node.id);
  closeContextMenu();
}

// Drag and drop file upload handling
function onDragOver(e: DragEvent) {
  e.preventDefault();
  isDraggingOver.value = true;
}

function onDragLeave() {
  isDraggingOver.value = false;
}

function onDrop(e: DragEvent) {
  e.preventDefault();
  isDraggingOver.value = false;
  if (e.dataTransfer?.files) {
    Array.from(e.dataTransfer.files).forEach((file) => {
      uploadStore.uploadFile(file, filesStore.currentParentId);
    });
  }
}

// Keyboard shortcuts: Del, F2, Escape
function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    closeContextMenu();
    isPreviewOpen.value = false;
    isShareOpen.value = false;
    showCreateFolderModal.value = false;
    showRenameModal.value = false;
  }
}

onMounted(() => {
  window.addEventListener("click", closeContextMenu);
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener("click", closeContextMenu);
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <div
    class="h-full flex flex-col space-y-6 relative"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- Drag overlay -->
    <div
      v-if="isDraggingOver"
      class="absolute inset-0 z-40 bg-brand-600/20 border-2 border-dashed border-brand-400 rounded-3xl flex items-center justify-center backdrop-blur-sm pointer-events-none"
    >
      <div class="p-6 rounded-2xl bg-slate-900/90 border border-brand-500/40 text-center space-y-2">
        <UploadCloud class="w-10 h-10 text-brand-400 mx-auto animate-bounce" />
        <div class="text-sm font-bold text-white">Drop files here to encrypt & upload</div>
        <p class="text-xs text-slate-400">Zero-knowledge AES-256-GCM chunking direct to R2</p>
      </div>
    </div>

    <!-- Actions toolbar -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <button
          @click="triggerCreateFolder"
          class="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-white flex items-center space-x-2 transition-colors shadow-sm"
        >
          <FolderPlus class="w-4 h-4 text-brand-400" />
          <span>New Folder</span>
        </button>
      </div>

      <!-- View Toggle -->
      <div class="flex items-center p-1 rounded-xl bg-slate-900 border border-slate-800">
        <button
          @click="filesStore.viewMode = 'grid'"
          class="p-1.5 rounded-lg transition-colors"
          :class="filesStore.viewMode === 'grid' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
          title="Grid view"
        >
          <LayoutGrid class="w-4 h-4" />
        </button>
        <button
          @click="filesStore.viewMode = 'list'"
          class="p-1.5 rounded-lg transition-colors"
          :class="filesStore.viewMode === 'list' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-white'"
          title="List view"
        >
          <List class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- STATE 1: LOADING (Skeletons) -->
    <div v-if="filesStore.isLoading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      <div v-for="i in 8" :key="i" class="p-4 rounded-2xl glass-panel border border-slate-800 animate-pulse space-y-3">
        <div class="w-10 h-10 rounded-xl bg-slate-800"></div>
        <div class="h-3 bg-slate-800 rounded w-3/4"></div>
        <div class="h-2 bg-slate-800 rounded w-1/2"></div>
      </div>
    </div>

    <!-- STATE 2: EMPTY STATE -->
    <div
      v-else-if="filesStore.nodes.length === 0"
      class="flex-1 flex flex-col items-center justify-center p-12 text-center rounded-3xl border border-dashed border-slate-800/80 bg-slate-900/20"
    >
      <div class="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4">
        <UploadCloud class="w-8 h-8 text-brand-400" />
      </div>
      <h3 class="text-base font-bold text-white">This folder is empty</h3>
      <p class="text-xs text-slate-400 max-w-sm mt-1 mb-6">
        Drag & drop files anywhere, or click below to encrypt and upload directly to zero-egress storage.
      </p>
      <button
        @click="triggerCreateFolder"
        class="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-xs font-semibold text-white shadow-md transition-all"
      >
        Create a Folder
      </button>
    </div>

    <!-- STATE 3 & 4: POPULATED VIEW -->
    <div v-else>
      <!-- Grid View -->
      <div v-if="filesStore.viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        <div
          v-for="node in filesStore.nodes"
          :key="node.id"
          @click="handleNodeClick(node, $event)"
          @contextmenu="openContextMenu($event, node)"
          class="group p-4 rounded-2xl glass-card border border-slate-800/80 hover:border-brand-500/40 cursor-pointer transition-all flex flex-col justify-between space-y-3 relative"
        >
          <div class="flex items-start justify-between">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center" :class="node.type === 'folder' ? 'bg-amber-500/10 text-amber-400' : 'bg-brand-500/10 text-brand-400'">
              <Folder v-if="node.type === 'folder'" class="w-5 h-5 fill-amber-400/20" />
              <FileText v-else class="w-5 h-5" />
            </div>

            <button
              @click.stop="openContextMenu($event, node)"
              class="p-1 rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreVertical class="w-4 h-4" />
            </button>
          </div>

          <div class="min-w-0">
            <div class="text-xs font-semibold text-slate-200 truncate group-hover:text-brand-300" :title="node.name">
              {{ node.name }}
            </div>
            <div class="text-[10px] text-slate-400 font-mono mt-0.5">
              {{ node.type === 'folder' ? 'Folder' : formatBytes(node.size_bytes) }}
            </div>
          </div>
        </div>
      </div>

      <!-- List View -->
      <div v-else class="rounded-2xl border border-slate-800 overflow-hidden bg-slate-900/40 divide-y divide-slate-800/60">
        <div
          v-for="node in filesStore.nodes"
          :key="node.id"
          @click="handleNodeClick(node, $event)"
          @contextmenu="openContextMenu($event, node)"
          class="flex items-center justify-between px-4 py-3 hover:bg-slate-800/40 cursor-pointer transition-colors text-xs"
        >
          <div class="flex items-center space-x-3 min-w-0">
            <Folder v-if="node.type === 'folder'" class="w-5 h-5 text-amber-400 fill-amber-400/20 shrink-0" />
            <FileText v-else class="w-5 h-5 text-brand-400 shrink-0" />
            <span class="font-medium text-slate-200 truncate max-w-md">{{ node.name }}</span>
          </div>

          <div class="flex items-center space-x-6 text-slate-400 font-mono text-[11px]">
            <span>{{ node.type === 'folder' ? '--' : formatBytes(node.size_bytes) }}</span>
            <button
              @click.stop="openContextMenu($event, node)"
              class="p-1 text-slate-500 hover:text-white rounded"
            >
              <MoreVertical class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Context Menu Dropdown -->
    <div
      v-if="contextMenu.visible && contextMenu.node"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      class="fixed z-50 w-48 rounded-2xl glass-panel border border-slate-700/80 p-1.5 shadow-2xl space-y-1 bg-[#0c1427]/98 text-xs font-medium text-slate-200"
    >
      <button
        v-if="contextMenu.node.type === 'file'"
        @click="previewNode = contextMenu.node; isPreviewOpen = true; closeContextMenu()"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-800 hover:text-white transition-colors"
      >
        <FileText class="w-4 h-4 text-brand-400" />
        <span>Preview & Decrypt</span>
      </button>

      <button
        @click="triggerShare(contextMenu.node)"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-800 hover:text-white transition-colors"
      >
        <Share2 class="w-4 h-4 text-brand-400" />
        <span>Share Link (#key)</span>
      </button>

      <button
        @click="triggerRename(contextMenu.node)"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-800 hover:text-white transition-colors"
      >
        <Edit2 class="w-4 h-4 text-slate-400" />
        <span>Rename</span>
      </button>

      <div class="border-t border-slate-800 my-1"></div>

      <button
        @click="triggerTrash(contextMenu.node)"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-rose-500/20 text-rose-400 transition-colors"
      >
        <Trash2 class="w-4 h-4" />
        <span>Move to Trash</span>
      </button>
    </div>

    <!-- Create Folder Modal -->
    <div v-if="showCreateFolderModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div class="glass-panel w-full max-w-sm rounded-3xl p-6 border border-slate-700 space-y-4 bg-[#0c1427]/95">
        <h3 class="text-sm font-bold text-white">Create New Folder</h3>
        <input
          type="text"
          v-model="newFolderName"
          placeholder="Folder name..."
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-brand-500"
          autofocus
          @keyup.enter="submitCreateFolder"
        />
        <div class="flex justify-end space-x-2 pt-2">
          <button @click="showCreateFolderModal = false" class="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white">
            Cancel
          </button>
          <button @click="submitCreateFolder" class="px-4 py-2 rounded-xl bg-brand-600 text-white font-bold text-xs shadow-md">
            Create
          </button>
        </div>
      </div>
    </div>

    <!-- Rename Modal -->
    <div v-if="showRenameModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div class="glass-panel w-full max-w-sm rounded-3xl p-6 border border-slate-700 space-y-4 bg-[#0c1427]/95">
        <h3 class="text-sm font-bold text-white">Rename</h3>
        <input
          type="text"
          v-model="renameInput"
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-brand-500"
          autofocus
          @keyup.enter="submitRename"
        />
        <div class="flex justify-end space-x-2 pt-2">
          <button @click="showRenameModal = false" class="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white">
            Cancel
          </button>
          <button @click="submitRename" class="px-4 py-2 rounded-xl bg-brand-600 text-white font-bold text-xs shadow-md">
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <PreviewModal
      :is-open="isPreviewOpen"
      :node="previewNode"
      @close="isPreviewOpen = false"
    />

    <!-- Share Modal -->
    <ShareModal
      :is-open="isShareOpen"
      :node="shareTargetNode"
      @close="isShareOpen = false"
    />
  </div>
</template>

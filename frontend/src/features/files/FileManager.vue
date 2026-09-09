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
  Lock,
  FileCode,
  FileArchive,
  FileImage,
  FileVideo,
  FileAudio,
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

function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  if (["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext)) return FileImage;
  if (["mp4", "webm", "mkv", "mov"].includes(ext)) return FileVideo;
  if (["mp3", "wav", "flac", "aac"].includes(ext)) return FileAudio;
  if (["zip", "tar", "gz", "7z", "rar"].includes(ext)) return FileArchive;
  if (["js", "ts", "py", "html", "css", "json", "vue", "rs", "go"].includes(ext)) return FileCode;
  if (["pdf", "doc", "docx", "txt", "md"].includes(ext)) return FileText;
  return File;
}

function handleNodeClick(node: FileNode) {
  if (node.type === "folder") {
    filesStore.navigateToFolder(node.id, node.name);
  } else {
    previewNode.value = node;
    isPreviewOpen.value = true;
  }
}

function openContextMenu(event: MouseEvent, node: FileNode) {
  event.preventDefault();
  contextMenu.value = {
    x: Math.min(event.clientX, window.innerWidth - 200),
    y: Math.min(event.clientY, window.innerHeight - 200),
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
    class="h-full flex flex-col space-y-5 relative text-slate-900"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <!-- Drag & Drop Overlay -->
    <div
      v-if="isDraggingOver"
      class="absolute inset-0 z-40 bg-blue-50/80 border-2 border-dashed border-blue-500 rounded-2xl flex items-center justify-center backdrop-blur-xs pointer-events-none"
    >
      <div class="p-6 rounded-2xl bg-white border border-slate-200 text-center space-y-2 shadow-xl">
        <UploadCloud class="w-8 h-8 text-blue-600 mx-auto animate-pulse" />
        <div class="text-sm font-semibold text-slate-900">Drop to encrypt & upload directly</div>
        <p class="text-xs text-slate-500 font-medium">Zero-Knowledge AES-256-GCM Slicing</p>
      </div>
    </div>

    <!-- Actions Toolbar -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2.5">
        <button
          @click="triggerCreateFolder"
          class="btn-secondary px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-700 flex items-center space-x-1.5 shadow-2xs"
        >
          <FolderPlus class="w-3.5 h-3.5 text-blue-600" />
          <span>New Folder</span>
        </button>
      </div>

      <!-- View Switcher -->
      <div class="flex items-center p-0.5 rounded-xl bg-slate-100 border border-slate-200">
        <button
          @click="filesStore.viewMode = 'grid'"
          class="p-1.5 rounded-lg transition-all"
          :class="filesStore.viewMode === 'grid' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'"
          title="Grid view"
        >
          <LayoutGrid class="w-3.5 h-3.5" />
        </button>
        <button
          @click="filesStore.viewMode = 'list'"
          class="p-1.5 rounded-lg transition-all"
          :class="filesStore.viewMode === 'list' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'"
          title="List view"
        >
          <List class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- Loading Skeletons -->
    <div v-if="filesStore.isLoading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3.5">
      <div v-for="i in 10" :key="i" class="p-4 rounded-2xl bg-white border border-slate-200 animate-pulse space-y-3">
        <div class="w-9 h-9 rounded-xl bg-slate-100"></div>
        <div class="h-3 bg-slate-100 rounded w-3/4"></div>
        <div class="h-2 bg-slate-100 rounded w-1/2"></div>
      </div>
    </div>

    <!-- Empty Vault State -->
    <div
      v-else-if="filesStore.nodes.length === 0"
      class="flex-1 flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-dashed border-slate-300 bg-white shadow-2xs"
    >
      <div class="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-3">
        <Lock class="w-5 h-5 text-blue-600" />
      </div>
      <h3 class="text-sm font-bold text-slate-900">This folder is empty</h3>
      <p class="text-xs text-slate-500 max-w-sm mt-1 mb-5">
        Drag and drop files here, or click "Upload Encrypted Files" to store files securely in your vault.
      </p>
      <button
        @click="triggerCreateFolder"
        class="btn-secondary px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 shadow-xs"
      >
        Create a Folder
      </button>
    </div>

    <!-- Populated Files View -->
    <div v-else>
      <!-- Grid View -->
      <div v-if="filesStore.viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3.5">
        <div
          v-for="node in filesStore.nodes"
          :key="node.id"
          @click="handleNodeClick(node)"
          @contextmenu="openContextMenu($event, node)"
          class="bg-white group p-3.5 rounded-2xl border border-slate-200 hover:border-slate-300 shadow-2xs hover:shadow cursor-pointer flex flex-col justify-between space-y-3 relative select-none transition-all"
        >
          <div class="flex items-start justify-between">
            <div
              class="w-10 h-10 rounded-xl flex items-center justify-center"
              :class="node.type === 'folder' ? 'bg-amber-50 text-amber-600 border border-amber-200/80' : 'bg-blue-50 text-blue-600 border border-blue-200/80'"
            >
              <Folder v-if="node.type === 'folder'" class="w-5 h-5 fill-amber-500/20" />
              <component v-else :is="getFileIcon(node.name)" class="w-5 h-5" />
            </div>

            <button
              @click.stop="openContextMenu($event, node)"
              class="p-1 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreVertical class="w-3.5 h-3.5" />
            </button>
          </div>

          <div class="min-w-0">
            <div class="text-xs font-semibold text-slate-900 truncate group-hover:text-blue-600 transition-colors" :title="node.name">
              {{ node.name }}
            </div>
            <div class="text-[10px] text-slate-500 font-mono mt-0.5">
              {{ node.type === 'folder' ? 'Folder' : formatBytes(node.size_bytes) }}
            </div>
          </div>
        </div>
      </div>

      <!-- List / Table View -->
      <div v-else class="bg-white rounded-2xl border border-slate-200 overflow-hidden divide-y divide-slate-100 shadow-2xs">
        <div
          v-for="node in filesStore.nodes"
          :key="node.id"
          @click="handleNodeClick(node)"
          @contextmenu="openContextMenu($event, node)"
          class="flex items-center justify-between px-4 py-3 hover:bg-slate-50/80 cursor-pointer transition-colors text-xs select-none"
        >
          <div class="flex items-center space-x-3 min-w-0">
            <Folder v-if="node.type === 'folder'" class="w-4 h-4 text-amber-600 fill-amber-500/20 shrink-0" />
            <component v-else :is="getFileIcon(node.name)" class="w-4 h-4 text-blue-600 shrink-0" />
            <span class="font-medium text-slate-900 truncate max-w-md">{{ node.name }}</span>
          </div>

          <div class="flex items-center space-x-6 text-slate-500 font-mono text-[11px]">
            <span>{{ node.type === 'folder' ? '—' : formatBytes(node.size_bytes) }}</span>
            <button
              @click.stop="openContextMenu($event, node)"
              class="p-1 text-slate-400 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <MoreVertical class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Context Menu Dropdown -->
    <div
      v-if="contextMenu.visible && contextMenu.node"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      class="fixed z-50 w-48 rounded-2xl p-1.5 shadow-xl space-y-0.5 text-xs font-medium text-slate-700 border border-slate-200 bg-white"
    >
      <button
        v-if="contextMenu.node.type === 'file'"
        @click="previewNode = contextMenu.node; isPreviewOpen = true; closeContextMenu()"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
      >
        <FileText class="w-3.5 h-3.5 text-blue-600" />
        <span>Preview & Decrypt</span>
      </button>

      <button
        @click="triggerShare(contextMenu.node)"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
      >
        <Share2 class="w-3.5 h-3.5 text-blue-600" />
        <span>Share Link (#key)</span>
      </button>

      <button
        @click="triggerRename(contextMenu.node)"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
      >
        <Edit2 class="w-3.5 h-3.5 text-slate-500" />
        <span>Rename</span>
      </button>

      <div class="border-t border-slate-100 my-1"></div>

      <button
        @click="triggerTrash(contextMenu.node)"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-rose-50 text-rose-600 transition-colors"
      >
        <Trash2 class="w-3.5 h-3.5" />
        <span>Move to Trash</span>
      </button>
    </div>

    <!-- Create Folder Modal -->
    <div v-if="showCreateFolderModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div class="bg-white w-full max-w-sm rounded-2xl p-6 border border-slate-200 space-y-4 shadow-xl">
        <h3 class="text-sm font-bold text-slate-900">Create New Folder</h3>
        <input
          type="text"
          v-model="newFolderName"
          placeholder="Folder name..."
          class="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
          autofocus
          @keyup.enter="submitCreateFolder"
        />
        <div class="flex justify-end space-x-2 pt-1">
          <button @click="showCreateFolderModal = false" class="btn-secondary px-3.5 py-1.5 rounded-xl text-xs font-medium">
            Cancel
          </button>
          <button @click="submitCreateFolder" class="btn-primary px-4 py-1.5 rounded-xl text-xs font-semibold">
            Create Folder
          </button>
        </div>
      </div>
    </div>

    <!-- Rename Modal -->
    <div v-if="showRenameModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div class="bg-white w-full max-w-sm rounded-2xl p-6 border border-slate-200 space-y-4 shadow-xl">
        <h3 class="text-sm font-bold text-slate-900">Rename</h3>
        <input
          type="text"
          v-model="renameInput"
          class="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all"
          autofocus
          @keyup.enter="submitRename"
        />
        <div class="flex justify-end space-x-2 pt-1">
          <button @click="showRenameModal = false" class="btn-secondary px-3.5 py-1.5 rounded-xl text-xs font-medium">
            Cancel
          </button>
          <button @click="submitRename" class="btn-primary px-4 py-1.5 rounded-xl text-xs font-semibold">
            Save Changes
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

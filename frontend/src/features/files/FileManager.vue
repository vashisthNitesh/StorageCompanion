<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useFilesStore, type FileNode } from "../../stores/files";
import { useUploadStore } from "../../stores/upload";
import { useAuthStore } from "../../stores/auth";
import { useFileDownload } from "./useFileDownload";
import PreviewModal from "./PreviewModal.vue";
import ShareModal from "../sharing/ShareModal.vue";
import {
  Folder,
  FolderPlus,
  FolderUp,
  FileText,
  FileSpreadsheet,
  FileVideo,
  FileAudio,
  FileImage,
  FileCode,
  FileArchive,
  File,
  LayoutGrid,
  List,
  UploadCloud,
  MoreVertical,
  Download,
  Share2,
  Trash2,
  Edit2,
  Lock,
  Eye,
  Loader2,
  ShieldCheck,
  Sparkles,
  ArrowUpDown,
  Search,
  Plus,
} from "lucide-vue-next";

const router = useRouter();
const filesStore = useFilesStore();
const uploadStore = useUploadStore();
const authStore = useAuthStore();
const { isDownloading, downloadFile } = useFileDownload();

const isDraggingOver = ref(false);
const showCreateFolderModal = ref(false);
const newFolderName = ref("");
const showRenameModal = ref(false);
const renameTargetNode = ref<FileNode | null>(null);
const renameInput = ref("");

// In-vault file input refs
const vaultFileInputRef = ref<HTMLInputElement | null>(null);
const vaultFolderInputRef = ref<HTMLInputElement | null>(null);

// Filters & Sorting
const activeFilter = ref<"all" | "folders" | "documents" | "media" | "archives">("all");
const activeSort = ref<"name_asc" | "name_desc" | "size_desc" | "size_asc">("name_asc");

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
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

interface FileMeta {
  label: string;
  ext: string;
  category: "doc" | "video" | "audio" | "image" | "archive" | "code" | "sheet" | "file";
  badgeClass: string;
  iconBgClass: string;
  icon: any;
  typeName: string;
}

function getFileMeta(name: string): FileMeta {
  const ext = name?.split(".").pop()?.toLowerCase() || "";

  if (["pdf"].includes(ext)) {
    return {
      label: "PDF",
      ext,
      category: "doc",
      badgeClass: "bg-rose-50 text-rose-600 border-rose-200/80",
      iconBgClass: "bg-rose-50 text-rose-600 border-rose-100",
      icon: FileText,
      typeName: "PDF Document",
    };
  }
  if (["docx", "doc", "odt", "rtf"].includes(ext)) {
    return {
      label: ext.toUpperCase(),
      ext,
      category: "doc",
      badgeClass: "bg-blue-50 text-blue-600 border-blue-200/80",
      iconBgClass: "bg-blue-50 text-blue-600 border-blue-100",
      icon: FileText,
      typeName: "Word Document",
    };
  }
  if (["xlsx", "xls", "csv", "tsv"].includes(ext)) {
    return {
      label: ext.toUpperCase(),
      ext,
      category: "sheet",
      badgeClass: "bg-emerald-50 text-emerald-600 border-emerald-200/80",
      iconBgClass: "bg-emerald-50 text-emerald-600 border-emerald-100",
      icon: FileSpreadsheet,
      typeName: "Spreadsheet",
    };
  }
  if (["mp4", "webm", "mkv", "mov", "avi", "m4v"].includes(ext)) {
    return {
      label: "VIDEO",
      ext,
      category: "video",
      badgeClass: "bg-purple-50 text-purple-600 border-purple-200/80",
      iconBgClass: "bg-purple-50 text-purple-600 border-purple-100",
      icon: FileVideo,
      typeName: "Video",
    };
  }
  if (["mp3", "wav", "ogg", "m4a", "flac", "aac"].includes(ext)) {
    return {
      label: "AUDIO",
      ext,
      category: "audio",
      badgeClass: "bg-amber-50 text-amber-600 border-amber-200/80",
      iconBgClass: "bg-amber-50 text-amber-600 border-amber-100",
      icon: FileAudio,
      typeName: "Audio",
    };
  }
  if (["png", "jpg", "jpeg", "webp", "gif", "svg", "bmp", "avif"].includes(ext)) {
    return {
      label: "IMAGE",
      ext,
      category: "image",
      badgeClass: "bg-teal-50 text-teal-600 border-teal-200/80",
      iconBgClass: "bg-teal-50 text-teal-600 border-teal-100",
      icon: FileImage,
      typeName: "Image",
    };
  }
  if (["zip", "tar", "gz", "7z", "rar", "bz2"].includes(ext)) {
    return {
      label: "ZIP",
      ext,
      category: "archive",
      badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
      iconBgClass: "bg-slate-100 text-slate-600 border-slate-200",
      icon: FileArchive,
      typeName: "Archive",
    };
  }
  if (["js", "ts", "py", "html", "css", "json", "vue", "rs", "go", "java", "c", "cpp", "sql", "sh", "yaml", "yml"].includes(ext)) {
    return {
      label: "CODE",
      ext,
      category: "code",
      badgeClass: "bg-sky-50 text-sky-600 border-sky-200/80",
      iconBgClass: "bg-sky-50 text-sky-600 border-sky-100",
      icon: FileCode,
      typeName: "Source Code",
    };
  }
  return {
    label: ext ? ext.toUpperCase() : "FILE",
    ext,
    category: "file",
    badgeClass: "bg-slate-100 text-slate-600 border-slate-200",
    iconBgClass: "bg-slate-50 text-slate-600 border-slate-200",
    icon: File,
    typeName: "Encrypted File",
  };
}

const filteredNodes = computed(() => {
  let list = [...filesStore.nodes];

  if (activeFilter.value === "folders") {
    list = list.filter((n) => n.type === "folder");
  } else if (activeFilter.value === "documents") {
    list = list.filter((n) => n.type === "file" && ["doc", "sheet"].includes(getFileMeta(n.name).category));
  } else if (activeFilter.value === "media") {
    list = list.filter((n) => n.type === "file" && ["video", "audio", "image"].includes(getFileMeta(n.name).category));
  } else if (activeFilter.value === "archives") {
    list = list.filter((n) => n.type === "file" && getFileMeta(n.name).category === "archive");
  }

  if (activeSort.value === "name_asc") {
    list.sort((a, b) => a.name.localeCompare(b.name));
  } else if (activeSort.value === "name_desc") {
    list.sort((a, b) => b.name.localeCompare(a.name));
  } else if (activeSort.value === "size_desc") {
    list.sort((a, b) => (b.size_bytes || 0) - (a.size_bytes || 0));
  } else if (activeSort.value === "size_asc") {
    list.sort((a, b) => (a.size_bytes || 0) - (b.size_bytes || 0));
  }

  return list;
});

const folders = computed(() => filteredNodes.value.filter((n) => n.type === "folder"));
const files = computed(() => filteredNodes.value.filter((n) => n.type === "file"));

const totalFilesSize = computed(() => {
  const total = files.value.reduce((acc, f) => acc + (f.size_bytes || 0), 0);
  return formatBytes(total);
});

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
    x: Math.min(event.clientX, window.innerWidth - 220),
    y: Math.min(event.clientY, window.innerHeight - 240),
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

function triggerVaultFileUpload() {
  if (!authStore.hasActiveSubscription) {
    router.push({ path: "/app/billing", query: { gate: "required" } });
    return;
  }
  vaultFileInputRef.value?.click();
}

function triggerVaultFolderUpload() {
  if (!authStore.hasActiveSubscription) {
    router.push({ path: "/app/billing", query: { gate: "required" } });
    return;
  }
  vaultFolderInputRef.value?.click();
}

function handleVaultFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    Array.from(target.files).forEach((file) => {
      uploadStore.uploadFile(file, filesStore.currentParentId);
    });
    target.value = "";
  }
}

function onDragOver(e: DragEvent) {
  e.preventDefault();
  isDraggingOver.value = true;
}

function onDragLeave(e: DragEvent) {
  // Only dismiss if leaving the container boundaries
  if (e.currentTarget === e.target) {
    isDraggingOver.value = false;
  }
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
    <!-- Hidden In-Vault Upload Inputs -->
    <input ref="vaultFileInputRef" type="file" multiple class="hidden" @change="handleVaultFileSelect" />
    <input ref="vaultFolderInputRef" type="file" webkitdirectory directory class="hidden" @change="handleVaultFileSelect" />

    <!-- Full Drag & Drop Overlay -->
    <div
      v-if="isDraggingOver"
      class="fixed inset-0 z-50 bg-blue-600/10 backdrop-blur-sm border-4 border-dashed border-blue-500 rounded-3xl flex items-center justify-center pointer-events-none transition-all"
    >
      <div class="p-8 rounded-3xl bg-white/95 border border-blue-200 text-center space-y-3 shadow-2xl scale-105 transition-transform">
        <div class="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mx-auto text-blue-600">
          <UploadCloud class="w-8 h-8 animate-bounce" />
        </div>
        <div class="text-base font-bold text-slate-900">Drop files anywhere to encrypt & upload</div>
        <div class="flex items-center justify-center space-x-2 text-xs text-slate-500">
          <span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-mono font-medium">
            <Lock class="w-3 h-3" />
            <span>AES-256-GCM Slicing</span>
          </span>
          <span>•</span>
          <span>Zero-Knowledge Vault</span>
        </div>
      </div>
    </div>

    <!-- Vault Action Bar & Primary Controls -->
    <div class="bg-white rounded-2xl border border-slate-200/90 p-4 shadow-xs flex flex-wrap items-center justify-between gap-3">
      <!-- Left: In-Vault Upload Actions & Folder Creation -->
      <div class="flex flex-wrap items-center gap-2.5">
        <!-- Primary Upload Button -->
        <button
          @click="triggerVaultFileUpload"
          class="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-sm shadow-blue-500/20 hover:shadow-md hover:shadow-blue-500/25 active:scale-95 transition-all flex items-center space-x-2"
        >
          <UploadCloud class="w-4 h-4" />
          <span>Upload Files</span>
        </button>

        <!-- Upload Folder Button -->
        <button
          @click="triggerVaultFolderUpload"
          class="btn-secondary px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:text-slate-900 flex items-center space-x-1.5 shadow-2xs hover:bg-slate-100 transition-colors"
          title="Upload entire folder directory"
        >
          <FolderUp class="w-4 h-4 text-indigo-600" />
          <span class="hidden sm:inline">Upload Folder</span>
        </button>

        <!-- New Folder Button -->
        <button
          @click="triggerCreateFolder"
          class="btn-secondary px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:text-slate-900 flex items-center space-x-1.5 shadow-2xs hover:bg-slate-100 transition-colors"
        >
          <FolderPlus class="w-4 h-4 text-blue-600" />
          <span>New Folder</span>
        </button>
      </div>

      <!-- Right: Category Filters, Sort, and View Mode Toggle -->
      <div class="flex items-center gap-2.5">
        <!-- Category Filter Pills -->
        <div class="hidden md:flex items-center p-0.5 rounded-xl bg-slate-100 border border-slate-200 text-xs font-medium text-slate-600">
          <button
            @click="activeFilter = 'all'"
            class="px-2.5 py-1 rounded-lg transition-all"
            :class="activeFilter === 'all' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'hover:text-slate-900'"
          >
            All ({{ filesStore.nodes.length }})
          </button>
          <button
            @click="activeFilter = 'documents'"
            class="px-2.5 py-1 rounded-lg transition-all"
            :class="activeFilter === 'documents' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'hover:text-slate-900'"
          >
            Documents
          </button>
          <button
            @click="activeFilter = 'media'"
            class="px-2.5 py-1 rounded-lg transition-all"
            :class="activeFilter === 'media' ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'hover:text-slate-900'"
          >
            Media
          </button>
        </div>

        <!-- Sort Select -->
        <div class="relative">
          <select
            v-model="activeSort"
            class="appearance-none bg-slate-100/80 hover:bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700 py-1.5 pl-2.5 pr-7 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-100 transition-colors cursor-pointer"
          >
            <option value="name_asc">Name (A–Z)</option>
            <option value="name_desc">Name (Z–A)</option>
            <option value="size_desc">Size (Largest)</option>
            <option value="size_asc">Size (Smallest)</option>
          </select>
          <ArrowUpDown class="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        <!-- Grid / List Switcher -->
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
    </div>

    <!-- Quick In-Vault Dropzone Banner (Interactive) -->
    <div
      @click="triggerVaultFileUpload"
      class="bg-gradient-to-r from-blue-50/70 via-indigo-50/40 to-slate-50/60 border border-dashed border-blue-200/90 hover:border-blue-400/90 rounded-2xl p-3.5 px-5 flex items-center justify-between cursor-pointer group shadow-2xs transition-all hover:bg-blue-50/90"
    >
      <div class="flex items-center space-x-3.5">
        <div class="w-10 h-10 rounded-xl bg-white border border-blue-100 flex items-center justify-center text-blue-600 shadow-2xs group-hover:scale-105 group-hover:text-blue-700 transition-all">
          <UploadCloud class="w-5 h-5" />
        </div>
        <div>
          <div class="text-xs font-bold text-slate-900 flex items-center space-x-2">
            <span>Drag & drop files or folders here to encrypt & store</span>
            <span class="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100/70 text-blue-700 font-mono">
              <Lock class="w-2.5 h-2.5" />
              <span>AES-256-GCM</span>
            </span>
          </div>
          <p class="text-[11px] text-slate-500 mt-0.5">
            Files are sliced into 8MB chunks and encrypted client-side before upload.
          </p>
        </div>
      </div>
      <button
        @click.stop="triggerVaultFileUpload"
        class="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold hover:border-blue-300 hover:text-blue-600 shadow-2xs transition-colors"
      >
        <Plus class="w-3.5 h-3.5" />
        <span>Browse Files</span>
      </button>
    </div>

    <!-- Loading Skeletons -->
    <div v-if="filesStore.isLoading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      <div v-for="i in 10" :key="i" class="p-4 rounded-2xl bg-white border border-slate-200 animate-pulse space-y-3">
        <div class="w-10 h-10 rounded-xl bg-slate-100"></div>
        <div class="h-3 bg-slate-100 rounded w-3/4"></div>
        <div class="h-2 bg-slate-100 rounded w-1/2"></div>
      </div>
    </div>

    <!-- Empty Vault State -->
    <div
      v-else-if="filesStore.nodes.length === 0"
      class="flex-1 flex flex-col items-center justify-center p-12 text-center rounded-3xl border border-dashed border-slate-300 bg-white/80 shadow-2xs space-y-4"
    >
      <div class="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shadow-xs">
        <UploadCloud class="w-8 h-8" />
      </div>
      <div class="space-y-1">
        <h3 class="text-sm font-bold text-slate-900">This vault folder is empty</h3>
        <p class="text-xs text-slate-500 max-w-sm">
          Upload files or create a subfolder to get started. All contents are fully encrypted in memory.
        </p>
      </div>
      <div class="flex items-center space-x-2 pt-2">
        <button
          @click="triggerVaultFileUpload"
          class="btn-primary px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-1.5 shadow-sm"
        >
          <UploadCloud class="w-4 h-4" />
          <span>Upload Encrypted Files</span>
        </button>
        <button
          @click="triggerCreateFolder"
          class="btn-secondary px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 shadow-xs"
        >
          Create a Folder
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div v-else class="space-y-6">
      <!-- 1. Folders Section (if any folders present) -->
      <div v-if="folders.length > 0" class="space-y-3">
        <div class="flex items-center justify-between text-xs font-bold text-slate-700 tracking-tight">
          <div class="flex items-center space-x-2">
            <span>Folders</span>
            <span class="px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200/80 text-amber-700 text-[10px] font-mono">
              {{ folders.length }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3.5">
          <div
            v-for="folder in folders"
            :key="folder.id"
            @click="handleNodeClick(folder)"
            @contextmenu="openContextMenu($event, folder)"
            class="group p-3.5 rounded-2xl bg-white border border-slate-200/90 hover:border-amber-300 shadow-2xs hover:shadow-md hover:-translate-y-0.5 cursor-pointer flex flex-col justify-between space-y-3 relative select-none transition-all"
          >
            <div class="flex items-start justify-between">
              <div class="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200/80 flex items-center justify-center text-amber-600 shadow-2xs group-hover:scale-105 transition-transform">
                <Folder class="w-5 h-5 fill-amber-500/25" />
              </div>

              <!-- Quick action dots -->
              <button
                @click.stop="openContextMenu($event, folder)"
                class="p-1 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Folder options"
              >
                <MoreVertical class="w-3.5 h-3.5" />
              </button>
            </div>

            <div class="min-w-0">
              <div class="text-xs font-bold text-slate-900 truncate group-hover:text-amber-700 transition-colors" :title="folder.name">
                {{ folder.name }}
              </div>
              <div class="text-[10px] text-slate-400 font-mono mt-0.5">
                Encrypted Directory
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Files Section (if any files present) -->
      <div v-if="files.length > 0" class="space-y-3">
        <div class="flex items-center justify-between text-xs font-bold text-slate-700 tracking-tight">
          <div class="flex items-center space-x-2">
            <span>Files</span>
            <span class="px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200/80 text-blue-700 text-[10px] font-mono">
              {{ files.length }}
            </span>
            <span class="text-[11px] text-slate-400 font-mono font-normal">
              • {{ totalFilesSize }} total
            </span>
          </div>
        </div>

        <!-- Files Grid View -->
        <div v-if="filesStore.viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3.5">
          <div
            v-for="file in files"
            :key="file.id"
            @click="handleNodeClick(file)"
            @contextmenu="openContextMenu($event, file)"
            class="group p-4 rounded-2xl bg-white border border-slate-200/90 hover:border-blue-300 shadow-2xs hover:shadow-lg hover:-translate-y-1 cursor-pointer flex flex-col justify-between space-y-3.5 relative select-none transition-all duration-200"
          >
            <!-- Card Header: Type Badge & Action Buttons -->
            <div class="flex items-center justify-between">
              <span
                class="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border tracking-wider uppercase"
                :class="getFileMeta(file.name).badgeClass"
              >
                {{ getFileMeta(file.name).label }}
              </span>

              <div class="flex items-center space-x-1">
                <!-- Direct Download Button with Tooltip -->
                <button
                  @click.stop="downloadFile(file)"
                  class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                  :title="`Download ${file.name}`"
                >
                  <Loader2 v-if="isDownloading(file.id)" class="w-3.5 h-3.5 text-blue-600 animate-spin" />
                  <Download v-else class="w-3.5 h-3.5" />
                </button>

                <!-- More Button -->
                <button
                  @click.stop="openContextMenu($event, file)"
                  class="p-1.5 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                  title="File options"
                >
                  <MoreVertical class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <!-- Card Center: Rich Visual Icon with Soft Ambient Glow -->
            <div class="py-2 flex items-center justify-center">
              <div
                class="w-14 h-14 rounded-2xl border flex items-center justify-center shadow-2xs group-hover:scale-105 transition-transform"
                :class="getFileMeta(file.name).iconBgClass"
              >
                <component :is="getFileMeta(file.name).icon" class="w-7 h-7" />
              </div>
            </div>

            <!-- Card Footer: Name, Monospace Size, and Action Strip -->
            <div class="space-y-2">
              <div class="min-w-0">
                <div
                  class="text-xs font-bold text-slate-900 line-clamp-2 group-hover:text-blue-600 transition-colors leading-snug"
                  :title="file.name"
                >
                  {{ file.name }}
                </div>
                <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono mt-1">
                  <span>{{ formatBytes(file.size_bytes) }}</span>
                  <span class="flex items-center space-x-0.5 text-slate-400">
                    <Lock class="w-2.5 h-2.5" />
                    <span>E2EE</span>
                  </span>
                </div>
              </div>

              <!-- Quick Action Strip on Card Hover -->
              <div class="pt-1 border-t border-slate-100 flex items-center justify-between gap-1 opacity-90 group-hover:opacity-100">
                <button
                  @click.stop="handleNodeClick(file)"
                  class="flex-1 py-1 px-2 rounded-lg text-[11px] font-medium text-slate-600 hover:text-blue-600 hover:bg-blue-50 flex items-center justify-center space-x-1 transition-colors"
                >
                  <Eye class="w-3 h-3" />
                  <span>Preview</span>
                </button>
                <button
                  @click.stop="downloadFile(file)"
                  class="flex-1 py-1 px-2 rounded-lg text-[11px] font-semibold text-blue-600 hover:bg-blue-50 flex items-center justify-center space-x-1 transition-colors"
                >
                  <Loader2 v-if="isDownloading(file.id)" class="w-3 h-3 animate-spin" />
                  <Download v-else class="w-3 h-3" />
                  <span>Download</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Files List / Table View -->
        <div v-else class="bg-white rounded-2xl border border-slate-200/90 overflow-hidden divide-y divide-slate-100 shadow-2xs">
          <!-- Table Header -->
          <div class="grid grid-cols-12 px-4 py-2.5 bg-slate-50/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            <div class="col-span-6 sm:col-span-5">Name</div>
            <div class="hidden sm:block sm:col-span-3">Type</div>
            <div class="col-span-3 sm:col-span-2 text-right sm:text-left">Size</div>
            <div class="col-span-3 sm:col-span-2 text-right">Actions</div>
          </div>

          <!-- Table Rows -->
          <div
            v-for="file in files"
            :key="file.id"
            @click="handleNodeClick(file)"
            @contextmenu="openContextMenu($event, file)"
            class="grid grid-cols-12 items-center px-4 py-3 hover:bg-blue-50/40 cursor-pointer transition-colors text-xs select-none group"
          >
            <!-- Name Column -->
            <div class="col-span-6 sm:col-span-5 flex items-center space-x-3 min-w-0 pr-2">
              <div
                class="w-8 h-8 rounded-lg border flex items-center justify-center shrink-0"
                :class="getFileMeta(file.name).iconBgClass"
              >
                <component :is="getFileMeta(file.name).icon" class="w-4 h-4" />
              </div>
              <div class="min-w-0">
                <span class="font-semibold text-slate-900 truncate block group-hover:text-blue-600 transition-colors" :title="file.name">
                  {{ file.name }}
                </span>
                <span class="text-[10px] text-slate-400 sm:hidden">
                  {{ formatBytes(file.size_bytes) }}
                </span>
              </div>
            </div>

            <!-- Type Column -->
            <div class="hidden sm:flex sm:col-span-3 items-center space-x-2">
              <span
                class="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border"
                :class="getFileMeta(file.name).badgeClass"
              >
                {{ getFileMeta(file.name).label }}
              </span>
              <span class="text-slate-500 text-xs truncate">
                {{ getFileMeta(file.name).typeName }}
              </span>
            </div>

            <!-- Size Column -->
            <div class="col-span-3 sm:col-span-2 text-right sm:text-left font-mono text-[11px] text-slate-600">
              {{ formatBytes(file.size_bytes) }}
            </div>

            <!-- Actions Column: Direct Download, Preview, Share, More -->
            <div class="col-span-3 sm:col-span-2 flex items-center justify-end space-x-1">
              <!-- Direct Download Action -->
              <button
                @click.stop="downloadFile(file)"
                class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                :title="`Download ${file.name}`"
              >
                <Loader2 v-if="isDownloading(file.id)" class="w-3.5 h-3.5 text-blue-600 animate-spin" />
                <Download v-else class="w-3.5 h-3.5" />
              </button>

              <!-- Preview Action -->
              <button
                @click.stop="handleNodeClick(file)"
                class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                title="Preview"
              >
                <Eye class="w-3.5 h-3.5" />
              </button>

              <!-- Share Action -->
              <button
                @click.stop="triggerShare(file)"
                class="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                title="Share link"
              >
                <Share2 class="w-3.5 h-3.5" />
              </button>

              <!-- More Action -->
              <button
                @click.stop="openContextMenu($event, file)"
                class="p-1.5 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                title="More actions"
              >
                <MoreVertical class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Context Menu Dropdown -->
    <div
      v-if="contextMenu.visible && contextMenu.node"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      class="fixed z-50 w-52 rounded-2xl p-1.5 shadow-2xl space-y-0.5 text-xs font-medium text-slate-700 border border-slate-200 bg-white"
    >
      <!-- Direct Download Option for Files -->
      <button
        v-if="contextMenu.node.type === 'file'"
        @click="downloadFile(contextMenu.node); closeContextMenu()"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-blue-50 text-blue-700 font-semibold transition-colors"
      >
        <Download class="w-3.5 h-3.5 text-blue-600" />
        <span>Download Decrypted File</span>
      </button>

      <!-- Preview Option for Files -->
      <button
        v-if="contextMenu.node.type === 'file'"
        @click="previewNode = contextMenu.node; isPreviewOpen = true; closeContextMenu()"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
      >
        <Eye class="w-3.5 h-3.5 text-slate-500" />
        <span>Preview & Decrypt</span>
      </button>

      <button
        @click="triggerShare(contextMenu.node)"
        class="w-full flex items-center space-x-2.5 px-3 py-2 rounded-xl hover:bg-slate-100 text-slate-700 hover:text-slate-900 transition-colors"
      >
        <Share2 class="w-3.5 h-3.5 text-slate-500" />
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
        <div class="flex items-center space-x-2.5 text-slate-900">
          <FolderPlus class="w-5 h-5 text-blue-600" />
          <h3 class="text-sm font-bold">Create New Folder</h3>
        </div>
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
        <div class="flex items-center space-x-2.5 text-slate-900">
          <Edit2 class="w-5 h-5 text-blue-600" />
          <h3 class="text-sm font-bold">Rename</h3>
        </div>
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

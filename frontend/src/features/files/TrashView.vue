<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import { useFilesStore, type FileNode } from "../../stores/files";
import { apiRequest } from "../../lib/api";
import { decryptName } from "../../lib/crypto/names";
import {
  Trash2,
  RotateCcw,
  Folder,
  FileText,
  AlertTriangle,
  Loader2,
  ShieldAlert,
} from "lucide-vue-next";

const authStore = useAuthStore();
const filesStore = useFilesStore();

const trashedNodes = ref<FileNode[]>([]);
const isLoading = ref(true);
const actionError = ref("");
const actionSuccess = ref("");
const processingNodeId = ref<string | null>(null);
const isPurgingAll = ref(false);
const showConfirmEmpty = ref(false);

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

onMounted(async () => {
  await fetchTrashedNodes();
});

async function fetchTrashedNodes() {
  if (!authStore.masterKey) return;
  isLoading.value = true;
  actionError.value = "";
  try {
    const res = await apiRequest<{ results: any[] } | any[]>("/api/v1/nodes?trashed=true");
    const items = Array.isArray(res) ? res : res.results || [];
    trashedNodes.value = await Promise.all(
      items.map(async (item: any) => {
        let decrypted = "[Encrypted]";
        if (authStore.masterKey) {
          try {
            decrypted = await decryptName(
              authStore.masterKey,
              item.encrypted_name,
              item.name_nonce
            );
          } catch {
            decrypted = "[Decryption Error]";
          }
        }
        return {
          ...item,
          name: decrypted,
        };
      })
    );
  } catch (err: any) {
    actionError.value = err.message || "Failed to load trashed items.";
  } finally {
    isLoading.value = false;
  }
}

async function handleRestore(node: FileNode) {
  processingNodeId.value = node.id;
  actionError.value = "";
  actionSuccess.value = "";
  try {
    await filesStore.restoreNode(node.id);
    trashedNodes.value = trashedNodes.value.filter((n) => n.id !== node.id);
    actionSuccess.value = `"${node.name}" restored to your vault.`;
    setTimeout(() => (actionSuccess.value = ""), 4000);
  } catch (err: any) {
    actionError.value = err.message || "Failed to restore item.";
  } finally {
    processingNodeId.value = null;
  }
}

async function handlePermanentDelete(node: FileNode) {
  if (!confirm(`Are you sure you want to permanently delete "${node.name}"? This action cannot be undone.`)) {
    return;
  }
  processingNodeId.value = node.id;
  actionError.value = "";
  actionSuccess.value = "";
  try {
    await filesStore.permanentDeleteNode(node.id);
    trashedNodes.value = trashedNodes.value.filter((n) => n.id !== node.id);
    actionSuccess.value = `"${node.name}" permanently deleted.`;
    setTimeout(() => (actionSuccess.value = ""), 4000);
  } catch (err: any) {
    actionError.value = err.message || "Failed to permanently delete item.";
  } finally {
    processingNodeId.value = null;
  }
}

async function handleEmptyTrash() {
  isPurgingAll.value = true;
  actionError.value = "";
  try {
    for (const node of trashedNodes.value) {
      await filesStore.permanentDeleteNode(node.id);
    }
    trashedNodes.value = [];
    showConfirmEmpty.value = false;
    actionSuccess.value = "Trash emptied successfully.";
    setTimeout(() => (actionSuccess.value = ""), 4000);
  } catch (err: any) {
    actionError.value = err.message || "Failed to empty trash.";
  } finally {
    isPurgingAll.value = false;
  }
}
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-xl font-bold text-slate-900 flex items-center space-x-2">
          <Trash2 class="w-5 h-5 text-rose-500" />
          <span>Trash</span>
        </h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Items in trash can be restored to your vault or permanently purged to free up storage quota.
        </p>
      </div>

      <button
        v-if="trashedNodes.length > 0"
        @click="showConfirmEmpty = true"
        class="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold transition-colors shadow-2xs"
      >
        <Trash2 class="w-3.5 h-3.5" />
        <span>Empty Trash</span>
      </button>
    </div>

    <!-- Feedback Alerts -->
    <div v-if="actionSuccess" class="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center space-x-2 animate-fade-in">
      <RotateCcw class="w-4 h-4 text-emerald-600 shrink-0" />
      <span>{{ actionSuccess }}</span>
    </div>

    <div v-if="actionError" class="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2 animate-fade-in">
      <AlertTriangle class="w-4 h-4 text-rose-600 shrink-0" />
      <span>{{ actionError }}</span>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="p-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center space-y-3">
      <Loader2 class="w-6 h-6 text-brand-600 animate-spin" />
      <span>Decrypting trashed items...</span>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="trashedNodes.length === 0"
      class="p-16 text-center rounded-2xl border border-dashed border-slate-200 bg-white shadow-xs space-y-3"
    >
      <div class="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mx-auto">
        <Trash2 class="w-6 h-6" />
      </div>
      <div class="text-sm font-bold text-slate-900">Trash is empty</div>
      <p class="text-xs text-slate-500 max-w-sm mx-auto">
        Files or folders you move to trash will be held here until permanently deleted.
      </p>
    </div>

    <!-- Trashed Items List -->
    <div v-else class="rounded-2xl border border-slate-200 bg-white divide-y divide-slate-100 shadow-xs overflow-hidden">
      <div
        v-for="node in trashedNodes"
        :key="node.id"
        class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors text-xs"
      >
        <div class="flex items-center space-x-3 min-w-0">
          <div
            class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border"
            :class="node.type === 'folder' ? 'bg-amber-50 text-amber-600 border-amber-200' : 'bg-blue-50 text-brand-600 border-blue-200'"
          >
            <Folder v-if="node.type === 'folder'" class="w-5 h-5 fill-amber-500/20" />
            <FileText v-else class="w-5 h-5" />
          </div>

          <div class="min-w-0">
            <div class="font-bold text-slate-900 truncate" :title="node.name">
              {{ node.name }}
            </div>
            <div class="text-[11px] text-slate-500 flex items-center space-x-2 mt-0.5 font-mono">
              <span>{{ node.type === 'folder' ? 'Folder' : formatBytes(node.size_bytes) }}</span>
              <span v-if="node.trashed_at">• Trashed {{ new Date(node.trashed_at).toLocaleDateString() }}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-2 shrink-0 self-end sm:self-center">
          <button
            @click="handleRestore(node)"
            :disabled="processingNodeId === node.id"
            class="px-3 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 flex items-center space-x-1.5 transition-colors font-medium text-xs disabled:opacity-50"
            title="Restore to original folder"
          >
            <RotateCcw class="w-3.5 h-3.5" />
            <span>Restore</span>
          </button>

          <button
            @click="handlePermanentDelete(node)"
            :disabled="processingNodeId === node.id"
            class="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 flex items-center space-x-1.5 transition-colors font-medium text-xs disabled:opacity-50"
            title="Delete permanently"
          >
            <Trash2 class="w-3.5 h-3.5" />
            <span>Delete Permanently</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm Empty Trash Modal -->
    <div v-if="showConfirmEmpty" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div class="bg-white w-full max-w-sm rounded-2xl p-6 border border-slate-200 space-y-4 shadow-xl">
        <div class="flex items-center space-x-2.5 text-rose-600">
          <ShieldAlert class="w-5 h-5" />
          <h3 class="text-sm font-bold text-slate-900">Empty Trash?</h3>
        </div>
        <p class="text-xs text-slate-600">
          All {{ trashedNodes.length }} items will be permanently deleted from the vault and upstream storage. This cannot be undone.
        </p>
        <div class="flex justify-end space-x-2 pt-1">
          <button @click="showConfirmEmpty = false" class="btn-secondary px-3.5 py-1.5 rounded-xl text-xs font-medium">
            Cancel
          </button>
          <button
            @click="handleEmptyTrash"
            :disabled="isPurgingAll"
            class="px-4 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-sm disabled:opacity-50"
          >
            <Loader2 v-if="isPurgingAll" class="w-3.5 h-3.5 animate-spin" />
            <span>Empty Forever</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

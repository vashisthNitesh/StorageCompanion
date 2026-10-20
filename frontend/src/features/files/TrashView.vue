<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { RotateCcw, Trash2, AlertCircle, RefreshCw, Loader2 } from "lucide-vue-next";
import { useAuthStore } from "../../stores/auth";
import { useFilesStore, type FileNode } from "../../stores/files";
import { useToastStore } from "../../stores/toast";
import { formatBytes, formatRelative } from "../../lib/format";
import { kindInfo, kindOf } from "./fileTypes";
import FileName from "./FileName.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";

const authStore = useAuthStore();
const filesStore = useFilesStore();
const toast = useToastStore();

const items = ref<FileNode[]>([]);
const loading = ref(false);
const error = ref("");
const busyId = ref<string | null>(null);
const confirmDelete = ref<FileNode | null>(null);
const confirmEmpty = ref(false);

async function load() {
  if (!authStore.masterKey) return;
  loading.value = true;
  error.value = "";
  try {
    items.value = await filesStore.fetchTrash();
  } catch (err: any) {
    error.value = err.message || "Couldn't load the trash.";
  } finally {
    loading.value = false;
  }
}

async function restore(node: FileNode) {
  busyId.value = node.id;
  try {
    await filesStore.restoreNode(node.id);
    items.value = items.value.filter((n) => n.id !== node.id);
    toast.success(`“${node.name}” restored.`);
  } catch (err: any) {
    toast.error(err.message || "Couldn't restore.");
  } finally {
    busyId.value = null;
  }
}

async function deleteForever(node: FileNode) {
  await filesStore.permanentDeleteNode(node.id);
  items.value = items.value.filter((n) => n.id !== node.id);
}

async function emptyTrash() {
  for (const node of [...items.value]) await deleteForever(node);
  toast.success("Trash emptied.");
}

onMounted(load);
watch(() => authStore.masterKey, (k) => k && load());
</script>

<template>
  <div>
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="page-title">Trash</h1>
        <p class="page-subtitle">Items in the trash don't count towards your storage. Restore them or delete them forever.</p>
      </div>
      <button v-if="items.length" class="btn-danger-ghost self-start" @click="confirmEmpty = true">
        <Trash2 class="h-4 w-4" /> Empty trash
      </button>
    </div>

    <div class="mt-6">
      <div v-if="!authStore.masterKey" class="card card-body flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
        <Loader2 class="h-4 w-4 animate-spin" /> Waiting for your vault to unlock…
      </div>
      <div v-else-if="loading && !items.length" class="card card-body flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
        <Loader2 class="h-4 w-4 animate-spin" /> Loading trash…
      </div>
      <div v-else-if="error" class="card card-body py-12 text-center">
        <AlertCircle class="mx-auto h-8 w-8 text-rose-500" />
        <p class="mt-3 text-sm text-slate-700">{{ error }}</p>
        <button class="btn-secondary mt-4" @click="load"><RefreshCw class="h-4 w-4" /> Try again</button>
      </div>
      <div v-else-if="!items.length" class="card card-body py-16 text-center">
        <Trash2 class="mx-auto h-10 w-10 text-slate-300" />
        <p class="mt-3 font-medium text-slate-900">Trash is empty</p>
        <p class="mt-1 text-sm text-slate-500">Files you delete appear here.</p>
      </div>
      <ul v-else class="card divide-y divide-slate-100">
        <li v-for="node in items" :key="node.id" class="flex items-center gap-3 px-4 py-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" :class="kindInfo(kindOf(node)).tint">
            <component :is="kindInfo(kindOf(node)).icon" class="h-[18px] w-[18px]" />
          </span>
          <div class="min-w-0 flex-1">
            <FileName :name="node.name" :is-folder="node.type === 'folder'" class="text-sm font-medium text-slate-900" />
            <p class="text-xs text-slate-500">
              {{ node.type === "folder" ? "Folder and its contents" : formatBytes(node.size_bytes) }} · deleted {{ formatRelative(node.trashed_at) }}
            </p>
          </div>
          <button class="btn-secondary btn-sm" :disabled="busyId === node.id" @click="restore(node)">
            <Loader2 v-if="busyId === node.id" class="h-4 w-4 animate-spin" />
            <RotateCcw v-else class="h-4 w-4" />
            <span class="hidden sm:inline">Restore</span>
          </button>
          <button class="btn-danger-ghost btn-sm" :aria-label="`Delete ${node.name} forever`" title="Delete forever" @click="confirmDelete = node">
            <Trash2 class="h-4 w-4" />
            <span class="hidden sm:inline">Delete</span>
          </button>
        </li>
      </ul>
    </div>

    <ConfirmDialog
      :open="!!confirmDelete"
      title="Delete forever?"
      :message="`“${confirmDelete?.name}” will be permanently deleted. This can't be undone.`"
      confirm-label="Delete forever"
      danger
      :action="() => deleteForever(confirmDelete!)"
      @close="confirmDelete = null"
    />
    <ConfirmDialog
      :open="confirmEmpty"
      title="Empty trash?"
      :message="`All ${items.length} items in the trash will be permanently deleted. This can't be undone.`"
      confirm-label="Empty trash"
      danger
      :action="emptyTrash"
      @close="confirmEmpty = false"
    />
  </div>
</template>

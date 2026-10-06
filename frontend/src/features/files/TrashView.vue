<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiRequest, apiRequestAllPages } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { decryptName } from "../../lib/crypto/names";
import { Trash2, RotateCcw, Folder, FileText, AlertCircle } from "lucide-vue-next";

interface TrashedItem {
  id: string;
  type: "file" | "folder";
  name: string;
  size_bytes: number;
  trashed_at: string | null;
}

const authStore = useAuthStore();
const items = ref<TrashedItem[]>([]);
const isLoading = ref(true);
const error = ref("");
const message = ref("");
const restoringIds = ref<Set<string>>(new Set());

function formatBytes(bytes: number): string {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${parseFloat((bytes / Math.pow(1024, i)).toFixed(1))} ${units[i]}`;
}

async function load() {
  isLoading.value = true;
  error.value = "";
  try {
    const raw = await apiRequestAllPages<any>("/api/v1/nodes?trashed=true");
    items.value = await Promise.all(
      raw.map(async (n: any) => {
        let name = "[Encrypted]";
        if (authStore.masterKey) {
          try {
            name = await decryptName(authStore.masterKey, n.encrypted_name, n.name_nonce);
          } catch {
            name = "[Unreadable name]";
          }
        }
        return { id: n.id, type: n.type, name, size_bytes: n.size_bytes || 0, trashed_at: n.trashed_at || null };
      })
    );
  } catch (err: any) {
    error.value = err?.message || "Could not load the trash.";
  } finally {
    isLoading.value = false;
  }
}

async function restore(item: TrashedItem) {
  message.value = "";
  error.value = "";
  restoringIds.value.add(item.id);
  try {
    await apiRequest(`/api/v1/nodes/${item.id}/restore`, { method: "POST" });
    items.value = items.value.filter((i) => i.id !== item.id);
    message.value = `Restored "${item.name}".`;
  } catch (err: any) {
    error.value = err?.message || `Could not restore "${item.name}".`;
  } finally {
    restoringIds.value.delete(item.id);
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <div>
      <h1 class="text-xl font-bold text-slate-900">Trash</h1>
      <p class="text-xs text-slate-500">Items you move to Trash stay here until you restore them. They still count toward your storage.</p>
    </div>

    <div v-if="message" class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">{{ message }}</div>
    <div v-if="error" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
      <AlertCircle class="w-4 h-4 shrink-0" />
      <span>{{ error }}</span>
      <button class="ml-auto underline" @click="load">Retry</button>
    </div>

    <div v-if="isLoading" class="text-xs text-slate-500">Loading trash...</div>

    <div v-else-if="items.length === 0 && !error" class="p-12 text-center rounded-2xl border border-dashed border-slate-200 bg-white shadow-xs space-y-3">
      <Trash2 class="w-10 h-10 text-slate-400 mx-auto" />
      <div class="text-sm font-bold text-slate-900">Trash is empty</div>
      <p class="text-xs text-slate-500 max-w-xs mx-auto">Files and folders you delete from My Files appear here and can be restored.</p>
    </div>

    <div v-else class="rounded-2xl border border-slate-200 bg-white divide-y divide-slate-100 shadow-xs">
      <div v-for="item in items" :key="item.id" class="p-4 flex items-center justify-between gap-3 text-xs">
        <div class="flex items-center space-x-3 min-w-0">
          <div class="w-9 h-9 rounded-xl bg-slate-50 flex items-center justify-center border border-slate-200 shrink-0">
            <Folder v-if="item.type === 'folder'" class="w-4 h-4 text-amber-500" />
            <FileText v-else class="w-4 h-4 text-slate-500" />
          </div>
          <div class="min-w-0">
            <div class="font-bold text-slate-900 truncate">{{ item.name }}</div>
            <div class="text-[11px] text-slate-500">
              {{ item.type === 'folder' ? 'Folder' : formatBytes(item.size_bytes) }}
              <span v-if="item.trashed_at"> · deleted {{ new Date(item.trashed_at).toLocaleString() }}</span>
            </div>
          </div>
        </div>
        <button
          @click="restore(item)"
          :disabled="restoringIds.has(item.id)"
          class="px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 flex items-center space-x-1.5 transition-colors font-medium text-xs shrink-0 disabled:opacity-60"
        >
          <RotateCcw class="w-3.5 h-3.5" />
          <span>{{ restoringIds.has(item.id) ? 'Restoring...' : 'Restore' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

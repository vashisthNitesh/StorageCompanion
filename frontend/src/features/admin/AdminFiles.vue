<script setup lang="ts">
import { ref, watch, onMounted, computed } from "vue";
import { Search, Folder, File, Loader2, ChevronLeft, ChevronRight } from "lucide-vue-next";
import { apiRequest } from "../../lib/api";
import { formatBytes, formatDate } from "../../lib/format";

interface AdminNode {
  id: string;
  type: "file" | "folder";
  size_bytes: number;
  owner_email: string;
  created_at: string;
  is_trashed: boolean;
  upstream: string;
  versions_count: number;
}

const rows = ref<AdminNode[]>([]);
const total = ref(0);
const totalSize = ref(0);
const page = ref(1);
const pageSize = 25;
const search = ref("");
const type = ref("");
const status = ref("");
const loading = ref(false);
const error = ref("");
const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams({ search: search.value, type: type.value, status: status.value, page: String(page.value), page_size: String(pageSize) });
    const data = await apiRequest<{ total_count: number; total_size_bytes: number; results: AdminNode[] }>(`/api/v1/admin/files/?${params}`);
    rows.value = data.results;
    total.value = data.total_count;
    totalSize.value = data.total_size_bytes;
  } catch (err: any) {
    error.value = err.message || "Couldn't load files.";
  } finally {
    loading.value = false;
  }
}

let timer: ReturnType<typeof setTimeout> | undefined;
watch([search, type, status], () => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    page.value = 1;
    void load();
  }, 300);
});
watch(page, load);
onMounted(load);
</script>

<template>
  <div>
    <p class="mb-4 text-sm text-slate-600">
      File names are end-to-end encrypted, so only owners, sizes and dates are visible here.
    </p>
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
      <div class="relative flex-1">
        <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input v-model="search" type="search" class="input pl-9" placeholder="Search by owner email or item ID" aria-label="Search files" />
      </div>
      <div class="flex gap-2">
        <select v-model="type" class="input h-10 w-auto" aria-label="Type">
          <option value="">Files and folders</option>
          <option value="file">Files</option>
          <option value="folder">Folders</option>
        </select>
        <select v-model="status" class="input h-10 w-auto" aria-label="Status">
          <option value="">Any status</option>
          <option value="active">Active</option>
          <option value="trashed">In trash</option>
        </select>
      </div>
    </div>

    <p class="mt-4 text-sm text-slate-500">{{ total }} items · {{ formatBytes(totalSize) }}</p>
    <div v-if="error" class="alert-error mt-2">{{ error }} <button class="ml-2 underline" @click="load">Retry</button></div>

    <div class="mt-2 card overflow-x-auto">
      <table class="w-full min-w-[640px] text-left text-sm">
        <thead class="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th class="px-4 py-2.5 font-medium">Item</th>
            <th class="px-4 py-2.5 font-medium">Owner</th>
            <th class="px-4 py-2.5 font-medium">Size</th>
            <th class="px-4 py-2.5 font-medium">Uploaded</th>
            <th class="px-4 py-2.5 font-medium">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-if="loading && !rows.length"><td colspan="5" class="px-4 py-10 text-center"><Loader2 class="mx-auto h-5 w-5 animate-spin text-slate-400" /></td></tr>
          <tr v-else-if="!rows.length"><td colspan="5" class="px-4 py-10 text-center text-slate-500">No items match.</td></tr>
          <tr v-for="n in rows" :key="n.id" :class="{ 'opacity-60': loading }">
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <Folder v-if="n.type === 'folder'" class="h-4 w-4 text-amber-500" />
                <File v-else class="h-4 w-4 text-slate-400" />
                <span class="font-mono text-xs text-slate-600">{{ n.id.slice(0, 8) }}</span>
                <span v-if="n.versions_count > 1" class="badge-gray">{{ n.versions_count }} versions</span>
              </div>
            </td>
            <td class="px-4 py-3 text-slate-700">{{ n.owner_email }}</td>
            <td class="px-4 py-3 text-slate-700">{{ n.type === "folder" ? "—" : formatBytes(n.size_bytes) }}</td>
            <td class="px-4 py-3 text-slate-700">{{ formatDate(n.created_at) }}</td>
            <td class="px-4 py-3">
              <span v-if="n.is_trashed" class="badge-amber">In trash</span>
              <span v-else-if="n.type === 'file' && n.upstream !== 'SpaceByte'" class="badge-red">Missing in storage</span>
              <span v-else class="badge-green">Stored</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="pages > 1" class="mt-4 flex items-center justify-end gap-2 text-sm text-slate-600">
      <button class="icon-btn" :disabled="page <= 1" aria-label="Previous page" @click="page--"><ChevronLeft class="h-4 w-4" /></button>
      <span>Page {{ page }} of {{ pages }}</span>
      <button class="icon-btn" :disabled="page >= pages" aria-label="Next page" @click="page++"><ChevronRight class="h-4 w-4" /></button>
    </div>
  </div>
</template>

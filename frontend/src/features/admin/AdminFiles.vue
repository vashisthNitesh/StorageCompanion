<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { Folder, File, CloudOff, SearchX } from "lucide-vue-next";
import { apiRequest } from "../../lib/api";
import { formatBytes, formatDate } from "../../lib/format";
import { normalizeApiError } from "../../lib/errors";
import UiSearchInput from "../../components/ui/UiSearchInput.vue";
import UiSelect from "../../components/ui/UiSelect.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiEmptyState from "../../components/ui/UiEmptyState.vue";
import UiPagination from "../../components/ui/UiPagination.vue";

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

const TYPE_OPTIONS = [
  { value: "", label: "Files and folders" },
  { value: "file", label: "Files" },
  { value: "folder", label: "Folders" },
];
const STATUS_OPTIONS = [
  { value: "", label: "Any status" },
  { value: "active", label: "Active" },
  { value: "trashed", label: "In trash" },
];

const rows = ref<AdminNode[]>([]);
const total = ref(0);
const totalSize = ref(0);
const page = ref(1);
const pageSize = 25;
const search = ref("");
const type = ref("");
const status = ref("");
const loading = ref(false);
const loaded = ref(false);
const error = ref<unknown>(null);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const params = new URLSearchParams({ search: search.value, type: type.value, status: status.value, page: String(page.value), page_size: String(pageSize) });
    const data = await apiRequest<{ total_count: number; total_size_bytes: number; results: AdminNode[] }>(`/api/v1/admin/files/?${params}`);
    rows.value = data.results;
    total.value = data.total_count;
    totalSize.value = data.total_size_bytes;
    loaded.value = true;
  } catch (err) {
    error.value = err;
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
    <p class="mb-4 text-base text-fg-muted">File names are end-to-end encrypted, so only owners, sizes and dates are visible here.</p>
    <div class="flex flex-col gap-2 lg:flex-row lg:items-center">
      <UiSearchInput v-model="search" class="flex-1" placeholder="Search by owner email or item ID" aria-label="Search files" />
      <div class="flex gap-2">
        <UiSelect v-model="type" :options="TYPE_OPTIONS" :block="false" aria-label="Type" />
        <UiSelect v-model="status" :options="STATUS_OPTIONS" :block="false" aria-label="Status" />
      </div>
    </div>

    <p class="tabular mt-4 text-sm text-fg-muted" aria-live="polite">
      <template v-if="loaded">{{ total.toLocaleString() }} {{ total === 1 ? "item" : "items" }} · {{ formatBytes(totalSize) }}</template>&nbsp;
    </p>

    <div v-if="error && !rows.length" class="mt-2 rounded-lg border border-line bg-surface">
      <UiEmptyState :icon="CloudOff" tone="danger" title="Couldn't load files" :description="normalizeApiError(error).message">
        <UiButton @click="load">Try again</UiButton>
      </UiEmptyState>
    </div>
    <div v-else class="relative mt-2 overflow-x-auto rounded-lg border border-line bg-surface">
      <table class="w-full min-w-[640px] text-left text-base">
        <thead class="border-b border-line bg-surface-sunken text-sm text-fg-muted">
          <tr>
            <th scope="col" class="px-4 py-2.5 font-medium">Item</th>
            <th scope="col" class="px-4 py-2.5 font-medium">Owner</th>
            <th scope="col" class="px-4 py-2.5 text-right font-medium">Size</th>
            <th scope="col" class="px-4 py-2.5 font-medium">Uploaded</th>
            <th scope="col" class="px-4 py-2.5 font-medium">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line" :aria-busy="loading">
          <template v-if="loading && !loaded">
            <tr v-for="i in 6" :key="i">
              <td v-for="j in 5" :key="j" class="px-4 py-3.5"><UiSkeleton class="h-3.5" :class="j === 2 ? 'w-40' : 'w-20'" /></td>
            </tr>
          </template>
          <tr v-else-if="!rows.length">
            <td colspan="5"><UiEmptyState :icon="SearchX" tone="neutral" title="No items match" description="Try a different search or filter." /></td>
          </tr>
          <tr v-for="n in rows" :key="n.id" class="transition-opacity" :class="{ 'opacity-60': loading }">
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <Folder v-if="n.type === 'folder'" :size="16" class="text-warning" aria-label="Folder" />
                <File v-else :size="16" class="text-fg-subtle" aria-label="File" />
                <span class="font-mono text-sm text-fg-muted">{{ n.id.slice(0, 8) }}</span>
                <UiBadge v-if="n.versions_count > 1">{{ n.versions_count }} versions</UiBadge>
              </div>
            </td>
            <td class="px-4 py-3 text-fg">{{ n.owner_email }}</td>
            <td class="tabular px-4 py-3 text-right text-fg-muted">{{ n.type === "folder" ? "—" : formatBytes(n.size_bytes) }}</td>
            <td class="tabular px-4 py-3 text-fg-muted">{{ formatDate(n.created_at) }}</td>
            <td class="px-4 py-3">
              <UiBadge v-if="n.is_trashed" tone="warning">In trash</UiBadge>
              <UiBadge v-else-if="n.type === 'file' && n.upstream !== 'SpaceByte'" tone="danger">Missing in storage</UiBadge>
              <UiBadge v-else tone="success">Stored</UiBadge>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <UiPagination v-model="page" class="mt-4" :total="total" :page-size="pageSize" label="Files pages" />
  </div>
</template>

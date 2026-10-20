<script setup lang="ts">
import { ref, watch } from "vue";
import { Download, Loader2 } from "lucide-vue-next";
import BaseModal from "../../components/BaseModal.vue";
import { apiRequest } from "../../lib/api";
import { formatBytes, formatDateTime } from "../../lib/format";
import type { FileNode } from "../../stores/files";
import { useFileDownload } from "./useFileDownload";

const props = defineProps<{ open: boolean; node: FileNode | null }>();
const emit = defineEmits<{ close: [] }>();
const { downloadFile, isDownloading, progressOf } = useFileDownload();

const versions = ref<{ id: string; version_no: number; size_bytes: number; created_at: string }[]>([]);
const loading = ref(false);
const error = ref("");

watch(
  () => props.open,
  async (open) => {
    if (!open || !props.node) return;
    loading.value = true;
    error.value = "";
    try {
      versions.value = await apiRequest(`/api/v1/nodes/${props.node.id}/versions`);
    } catch (err: any) {
      error.value = err.message || "Couldn't load versions.";
    } finally {
      loading.value = false;
    }
  }
);
</script>

<template>
  <BaseModal :open="open" title="Version history" @close="emit('close')">
    <p class="mb-3 truncate text-sm text-slate-600" :title="node?.name">{{ node?.name }}</p>
    <div v-if="loading" class="flex items-center justify-center gap-2 py-8 text-sm text-slate-500">
      <Loader2 class="h-4 w-4 animate-spin" /> Loading…
    </div>
    <div v-else-if="error" class="alert-error">{{ error }}</div>
    <ul v-else class="divide-y divide-slate-100 rounded-lg border border-slate-200">
      <li v-for="(v, i) in versions" :key="v.id" class="flex items-center justify-between gap-3 px-4 py-3">
        <div class="min-w-0">
          <p class="text-sm font-medium text-slate-900">
            Version {{ v.version_no }} <span v-if="i === 0" class="badge-blue ml-1">Current</span>
          </p>
          <p class="text-xs text-slate-500">{{ formatBytes(v.size_bytes) }} · {{ formatDateTime(v.created_at) }}</p>
        </div>
        <button class="btn-secondary btn-sm" :disabled="!node || isDownloading(node, v.version_no)" @click="node && downloadFile(node, v.version_no)">
          <Loader2 v-if="node && isDownloading(node, v.version_no)" class="h-4 w-4 animate-spin" />
          <Download v-else class="h-4 w-4" />
          {{ node && isDownloading(node, v.version_no) ? `${progressOf(node, v.version_no)}%` : "Download" }}
        </button>
      </li>
    </ul>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Download, LockKeyhole, Share2 } from "lucide-vue-next";
import UiDrawer from "../../components/ui/UiDrawer.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { apiRequest } from "../../lib/api";
import { normalizeApiError } from "../../lib/errors";
import { formatBytes, formatDateTime } from "../../lib/format";
import { useFilesStore, type FileNode } from "../../stores/files";
import { kindInfo, kindOf } from "./fileTypes";
import { useFileDownload } from "./useFileDownload";
import FileThumb from "../preview/FileThumb.vue";

const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{ node: FileNode | null }>();
const emit = defineEmits<{ share: [node: FileNode] }>();
const files = useFilesStore();
const { downloadFile, isDownloading, progressOf } = useFileDownload();

const versions = ref<{ id: string; version_no: number; size_bytes: number; created_at: string }[]>([]);
const loadingVersions = ref(false);
const versionsError = ref("");
const location = computed(() => files.breadcrumbs.map((c) => c.name).join(" / "));

watch(
  () => [open.value, props.node?.id],
  async () => {
    versions.value = [];
    versionsError.value = "";
    if (!open.value || props.node?.type !== "file") return;
    loadingVersions.value = true;
    try {
      versions.value = await apiRequest(`/api/v1/nodes/${props.node.id}/versions`);
    } catch (err) {
      versionsError.value = normalizeApiError(err).message;
    } finally {
      loadingVersions.value = false;
    }
  }
);
</script>

<template>
  <UiDrawer v-model:open="open" :title="node?.name ?? ''" :description="node ? kindInfo(kindOf(node)).label : ''">
    <div v-if="node" class="space-y-6">
      <div class="aspect-[16/9] overflow-hidden rounded-lg bg-canvas-subtle">
        <FileThumb :node="node" variant="card" />
      </div>

      <div class="flex items-start gap-2.5 rounded-lg border border-success/25 bg-success-soft p-3 text-sm text-success">
        <LockKeyhole :size="16" :stroke-width="2" class="mt-0.5 shrink-0" aria-hidden="true" />
        <span><strong class="font-semibold">Encrypted on your device.</strong> Only you can open this {{ node.type }}.</span>
      </div>

      <dl class="tabular grid grid-cols-[110px_1fr] gap-x-4 gap-y-2.5 text-base">
        <dt class="text-fg-subtle">Type</dt><dd class="text-fg">{{ kindInfo(kindOf(node)).label }}</dd>
        <template v-if="node.type === 'file'"><dt class="text-fg-subtle">Size</dt><dd class="text-fg">{{ formatBytes(node.size_bytes) }}</dd></template>
        <dt class="text-fg-subtle">Location</dt><dd class="break-words text-fg">{{ location }}</dd>
        <dt class="text-fg-subtle">Created</dt><dd class="text-fg">{{ formatDateTime(node.created_at) }}</dd>
        <dt class="text-fg-subtle">Modified</dt><dd class="text-fg">{{ formatDateTime(node.updated_at) }}</dd>
      </dl>

      <section v-if="node.type === 'file'">
        <h3 class="text-base font-semibold text-fg">Version history</h3>
        <div v-if="loadingVersions" class="mt-3 space-y-2" aria-busy="true">
          <UiSkeleton v-for="i in 2" :key="i" class="h-12" />
        </div>
        <UiAlert v-else-if="versionsError" class="mt-3">{{ versionsError }}</UiAlert>
        <ul v-else class="mt-3 divide-y divide-line rounded-lg border border-line">
          <li v-for="(v, i) in versions" :key="v.id" class="flex items-center justify-between gap-3 px-3 py-2.5">
            <div class="min-w-0">
              <p class="flex items-center gap-2 text-base text-fg">Version {{ v.version_no }} <UiBadge v-if="i === 0" tone="primary">Current</UiBadge></p>
              <p class="tabular text-xs text-fg-subtle">{{ formatBytes(v.size_bytes) }} · {{ formatDateTime(v.created_at) }}</p>
            </div>
            <UiButton
              variant="ghost"
              size="sm"
              icon-only
              :icon="Download"
              :loading="isDownloading(node, v.version_no)"
              :aria-label="isDownloading(node, v.version_no) ? `Downloading ${progressOf(node, v.version_no)}%` : `Download version ${v.version_no}`"
              @click="downloadFile(node, v.version_no)"
            />
          </li>
        </ul>
      </section>
    </div>
    <template v-if="node?.type === 'file'" #footer>
      <div class="grid grid-cols-2 gap-2">
        <UiButton :icon="Share2" @click="emit('share', node)">Share</UiButton>
        <UiButton variant="primary" :icon="Download" :loading="isDownloading(node)" @click="downloadFile(node)">Download</UiButton>
      </div>
    </template>
  </UiDrawer>
</template>

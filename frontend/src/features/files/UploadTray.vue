<script setup lang="ts">
import { ref, computed } from "vue";
import { ChevronDown, ChevronUp, X, Pause, Play, RotateCw, CheckCircle2, AlertCircle, Loader2 } from "lucide-vue-next";
import { useUploadStore } from "../../stores/upload";
import { formatBytes } from "../../lib/format";

const uploadStore = useUploadStore();
const collapsed = ref(false);

const visible = computed(() => uploadStore.uploads.length > 0);
const heading = computed(() => {
  const active = uploadStore.activeCount;
  const failed = uploadStore.uploads.filter((u) => u.status === "error").length;
  if (active) return `Uploading ${active} ${active === 1 ? "file" : "files"} · ${uploadStore.totalProgress}%`;
  if (failed) return `${failed} upload${failed === 1 ? "" : "s"} need attention`;
  return "Uploads complete";
});

const statusText: Record<string, string> = {
  queued: "Waiting…",
  encrypting: "Encrypting…",
  completing: "Finishing…",
  completed: "Uploaded",
  paused: "Paused",
};
</script>

<template>
  <div
    v-if="visible"
    class="fixed bottom-0 right-0 z-40 w-full sm:bottom-4 sm:right-4 sm:w-96"
    role="region"
    aria-label="Uploads"
  >
    <div class="overflow-hidden border border-slate-200 bg-white shadow-pop sm:rounded-xl">
      <div class="flex items-center gap-2 bg-slate-900 px-4 py-3 text-white">
        <Loader2 v-if="uploadStore.activeCount" class="h-4 w-4 animate-spin" />
        <p class="flex-1 text-sm font-medium">{{ heading }}</p>
        <button class="rounded p-1 hover:bg-white/10" :aria-label="collapsed ? 'Expand uploads' : 'Collapse uploads'" @click="collapsed = !collapsed">
          <ChevronUp v-if="collapsed" class="h-4 w-4" />
          <ChevronDown v-else class="h-4 w-4" />
        </button>
        <button
          v-if="!uploadStore.activeCount"
          class="rounded p-1 hover:bg-white/10"
          aria-label="Close uploads"
          @click="uploadStore.clearFinished()"
        >
          <X class="h-4 w-4" />
        </button>
      </div>
      <ul v-if="!collapsed" class="max-h-80 divide-y divide-slate-100 overflow-y-auto">
        <li v-for="u in uploadStore.uploads" :key="u.id" class="px-4 py-3">
          <div class="flex items-start gap-3">
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-slate-900" :title="u.name">{{ u.name }}</p>
              <p class="mt-0.5 text-xs" :class="u.status === 'error' ? 'text-rose-600' : 'text-slate-500'">
                <template v-if="u.status === 'error'">{{ u.errorMessage }}</template>
                <template v-else-if="u.status === 'uploading'">
                  {{ u.progress }}% of {{ formatBytes(u.size) }}<template v-if="u.speedMBs"> · {{ u.speedMBs }} MB/s</template>
                  <template v-if="u.errorMessage"> · {{ u.errorMessage }}</template>
                </template>
                <template v-else>{{ statusText[u.status] }} · {{ formatBytes(u.size) }}</template>
              </p>
            </div>
            <CheckCircle2 v-if="u.status === 'completed'" class="h-5 w-5 shrink-0 text-emerald-500" />
            <template v-else>
              <AlertCircle v-if="u.status === 'error'" class="h-5 w-5 shrink-0 text-rose-500" />
              <button v-if="u.status === 'uploading' || u.status === 'queued'" class="icon-btn h-7 w-7" title="Pause" @click="uploadStore.pauseUpload(u.id)">
                <Pause class="h-4 w-4" />
              </button>
              <button v-if="u.status === 'paused'" class="icon-btn h-7 w-7" title="Resume" @click="uploadStore.retryUpload(u.id)">
                <Play class="h-4 w-4" />
              </button>
              <button v-if="u.status === 'error'" class="icon-btn h-7 w-7" title="Retry" @click="uploadStore.retryUpload(u.id)">
                <RotateCw class="h-4 w-4" />
              </button>
              <button class="icon-btn h-7 w-7" title="Cancel upload" @click="uploadStore.cancelUpload(u.id)">
                <X class="h-4 w-4" />
              </button>
            </template>
          </div>
          <div v-if="u.status !== 'completed'" class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              class="h-full rounded-full transition-all"
              :class="u.status === 'error' ? 'bg-rose-500' : u.status === 'paused' ? 'bg-slate-400' : 'bg-brand-600'"
              :style="{ width: `${u.progress}%` }"
            ></div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

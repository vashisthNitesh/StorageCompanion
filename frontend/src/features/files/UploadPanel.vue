<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { ChevronDown, ChevronUp, X, Pause, Play, RotateCw, CheckCircle2, AlertCircle, Folder, ChevronRight } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiProgress from "../../components/ui/UiProgress.vue";
import UiProgressCircle from "../../components/ui/UiProgressCircle.vue";
import { useUploadStore, STAGE_LABEL, type ActiveUpload } from "../../stores/upload";
import { formatBytes } from "../../lib/format";
import { kindInfo, kindOf } from "./fileTypes";

const store = useUploadStore();
const collapsed = ref(false);
const openGroups = ref<Set<string>>(new Set());

function eta(seconds: number | null): string {
  if (seconds == null || !isFinite(seconds)) return "";
  if (seconds < 60) return "less than a minute left";
  const m = Math.round(seconds / 60);
  if (m < 60) return `about ${m} min left`;
  return `about ${Math.round(m / 60)} h ${m % 60} min left`;
}
function speed(mbs: number) {
  return mbs >= 1 ? `${mbs.toFixed(1)} MB/s` : `${Math.round(mbs * 1024)} KB/s`;
}

const failed = computed(() => store.uploads.filter((u) => u.status === "error").length);
const done = computed(() => store.uploads.filter((u) => u.status === "completed").length);
const heading = computed(() => {
  if (store.activeCount) return `Uploading ${store.activeCount} ${store.activeCount === 1 ? "file" : "files"}`;
  if (failed.value) return `${failed.value} ${failed.value === 1 ? "upload" : "uploads"} failed`;
  return `${done.value} ${done.value === 1 ? "upload" : "uploads"} complete`;
});

// Rows: loose files, and folder uploads grouped under their top-level folder.
type Row = { kind: "file"; item: ActiveUpload } | { kind: "group"; name: string; items: ActiveUpload[] };
const rows = computed<Row[]>(() => {
  const out: Row[] = [];
  const groups = new Map<string, ActiveUpload[]>();
  for (const u of store.uploads) {
    if (!u.group) out.push({ kind: "file", item: u });
    else {
      const key = `${u.batchId}:${u.group}`;
      if (!groups.has(key)) {
        groups.set(key, []);
        out.push({ kind: "group", name: key, items: groups.get(key)! });
      }
      groups.get(key)!.push(u);
    }
  }
  return out;
});
function groupProgress(items: ActiveUpload[]) {
  const total = items.reduce((s, u) => s + u.size, 0) || 1;
  return Math.round(items.reduce((s, u) => s + (u.size * (u.status === "completed" ? 100 : u.progress)) / 100, 0) / total * 100);
}
function toggleGroup(key: string) {
  const next = new Set(openGroups.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  openGroups.value = next;
}

// Report our height so toasts stack above the panel instead of covering it.
const panelEl = ref<HTMLElement | null>(null);
let observer: ResizeObserver | null = null;
watch(panelEl, (el) => {
  observer?.disconnect();
  if (!el) {
    store.panelHeight = 0;
    return;
  }
  observer = new ResizeObserver(() => (store.panelHeight = el.offsetHeight));
  observer.observe(el);
});
onUnmounted(() => observer?.disconnect());

// Screen-reader summary, updated in steps so it doesn't chatter.
const announcement = ref("");
watch(
  () => [Math.floor(store.totalProgress / 10), store.activeCount, failed.value],
  () => {
    announcement.value = store.activeCount ? `Uploads ${store.totalProgress}% complete` : heading.value;
  }
);
</script>

<template>
  <Transition enter-active-class="animate-slide-up" leave-active-class="animate-fade-out">
    <section
      v-if="store.isTrayOpen && store.uploads.length"
      ref="panelEl"
      class="fixed inset-x-0 bottom-0 z-40 sm:inset-x-auto sm:bottom-5 sm:right-5 sm:w-[400px]"
      aria-label="Uploads"
    >
      <p class="sr-only" aria-live="polite">{{ announcement }}</p>
      <div class="overflow-hidden border border-line bg-surface-raised shadow-xl sm:rounded-xl">
        <header class="flex items-center gap-3 border-b border-line px-4 py-3">
          <span v-if="store.activeCount" class="text-primary"><UiProgressCircle :value="store.totalProgress" :size="20" label="Overall upload progress" /></span>
          <AlertCircle v-else-if="failed" :size="20" class="text-danger" aria-hidden="true" />
          <CheckCircle2 v-else :size="20" class="text-success" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <h2 class="text-base font-semibold text-fg">{{ heading }}</h2>
            <p v-if="store.activeCount" class="tabular text-xs text-fg-subtle">{{ store.totalProgress }}%<template v-if="store.totalEta != null"> · {{ eta(store.totalEta) }}</template></p>
          </div>
          <UiButton variant="ghost" size="sm" icon-only :icon="collapsed ? ChevronUp : ChevronDown" :aria-label="collapsed ? 'Expand uploads' : 'Collapse uploads'" :aria-expanded="!collapsed" @click="collapsed = !collapsed" />
          <UiButton v-if="!store.activeCount" variant="ghost" size="sm" icon-only :icon="X" aria-label="Close uploads" @click="store.clearFinished()" />
        </header>

        <ul v-if="!collapsed" class="max-h-[50vh] divide-y divide-line overflow-y-auto scrollbar-thin sm:max-h-80">
          <template v-for="row in rows" :key="row.kind === 'file' ? row.item.id : row.name">
            <!-- Folder upload group -->
            <li v-if="row.kind === 'group'" class="px-4 py-3">
              <button class="flex w-full items-center gap-3 text-left" :aria-expanded="openGroups.has(row.name)" @click="toggleGroup(row.name)">
                <ChevronRight :size="14" class="shrink-0 text-fg-subtle transition-transform" :class="{ 'rotate-90': openGroups.has(row.name) }" aria-hidden="true" />
                <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-amber-500/10 text-amber-500"><Folder :size="16" aria-hidden="true" /></span>
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-base text-fg">{{ row.items[0].group }}</span>
                  <span class="tabular block text-xs text-fg-subtle">
                    {{ row.items.filter((u) => u.status === "completed").length }} of {{ row.items.length }} files
                    <template v-if="row.items.some((u) => u.status === 'error')"> · {{ row.items.filter((u) => u.status === "error").length }} failed</template>
                  </span>
                </span>
              </button>
              <UiProgress class="mt-2" size="sm" :value="groupProgress(row.items)" :tone="row.items.some((u) => u.status === 'error') ? 'danger' : 'primary'" :label="`${row.items[0].group} progress`" />
              <ul v-if="openGroups.has(row.name)" class="mt-2 space-y-1 border-l border-line pl-4">
                <li v-for="u in row.items" :key="u.id" class="flex items-center justify-between gap-2 text-sm">
                  <span class="truncate text-fg-muted">{{ u.name }}</span>
                  <span class="tabular shrink-0" :class="u.status === 'error' ? 'text-danger' : 'text-fg-subtle'">{{ u.status === "uploading" ? `${u.progress}%` : STAGE_LABEL[u.status] }}</span>
                </li>
              </ul>
            </li>

            <!-- Single file -->
            <li v-else class="px-4 py-3">
              <div class="flex items-center gap-3">
                <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded" :class="kindInfo(kindOf({ type: 'file', name: row.item.name })).tint">
                  <component :is="kindInfo(kindOf({ type: 'file', name: row.item.name })).icon" :size="16" aria-hidden="true" />
                </span>
                <div class="min-w-0 flex-1">
                  <p class="truncate text-base text-fg">{{ row.item.name }}</p>
                  <p class="tabular truncate text-xs" :class="row.item.status === 'error' ? 'text-danger' : 'text-fg-subtle'">
                    <template v-if="row.item.status === 'error'">{{ row.item.errorMessage }}</template>
                    <template v-else-if="row.item.status === 'uploading'">
                      {{ row.item.notice ?? `${row.item.progress}% of ${formatBytes(row.item.size)}` }}<template v-if="!row.item.notice && row.item.speedMBs"> · {{ speed(row.item.speedMBs) }}</template><template v-if="!row.item.notice && row.item.etaSeconds != null"> · {{ eta(row.item.etaSeconds) }}</template>
                    </template>
                    <template v-else>{{ STAGE_LABEL[row.item.status] }} · {{ formatBytes(row.item.size) }}</template>
                  </p>
                </div>
                <CheckCircle2 v-if="row.item.status === 'completed'" :size="18" class="shrink-0 text-success" aria-label="Done" />
                <div v-else class="flex shrink-0 items-center">
                  <UiButton v-if="row.item.status === 'uploading' || row.item.status === 'queued'" variant="ghost" size="sm" icon-only :icon="Pause" :aria-label="`Pause ${row.item.name}`" @click="store.pauseUpload(row.item.id)" />
                  <UiButton v-else-if="row.item.status === 'paused'" variant="ghost" size="sm" icon-only :icon="Play" :aria-label="`Resume ${row.item.name}`" @click="store.retryUpload(row.item.id)" />
                  <UiButton v-else-if="row.item.status === 'error'" variant="ghost" size="sm" icon-only :icon="RotateCw" :aria-label="`Retry ${row.item.name}`" @click="store.retryUpload(row.item.id)" />
                  <UiButton variant="ghost" size="sm" icon-only :icon="X" :aria-label="`Cancel ${row.item.name}`" @click="store.cancelUpload(row.item.id)" />
                </div>
              </div>
              <UiProgress
                v-if="row.item.status !== 'completed'"
                class="mt-2"
                size="sm"
                :value="row.item.status === 'encrypting' || row.item.status === 'completing' ? null : row.item.progress"
                :tone="row.item.status === 'error' ? 'danger' : row.item.status === 'paused' ? 'neutral' : 'primary'"
                :label="`${row.item.name} upload progress`"
              />
            </li>
          </template>
        </ul>

        <footer v-if="!collapsed && failed" class="flex justify-end gap-2 border-t border-line px-4 py-2.5">
          <UiButton size="sm" :icon="RotateCw" @click="store.retryFailed()">Retry failed</UiButton>
        </footer>
      </div>
    </section>
  </Transition>
</template>

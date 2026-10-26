<script setup lang="ts">
import { computed, ref, shallowRef, watch } from "vue";
import { DialogRoot, DialogPortal, DialogContent, DialogTitle, DialogDescription } from "reka-ui";
import { ChevronLeft, ChevronRight, Download, X, Info, Share2 } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiProgress from "../../components/ui/UiProgress.vue";
import { useAuthStore } from "../../stores/auth";
import type { FileNode } from "../../stores/files";
import { normalizeApiError } from "../../lib/errors";
import { formatBytes } from "../../lib/format";
import { DecryptError, openEncryptedFile, type EncryptedFile } from "../../lib/crypto/encryptedFile";
import { kindInfo, kindOf } from "../files/fileTypes";
import { useFileDownload } from "../files/useFileDownload";
import { likelyUnsupported, previewKindOf, extensionOf } from "./previewTypes";
import ImageView from "./views/ImageView.vue";
import MediaView from "./views/MediaView.vue";
import PdfView from "./views/PdfView.vue";
import DocxView from "./views/DocxView.vue";
import SheetView from "./views/SheetView.vue";
import TextView from "./views/TextView.vue";
import PreviewFallback from "./views/PreviewFallback.vue";
import type { ViewProblem } from "./views/types";

// Full-screen viewer for the files in the current listing, with previous / next.
const open = defineModel<boolean>("open", { default: false });
const index = defineModel<number>("index", { default: 0 });
const props = defineProps<{ items: FileNode[] }>();
const emit = defineEmits<{ details: [node: FileNode]; share: [node: FileNode] }>();

const authStore = useAuthStore();
const { downloadFile, isDownloading, progressOf } = useFileDownload();

const node = computed<FileNode | null>(() => props.items[index.value] ?? null);
const kind = computed(() => (node.value ? previewKindOf(node.value) : null));
const file = shallowRef<EncryptedFile | null>(null);
const problem = ref<ViewProblem | null>(null);
/** Download-and-decrypt progress for views that need the whole file (0–1), or null. */
const progress = ref<number | null>(null);

let seq = 0;
watch(
  [open, node],
  async () => {
    const mine = ++seq;
    file.value = null;
    problem.value = null;
    progress.value = null;
    const n = node.value;
    if (!open.value || !n) return;
    if (!kind.value) return void (problem.value = { kind: "unsupported" });
    if (likelyUnsupported(kind.value, n.name)) return void (problem.value = { kind: "unsupported" });
    if (!authStore.masterKey) return void (problem.value = { kind: "locked" });
    try {
      const f = await openEncryptedFile(n, authStore.masterKey, "preview");
      if (mine === seq) file.value = f;
    } catch (err) {
      if (mine !== seq) return;
      problem.value = err instanceof DecryptError ? { kind: "damaged" } : { kind: "failed", message: normalizeApiError(err).message };
    }
  },
  { immediate: true }
);

function onProblem(p: ViewProblem) {
  problem.value = p;
  progress.value = null;
}

const canPrev = computed(() => index.value > 0);
const canNext = computed(() => index.value < props.items.length - 1);
const go = (delta: number) => {
  const next = index.value + delta;
  if (next >= 0 && next < props.items.length) index.value = next;
};

function onKeydown(e: KeyboardEvent) {
  const target = e.target as HTMLElement;
  // Leave arrow keys to media controls, inputs and scrollable documents that have focus.
  if (target.closest("video, audio, input, textarea, [data-preview-scroll]")) return;
  const delta = e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0;
  if (!delta) return;
  e.preventDefault();
  go(delta);
}

/** Focus the viewer itself (not its first button) so arrow keys work straight away. */
function focusViewer(e: Event) {
  e.preventDefault();
  (e.target as HTMLElement | null)?.focus();
}

const ext = computed(() => (node.value ? extensionOf(node.value.name).toUpperCase() : ""));
</script>

<template>
  <DialogRoot :open="open" @update:open="(v: boolean) => (open = v)">
    <DialogPortal>
      <DialogContent
        data-theme="dark"
        class="fixed inset-0 z-50 flex flex-col bg-[rgb(8_11_18)] text-fg outline-none data-[state=open]:animate-fade-in"
        tabindex="-1"
        @keydown="onKeydown"
        @open-auto-focus="focusViewer"
      >
        <!-- Top bar -->
        <header class="flex h-14 shrink-0 items-center gap-2 border-b border-white/10 bg-black/40 px-2 sm:px-4">
          <UiButton variant="ghost" icon-only :icon="X" aria-label="Close preview" class="text-fg" @click="open = false" />
          <template v-if="node">
            <span class="hidden h-8 w-8 shrink-0 items-center justify-center rounded sm:flex" :class="kindInfo(kindOf(node)).tint">
              <component :is="kindInfo(kindOf(node)).icon" :size="16" :stroke-width="1.75" aria-hidden="true" />
            </span>
            <div class="min-w-0 flex-1">
              <DialogTitle class="truncate text-base font-medium text-fg">{{ node.name }}</DialogTitle>
              <DialogDescription class="tabular truncate text-xs text-fg-subtle">{{ formatBytes(node.size_bytes) }}<template v-if="ext"> · {{ ext }}</template></DialogDescription>
            </div>
            <span v-if="items.length > 1" class="tabular hidden px-2 text-sm text-fg-muted sm:inline" aria-live="polite">{{ index + 1 }} / {{ items.length }}</span>
            <UiButton variant="ghost" icon-only :icon="Info" aria-label="Details" class="hidden text-fg sm:inline-flex" @click="emit('details', node)" />
            <UiButton variant="ghost" icon-only :icon="Share2" aria-label="Share" class="text-fg" @click="emit('share', node)" />
            <UiButton variant="secondary" :icon="Download" :loading="isDownloading(node)" class="hidden sm:inline-flex" @click="downloadFile(node)">
              {{ isDownloading(node) ? `${progressOf(node)}%` : "Download" }}
            </UiButton>
            <UiButton variant="ghost" icon-only :icon="Download" :loading="isDownloading(node)" aria-label="Download" class="text-fg sm:hidden" @click="downloadFile(node)" />
          </template>
        </header>

        <UiProgress v-if="progress !== null" :value="progress * 100" label="Opening file" class="absolute inset-x-0 top-14 z-10 [&_*]:rounded-none" size="sm" />

        <!-- Body -->
        <main class="relative min-h-0 flex-1">
          <template v-if="node">
            <PreviewFallback v-if="problem" :node="node" :problem="problem" @download="downloadFile(node)" />
            <div v-else-if="!file" class="flex h-full items-center justify-center p-8" aria-busy="true">
              <div class="aspect-[4/3] w-full max-w-xl animate-pulse rounded-lg bg-white/5" />
            </div>
            <template v-else>
              <ImageView v-if="kind === 'image'" :key="node.id" :node="node" :file="file" @progress="progress = $event" @problem="onProblem" @swipe="go" />
              <MediaView v-else-if="kind === 'video' || kind === 'audio'" :key="node.id" :node="node" :file="file" :kind="kind" @progress="progress = $event" @problem="onProblem" />
              <PdfView v-else-if="kind === 'pdf'" :key="node.id" :file="file" @progress="progress = $event" @problem="onProblem" />
              <DocxView v-else-if="kind === 'docx'" :key="node.id" :file="file" @progress="progress = $event" @problem="onProblem" />
              <SheetView v-else-if="kind === 'sheet'" :key="node.id" :node="node" :file="file" @progress="progress = $event" @problem="onProblem" />
              <TextView v-else-if="kind === 'text'" :key="node.id" :node="node" :file="file" @progress="progress = $event" @problem="onProblem" />
            </template>
          </template>

          <!-- Previous / next -->
          <button
            v-if="canPrev"
            type="button"
            class="absolute left-3 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/50 text-white backdrop-blur transition-colors hover:bg-black/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:flex"
            aria-label="Previous file"
            @click="go(-1)"
          >
            <ChevronLeft :size="22" />
          </button>
          <button
            v-if="canNext"
            type="button"
            class="absolute right-3 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/50 text-white backdrop-blur transition-colors hover:bg-black/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:flex"
            aria-label="Next file"
            @click="go(1)"
          >
            <ChevronRight :size="22" />
          </button>
        </main>

        <!-- Phone navigation -->
        <footer v-if="items.length > 1" class="flex h-12 shrink-0 items-center justify-between border-t border-white/10 bg-black/40 px-2 md:hidden">
          <UiButton variant="ghost" icon-only :icon="ChevronLeft" aria-label="Previous file" :disabled="!canPrev" class="text-fg" @click="go(-1)" />
          <span class="tabular text-sm text-fg-muted">{{ index + 1 }} / {{ items.length }}</span>
          <UiButton variant="ghost" icon-only :icon="ChevronRight" aria-label="Next file" :disabled="!canNext" class="text-fg" @click="go(1)" />
        </footer>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

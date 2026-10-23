<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import { ZoomIn, ZoomOut } from "lucide-vue-next";
import UiButton from "../../../components/ui/UiButton.vue";
import { DecryptError, type EncryptedFile } from "../../../lib/crypto/encryptedFile";
import { normalizeApiError } from "../../../lib/errors";
import { openPdf } from "../../../lib/pdf";
import { LIMITS, type ViewProblem } from "./types";

const props = defineProps<{ file: EncryptedFile }>();
const emit = defineEmits<{ progress: [value: number | null]; problem: [p: ViewProblem] }>();

class PdfUnreadable extends Error {}
type PdfDoc = Awaited<ReturnType<typeof openPdf>>;
const doc = shallowRef<PdfDoc | null>(null);
const sizes = ref<{ w: number; h: number }[]>([]);
const scroller = ref<HTMLElement | null>(null);
const width = ref(800);
const zoom = ref(1);
const current = ref(1);
const canvases = ref<HTMLCanvasElement[]>([]);
const rendered = new Map<number, number>(); // page -> width it was drawn at
let observer: IntersectionObserver | null = null;
let resize: ResizeObserver | null = null;

/** Page width in CSS pixels: fit to the window, then zoom. */
const pageWidth = computed(() => Math.round(Math.min(width.value - 32, 960) * zoom.value));

onMounted(async () => {
  if (props.file.size > LIMITS.pdf) return emit("problem", { kind: "too-large" });
  try {
    const blob = await props.file.readAll((f) => emit("progress", f));
    const d = await openPdf(new Uint8Array(await blob.arrayBuffer())).catch(() => {
      throw new PdfUnreadable();
    });
    const list: { w: number; h: number }[] = [];
    for (let i = 1; i <= d.numPages; i++) {
      const v = (await d.getPage(i)).getViewport({ scale: 1 });
      list.push({ w: v.width, h: v.height });
    }
    doc.value = d;
    sizes.value = list;
    await nextTick();
    observe();
  } catch (err) {
    emit(
      "problem",
      err instanceof DecryptError ? { kind: "damaged" } : err instanceof PdfUnreadable ? { kind: "unsupported" } : { kind: "failed", message: normalizeApiError(err).message }
    );
  } finally {
    emit("progress", null);
  }
});

onMounted(() => {
  resize = new ResizeObserver(([entry]) => (width.value = entry.contentRect.width));
  if (scroller.value) resize.observe(scroller.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  resize?.disconnect();
  void doc.value?.destroy();
});

async function draw(page: number) {
  const canvas = canvases.value[page - 1];
  if (!doc.value || !canvas || rendered.get(page) === pageWidth.value) return;
  rendered.set(page, pageWidth.value);
  const p = await doc.value.getPage(page);
  const base = p.getViewport({ scale: 1 });
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const viewport = p.getViewport({ scale: (pageWidth.value / base.width) * dpr });
  canvas.width = Math.floor(viewport.width);
  canvas.height = Math.floor(viewport.height);
  await p.render({ canvasContext: canvas.getContext("2d")!, viewport }).promise.catch(() => rendered.delete(page));
}

function observe() {
  observer?.disconnect();
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        const page = Number((e.target as HTMLElement).dataset.page);
        if (e.isIntersecting) void draw(page);
      }
    },
    { root: scroller.value, rootMargin: "800px 0px" }
  );
  canvases.value.forEach((c) => observer!.observe(c));
}

// Redraw visible pages after zoom or resize.
watch(pageWidth, () => {
  rendered.clear();
  observe();
});

function onScroll() {
  const el = scroller.value;
  if (!el) return;
  const mid = el.scrollTop + el.clientHeight / 3;
  const idx = canvases.value.findIndex((c) => c.offsetTop + c.offsetHeight > mid);
  current.value = idx < 0 ? sizes.value.length : idx + 1;
}

const setZoom = (z: number) => (zoom.value = Math.min(3, Math.max(0.5, Math.round(z * 100) / 100)));
</script>

<template>
  <div class="relative h-full w-full">
    <div ref="scroller" data-preview-scroll tabindex="0" class="h-full overflow-auto outline-none" aria-label="PDF pages" @scroll.passive="onScroll">
      <div v-if="!sizes.length" class="mx-auto mt-6 aspect-[1/1.414] w-full max-w-2xl animate-pulse rounded bg-white/5" aria-hidden="true" />
      <div class="flex flex-col items-center gap-4 px-4 py-6">
        <canvas
          v-for="(s, i) in sizes"
          :key="i"
          ref="canvases"
          :data-page="i + 1"
          class="bg-white shadow-xl"
          :style="{ width: `${pageWidth}px`, height: `${Math.round((pageWidth * s.h) / s.w)}px` }"
          :aria-label="`Page ${i + 1}`"
          role="img"
        />
      </div>
    </div>
    <div v-if="sizes.length" class="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-black/60 p-1 text-white backdrop-blur">
      <span class="tabular px-3 text-sm" aria-live="polite">{{ current }} / {{ sizes.length }}</span>
      <UiButton variant="ghost" size="sm" icon-only :icon="ZoomOut" aria-label="Zoom out" class="rounded-full text-white" :disabled="zoom <= 0.5" @click="setZoom(zoom - 0.25)" />
      <span class="tabular w-12 text-center text-sm">{{ Math.round(zoom * 100) }}%</span>
      <UiButton variant="ghost" size="sm" icon-only :icon="ZoomIn" aria-label="Zoom in" class="rounded-full text-white" :disabled="zoom >= 3" @click="setZoom(zoom + 0.25)" />
    </div>
  </div>
</template>

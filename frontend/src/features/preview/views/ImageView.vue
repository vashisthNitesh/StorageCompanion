<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ZoomIn, ZoomOut, Maximize } from "lucide-vue-next";
import UiButton from "../../../components/ui/UiButton.vue";
import type { FileNode } from "../../../stores/files";
import { DecryptError, type EncryptedFile } from "../../../lib/crypto/encryptedFile";
import { normalizeApiError } from "../../../lib/errors";
import { mimeOf } from "../previewTypes";
import { LIMITS, type ViewProblem } from "./types";

const props = defineProps<{ node: FileNode; file: EncryptedFile }>();
const emit = defineEmits<{ progress: [value: number | null]; problem: [p: ViewProblem]; swipe: [delta: number] }>();

const url = ref("");
const loaded = ref(false);
const stage = ref<HTMLElement | null>(null);

const MIN = 1;
const MAX = 8;
const scale = ref(1);
const tx = ref(0);
const ty = ref(0);
const zoomed = computed(() => scale.value > 1.001);
const dragging = ref(false);

onMounted(async () => {
  if (props.file.size > LIMITS.image) return emit("problem", { kind: "too-large" });
  try {
    const blob = await props.file.readAll((f) => emit("progress", f));
    url.value = URL.createObjectURL(new Blob([blob], { type: mimeOf(props.node.name) }));
  } catch (err) {
    emit("problem", err instanceof DecryptError ? { kind: "damaged" } : { kind: "failed", message: normalizeApiError(err).message });
  } finally {
    emit("progress", null);
  }
});
onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
  if (url.value) URL.revokeObjectURL(url.value);
});

/** Zoom to `next`, keeping the point (px, py) — relative to the stage centre — still. */
function zoomTo(next: number, px = 0, py = 0) {
  next = Math.min(MAX, Math.max(MIN, next));
  const qx = (px - tx.value) / scale.value;
  const qy = (py - ty.value) / scale.value;
  scale.value = next;
  if (next === MIN) {
    tx.value = 0;
    ty.value = 0;
  } else {
    tx.value = px - next * qx;
    ty.value = py - next * qy;
  }
}
function fromCentre(e: { clientX: number; clientY: number }) {
  const r = stage.value!.getBoundingClientRect();
  return [e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2] as const;
}
function onWheel(e: WheelEvent) {
  e.preventDefault();
  zoomTo(scale.value * Math.exp(-e.deltaY * 0.0015), ...fromCentre(e));
}
function onDblClick(e: MouseEvent) {
  zoomTo(zoomed.value ? 1 : 2.5, ...fromCentre(e));
}

// Drag to pan, pinch to zoom, swipe (when not zoomed) to change file.
const pointers = new Map<number, { x: number; y: number }>();
let pinch: { dist: number; scale: number } | null = null;
let swipeStart: { x: number; y: number; t: number } | null = null;

function onPointerDown(e: PointerEvent) {
  (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  dragging.value = true;
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinch = { dist: Math.hypot(a.x - b.x, a.y - b.y), scale: scale.value };
    swipeStart = null;
  } else if (pointers.size === 1 && !zoomed.value) {
    swipeStart = { x: e.clientX, y: e.clientY, t: Date.now() };
  }
}
function onPointerMove(e: PointerEvent) {
  const prev = pointers.get(e.pointerId);
  if (!prev) return;
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pinch && pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    const mid = { clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 };
    zoomTo((pinch.scale * Math.hypot(a.x - b.x, a.y - b.y)) / pinch.dist, ...fromCentre(mid));
  } else if (zoomed.value && pointers.size === 1) {
    tx.value += e.clientX - prev.x;
    ty.value += e.clientY - prev.y;
  }
}
function onPointerUp(e: PointerEvent) {
  pointers.delete(e.pointerId);
  dragging.value = pointers.size > 0;
  if (pointers.size < 2) pinch = null;
  if (swipeStart && pointers.size === 0) {
    const dx = e.clientX - swipeStart.x;
    const dy = e.clientY - swipeStart.y;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5 && Date.now() - swipeStart.t < 600) emit("swipe", dx < 0 ? 1 : -1);
    swipeStart = null;
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key === "+" || e.key === "=") zoomTo(scale.value * 1.25);
  else if (e.key === "-") zoomTo(scale.value / 1.25);
  else if (e.key === "0") zoomTo(1);
  else return;
  e.preventDefault();
}
</script>

<template>
  <div class="relative h-full w-full select-none">
    <div
      ref="stage"
      class="flex h-full w-full touch-none items-center justify-center overflow-hidden p-2 sm:p-6"
      :class="zoomed ? 'cursor-grab active:cursor-grabbing' : 'cursor-zoom-in'"
      @wheel="onWheel"
      @dblclick="onDblClick"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <div v-if="!loaded" class="absolute inset-0 m-auto aspect-[4/3] w-full max-w-xl animate-pulse rounded-lg bg-white/5" aria-hidden="true" />
      <img
        v-if="url"
        :src="url"
        :alt="node.name"
        draggable="false"
        class="max-h-full max-w-full object-contain shadow-2xl transition-opacity duration-base"
        :class="loaded ? 'opacity-100' : 'opacity-0'"
        :style="{ transform: `translate(${tx}px, ${ty}px) scale(${scale})`, transition: dragging ? 'none' : 'transform 120ms ease-out' }"
        @load="loaded = true"
        @error="emit('problem', { kind: 'unsupported' })"
      />
    </div>

    <div v-if="loaded" class="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-black/60 p-1 text-white backdrop-blur">
      <UiButton variant="ghost" size="sm" icon-only :icon="ZoomOut" aria-label="Zoom out" class="rounded-full text-white" :disabled="!zoomed" @click="zoomTo(scale / 1.25)" />
      <span class="tabular w-12 text-center text-sm" aria-live="polite">{{ Math.round(scale * 100) }}%</span>
      <UiButton variant="ghost" size="sm" icon-only :icon="ZoomIn" aria-label="Zoom in" class="rounded-full text-white" :disabled="scale >= MAX" @click="zoomTo(scale * 1.25)" />
      <UiButton variant="ghost" size="sm" icon-only :icon="Maximize" aria-label="Fit to screen" class="rounded-full text-white" :disabled="!zoomed" @click="zoomTo(1)" />
    </div>
  </div>
</template>

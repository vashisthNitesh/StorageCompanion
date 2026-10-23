<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Play } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";
import { formatDuration } from "../../lib/format";
import { kindInfo, kindOf } from "../files/fileTypes";
import { canThumbnail, getThumbnail, type Thumbnail } from "./thumbnails";
import { previewKindOf } from "./previewTypes";

// File icon that turns into a real thumbnail (image, video frame, PDF page) once it
// scrolls into view and has been decrypted.
const props = defineProps<{ node: FileNode; variant: "card" | "row" }>();

const el = ref<HTMLElement | null>(null);
const thumb = ref<Thumbnail | null>(null);
const shown = ref(false);
const kind = computed(() => kindInfo(kindOf(props.node)));
const isVideo = computed(() => previewKindOf(props.node) === "video");

let observer: IntersectionObserver | null = null;
let token = 0;

function request() {
  const mine = ++token;
  void getThumbnail(props.node).then((t) => {
    if (mine === token) thumb.value = t;
  });
}

function observe() {
  observer?.disconnect();
  if (!el.value || !canThumbnail(props.node)) return;
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        observer?.disconnect();
        request();
      }
    },
    { rootMargin: "300px" }
  );
  observer.observe(el.value);
}

onMounted(observe);
onBeforeUnmount(() => observer?.disconnect());
watch(
  () => `${props.node.id}:${props.node.updated_at}`,
  () => {
    token++;
    thumb.value = null;
    shown.value = false;
    observe();
  }
);
</script>

<template>
  <span
    ref="el"
    class="relative flex shrink-0 items-center justify-center overflow-hidden"
    :class="[variant === 'card' ? 'h-full w-full' : 'h-8 w-8 rounded', shown ? 'bg-canvas-subtle' : kind.tint]"
  >
    <component :is="kind.icon" v-if="!shown" :size="variant === 'card' ? 36 : 18" :stroke-width="variant === 'card' ? 1.5 : 1.75" aria-hidden="true" />
    <img
      v-if="thumb"
      :src="thumb.url"
      alt=""
      draggable="false"
      class="absolute inset-0 h-full w-full object-cover transition-opacity duration-base"
      :class="shown ? 'opacity-100' : 'opacity-0'"
      @load="shown = true"
      @error="thumb = null"
    />
    <template v-if="isVideo && shown && variant === 'card'">
      <span class="absolute bottom-2 left-2 flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white" aria-hidden="true">
        <Play :size="13" fill="currentColor" class="ml-0.5" />
      </span>
      <span v-if="thumb?.duration" class="tabular absolute bottom-2 right-2 rounded bg-black/60 px-1.5 py-0.5 text-xs font-medium text-white">
        {{ formatDuration(thumb.duration) }}
      </span>
    </template>
    <span v-else-if="isVideo && shown" class="absolute inset-0 flex items-center justify-center bg-black/25 text-white" aria-hidden="true">
      <Play :size="12" fill="currentColor" />
    </span>
  </span>
</template>

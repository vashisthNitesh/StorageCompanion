<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Play } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";
import { formatDuration } from "../../lib/format";
import { kindInfo, kindOf } from "../files/fileTypes";
import { canThumbnail, getThumbnail, type Thumbnail } from "./thumbnails";
import { previewKindOf } from "./previewTypes";
import FileGlyph from "./FileGlyph.vue";

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
    :class="variant === 'card' ? 'h-full w-full' : ['h-8 w-8 rounded', shown ? 'bg-canvas-subtle' : kind.tint]"
  >
    <span v-if="!shown && variant === 'card'" class="flex h-[60%] max-h-32 items-center justify-center transition-transform duration-slow ease-out group-hover:scale-[1.04]">
      <FileGlyph :name="node.name" :kind="kindOf(node)" />
    </span>
    <component :is="kind.icon" v-else-if="!shown" :size="18" :stroke-width="1.75" aria-hidden="true" />
    <img
      v-if="thumb"
      :src="thumb.url"
      alt=""
      draggable="false"
      class="absolute inset-0 h-full w-full object-cover transition-[opacity,transform] duration-slow ease-out"
      :class="[shown ? 'opacity-100' : 'opacity-0', variant === 'card' ? 'group-hover:scale-[1.03]' : '']"
      @load="shown = true"
      @error="thumb = null"
    />
    <span
      v-if="isVideo && shown && variant === 'card'"
      class="tabular absolute bottom-2 left-2 flex items-center gap-1 rounded-full bg-black/55 py-0.5 pl-1.5 pr-2 text-[11px] font-medium text-white backdrop-blur-sm"
      aria-hidden="true"
    >
      <Play :size="10" fill="currentColor" />
      {{ thumb?.duration ? formatDuration(thumb.duration) : "Video" }}
    </span>
    <span v-else-if="isVideo && shown" class="absolute inset-0 flex items-center justify-center bg-black/25 text-white" aria-hidden="true">
      <Play :size="12" fill="currentColor" />
    </span>
  </span>
</template>

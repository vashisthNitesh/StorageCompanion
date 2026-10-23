<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { Music } from "lucide-vue-next";
import type { FileNode } from "../../../stores/files";
import { DecryptError, type EncryptedFile } from "../../../lib/crypto/encryptedFile";
import { createStreamUrl, ensureStreamWorker } from "../../../lib/mediaStream";
import { normalizeApiError } from "../../../lib/errors";
import { mimeOf } from "../previewTypes";
import { LIMITS, type ViewProblem } from "./types";

// Streams through the service worker, so playback starts at once and seeking only
// fetches the parts it needs. Without the worker, small files are decrypted first.
const props = defineProps<{ node: FileNode; file: EncryptedFile; kind: "video" | "audio" }>();
const emit = defineEmits<{ progress: [value: number | null]; problem: [p: ViewProblem] }>();

const src = ref("");
const ready = ref(false);
const media = ref<HTMLMediaElement | null>(null);
let release: (() => void) | null = null;

onMounted(async () => {
  const type = mimeOf(props.node.name);
  if (await ensureStreamWorker()) {
    const stream = createStreamUrl(props.file, type, props.node.name);
    release = () => stream.release();
    src.value = stream.url;
    return;
  }
  if (props.file.size > LIMITS.mediaInMemory) return emit("problem", { kind: "too-large" });
  try {
    const blob = await props.file.readAll((f) => emit("progress", f));
    const url = URL.createObjectURL(new Blob([blob], { type }));
    release = () => URL.revokeObjectURL(url);
    src.value = url;
  } catch (err) {
    emit("problem", err instanceof DecryptError ? { kind: "damaged" } : { kind: "failed", message: normalizeApiError(err).message });
  } finally {
    emit("progress", null);
  }
});

onBeforeUnmount(() => {
  const el = media.value;
  if (el) {
    el.pause();
    el.removeAttribute("src");
    el.load();
  }
  release?.();
});

function onError() {
  const code = media.value?.error?.code;
  // 3 = decode, 4 = format/codec not supported by this browser.
  emit("problem", code === 3 || code === 4 ? { kind: "unsupported" } : { kind: "failed", message: "The file stopped loading. Check your connection and try again." });
}
</script>

<template>
  <div class="flex h-full w-full items-center justify-center bg-black">
    <template v-if="kind === 'video'">
      <div v-if="!ready" class="absolute inset-0 m-auto aspect-video w-full max-w-3xl animate-pulse rounded-lg bg-white/5" aria-hidden="true" />
      <video
        v-if="src"
        ref="media"
        :src="src"
        controls
        autoplay
        playsinline
        preload="auto"
        class="h-full w-full object-contain outline-none"
        :aria-label="node.name"
        @loadeddata="ready = true"
        @error="onError"
      />
    </template>
    <div v-else class="w-full max-w-md px-6 text-center">
      <span class="mx-auto flex h-28 w-28 items-center justify-center rounded-2xl bg-pink-500/15 text-pink-400"><Music :size="48" :stroke-width="1.25" aria-hidden="true" /></span>
      <p class="mt-5 truncate text-md font-medium text-fg">{{ node.name }}</p>
      <audio v-if="src" ref="media" :src="src" controls autoplay preload="auto" class="mt-6 w-full" :aria-label="node.name" @loadeddata="ready = true" @error="onError" />
    </div>
  </div>
</template>

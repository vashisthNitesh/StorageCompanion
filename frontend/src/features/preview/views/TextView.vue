<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import UiSwitch from "../../../components/ui/UiSwitch.vue";
import type { FileNode } from "../../../stores/files";
import { DecryptError, type EncryptedFile } from "../../../lib/crypto/encryptedFile";
import { normalizeApiError } from "../../../lib/errors";
import type { ViewProblem } from "./types";

const props = defineProps<{ node: FileNode; file: EncryptedFile }>();
const emit = defineEmits<{ progress: [value: number | null]; problem: [p: ViewProblem] }>();

/** Only the start of very large text files is shown. */
const MAX_BYTES = 2 * 1024 * 1024;
const text = ref<string | null>(null);
const wrap = ref(false);
const truncated = computed(() => props.file.size > MAX_BYTES);
const lineCount = computed(() => (text.value ? text.value.split("\n").length : 0));
const numbers = computed(() => Array.from({ length: lineCount.value }, (_, i) => i + 1).join("\n"));

onMounted(async () => {
  try {
    const bytes = await props.file.read(0, Math.min(props.file.size, MAX_BYTES));
    const decoded = new TextDecoder("utf-8").decode(bytes);
    // Lots of replacement characters means it isn't really text.
    const bad = (decoded.match(/�/g)?.length ?? 0) / Math.max(1, decoded.length);
    if (bad > 0.02 || decoded.includes("\u0000")) return emit("problem", { kind: "unsupported" });
    text.value = decoded;
  } catch (err) {
    emit("problem", err instanceof DecryptError ? { kind: "damaged" } : { kind: "failed", message: normalizeApiError(err).message });
  }
});
</script>

<template>
  <div class="flex h-full flex-col bg-surface">
    <div v-if="text === null" class="m-6 space-y-2" aria-hidden="true">
      <div v-for="i in 10" :key="i" class="h-4 animate-pulse rounded bg-white/5" :style="{ width: `${40 + ((i * 37) % 55)}%` }" />
    </div>
    <template v-else>
      <div class="flex shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-2 text-sm text-fg-muted">
        <span class="tabular">{{ lineCount.toLocaleString() }} lines<template v-if="truncated"> · showing the first 2 MB</template></span>
        <UiSwitch v-model="wrap" label="Wrap lines" class="items-center gap-2 [&_label]:text-sm [&_label]:text-fg-muted" />
      </div>
      <div data-preview-scroll tabindex="0" class="min-h-0 flex-1 overflow-auto outline-none" :aria-label="node.name">
        <div class="flex min-w-full font-mono text-[13px] leading-5">
          <pre v-if="!wrap" class="tabular sticky left-0 shrink-0 select-none bg-surface-sunken px-3 py-3 text-right text-fg-subtle" aria-hidden="true">{{ numbers }}</pre>
          <pre class="min-w-0 flex-1 px-4 py-3 text-fg" :class="wrap ? 'whitespace-pre-wrap break-words' : 'whitespace-pre'">{{ text }}</pre>
        </div>
      </div>
    </template>
  </div>
</template>

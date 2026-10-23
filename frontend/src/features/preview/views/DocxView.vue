<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { DecryptError, type EncryptedFile } from "../../../lib/crypto/encryptedFile";
import { normalizeApiError } from "../../../lib/errors";
import { LIMITS, type ViewProblem } from "./types";

const props = defineProps<{ file: EncryptedFile }>();
const emit = defineEmits<{ progress: [value: number | null]; problem: [p: ViewProblem] }>();

const body = ref<HTMLElement | null>(null);
const styles = ref<HTMLElement | null>(null);
const ready = ref(false);

const host = ref<HTMLElement | null>(null);
let resize: ResizeObserver | null = null;
onBeforeUnmount(() => resize?.disconnect());

/** Shrink pages to fit narrow screens (never enlarge). */
function fit() {
  const wrapper = body.value?.querySelector<HTMLElement>(".docx-wrapper");
  const page = wrapper?.querySelector<HTMLElement>("section.docx");
  if (!wrapper || !page || !host.value) return;
  const available = host.value.clientWidth - 24;
  wrapper.style.zoom = String(Math.min(1, available / page.offsetWidth));
}

class Unreadable extends Error {}

onMounted(async () => {
  if (props.file.size > LIMITS.docx) return emit("problem", { kind: "too-large" });
  try {
    const blob = await props.file.readAll((f) => emit("progress", f));
    const { renderAsync } = await import("docx-preview");
    await renderAsync(blob, body.value!, styles.value!, {
      className: "docx",
      inWrapper: true,
      breakPages: true,
      ignoreLastRenderedPageBreak: true,
      useBase64URL: true,
      renderHeaders: true,
      renderFooters: true,
    }).catch(() => {
      throw new Unreadable();
    });
    // Links in a document only open web or mail addresses, in a new tab.
    body.value!.querySelectorAll("a[href]").forEach((a) => {
      const href = a.getAttribute("href") || "";
      if (/^(https?:|mailto:)/i.test(href)) {
        a.setAttribute("target", "_blank");
        a.setAttribute("rel", "noopener noreferrer");
      } else if (!href.startsWith("#")) a.removeAttribute("href");
    });
    ready.value = true;
    fit();
    resize = new ResizeObserver(fit);
    resize.observe(host.value!);
  } catch (err) {
    emit("problem", err instanceof DecryptError ? { kind: "damaged" } : err instanceof Unreadable ? { kind: "unsupported" } : { kind: "failed", message: normalizeApiError(err).message });
  } finally {
    emit("progress", null);
  }
});
</script>

<template>
  <div ref="host" data-preview-scroll tabindex="0" class="docx-host h-full overflow-auto outline-none" aria-label="Document">
    <div v-if="!ready" class="mx-auto mt-6 aspect-[1/1.414] w-full max-w-2xl animate-pulse rounded bg-white/5" aria-hidden="true" />
    <div ref="styles" />
    <div ref="body" />
  </div>
</template>

<style scoped>
/* docx-preview draws white pages on a grey wrapper; match the viewer's backdrop. */
.docx-host :deep(.docx-wrapper) {
  background: transparent;
  padding: 24px 12px;
}
.docx-host :deep(.docx-wrapper > section.docx) {
  box-shadow: 0 20px 40px rgb(0 0 0 / 0.45);
  margin-bottom: 16px;
  color: #111;
}
</style>

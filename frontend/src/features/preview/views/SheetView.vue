<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from "vue";
import type { FileNode } from "../../../stores/files";
import { DecryptError, type EncryptedFile } from "../../../lib/crypto/encryptedFile";
import { normalizeApiError } from "../../../lib/errors";
import { LIMITS, type ViewProblem } from "./types";

const props = defineProps<{ node: FileNode; file: EncryptedFile }>();
const emit = defineEmits<{ progress: [value: number | null]; problem: [p: ViewProblem] }>();

const MAX_ROWS = 2000;
const MAX_COLS = 60;

type Sheet = { name: string; rows: string[][]; totalRows: number; totalCols: number };
const sheets = shallowRef<Sheet[]>([]);
const active = ref(0);
const sheet = computed(() => sheets.value[active.value]);

function columnName(i: number) {
  let s = "";
  for (i++; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + ((i - 1) % 26)) + s;
  return s;
}

class Unreadable extends Error {}

onMounted(async () => {
  if (props.file.size > LIMITS.sheet) return emit("problem", { kind: "too-large" });
  try {
    const blob = await props.file.readAll((f) => emit("progress", f));
    const XLSX = await import("xlsx");
    let book: import("xlsx").WorkBook;
    try {
      book = XLSX.read(new Uint8Array(await blob.arrayBuffer()), { type: "array", dense: true, cellDates: true, sheetRows: MAX_ROWS + 1 });
    } catch {
      throw new Unreadable();
    }
    sheets.value = book.SheetNames.map((name) => {
      const ws = book.Sheets[name];
      const all = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, raw: false, blankrows: false, defval: "" });
      const range = ws["!ref"] ? XLSX.utils.decode_range(ws["!ref"]) : null;
      const totalCols = range ? range.e.c + 1 : Math.max(0, ...all.map((r) => r.length));
      return {
        name,
        rows: all.slice(0, MAX_ROWS).map((r) => r.slice(0, MAX_COLS).map((c) => (c == null ? "" : String(c)))),
        totalRows: range ? range.e.r + 1 : all.length,
        totalCols,
      };
    });
  } catch (err) {
    emit("problem", err instanceof DecryptError ? { kind: "damaged" } : err instanceof Unreadable ? { kind: "unsupported" } : { kind: "failed", message: normalizeApiError(err).message });
  } finally {
    emit("progress", null);
  }
});

const cols = computed(() => Math.min(MAX_COLS, Math.max(1, ...(sheet.value?.rows.map((r) => r.length) ?? [1]))));
const truncated = computed(() => !!sheet.value && (sheet.value.totalRows > MAX_ROWS || sheet.value.totalCols > MAX_COLS));
</script>

<template>
  <div class="flex h-full flex-col bg-surface">
    <div v-if="!sheets.length" class="m-6 space-y-2" aria-hidden="true">
      <div v-for="i in 8" :key="i" class="h-7 animate-pulse rounded bg-white/5" />
    </div>
    <template v-else>
      <p v-if="truncated" class="shrink-0 border-b border-line bg-warning-soft px-4 py-2 text-sm text-warning">
        Showing the first {{ MAX_ROWS.toLocaleString() }} rows and {{ MAX_COLS }} columns. Download the file to see everything.
      </p>
      <div data-preview-scroll tabindex="0" class="min-h-0 flex-1 overflow-auto outline-none" :aria-label="`Sheet ${sheet?.name}`">
        <table class="tabular border-separate border-spacing-0 text-sm text-fg">
          <thead>
            <tr>
              <th class="sticky left-0 top-0 z-20 h-7 min-w-[48px] border-b border-r border-line bg-surface-sunken" />
              <th
                v-for="c in cols"
                :key="c"
                scope="col"
                class="sticky top-0 z-10 h-7 min-w-[96px] border-b border-r border-line bg-surface-sunken px-2 text-center text-xs font-medium text-fg-muted"
              >
                {{ columnName(c - 1) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, r) in sheet!.rows" :key="r">
              <th scope="row" class="sticky left-0 z-10 h-7 border-b border-r border-line bg-surface-sunken px-2 text-right text-xs font-medium text-fg-muted">{{ r + 1 }}</th>
              <td v-for="c in cols" :key="c" class="h-7 max-w-[320px] truncate whitespace-nowrap border-b border-r border-line px-2">{{ row[c - 1] ?? "" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav v-if="sheets.length > 1" class="flex shrink-0 gap-1 overflow-x-auto border-t border-line bg-surface-sunken px-2 py-1.5 scrollbar-thin" aria-label="Sheets">
        <button
          v-for="(s, i) in sheets"
          :key="s.name"
          type="button"
          class="shrink-0 rounded px-3 py-1 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          :class="i === active ? 'bg-surface font-medium text-fg shadow-xs' : 'text-fg-muted hover:text-fg'"
          :aria-current="i === active ? 'page' : undefined"
          @click="active = i"
        >
          {{ s.name }}
        </button>
      </nav>
    </template>
  </div>
</template>

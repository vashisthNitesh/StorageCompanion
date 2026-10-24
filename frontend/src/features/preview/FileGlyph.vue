<script setup lang="ts">
import { computed } from "vue";
import type { FileKind } from "../files/fileTypes";
import { kindInfo } from "../files/fileTypes";
import { extensionOf } from "./previewTypes";

// Large document icon for files without a thumbnail: a page with a folded corner, the file
// type's icon and a solid badge with its extension. Badge colours keep white text legible.
const props = defineProps<{ name: string; kind: FileKind }>();

const BADGE: Record<FileKind, { badge: string; icon: string }> = {
  folder: { badge: "bg-amber-600", icon: "text-amber-600" },
  image: { badge: "bg-emerald-700", icon: "text-emerald-600" },
  video: { badge: "bg-violet-600", icon: "text-violet-600" },
  audio: { badge: "bg-pink-600", icon: "text-pink-600" },
  pdf: { badge: "bg-red-600", icon: "text-red-600" },
  doc: { badge: "bg-blue-600", icon: "text-blue-600" },
  sheet: { badge: "bg-green-700", icon: "text-green-700" },
  slides: { badge: "bg-orange-700", icon: "text-orange-600" },
  archive: { badge: "bg-slate-600", icon: "text-slate-500" },
  code: { badge: "bg-sky-700", icon: "text-sky-600" },
  other: { badge: "bg-slate-500", icon: "text-slate-400" },
};
const style = computed(() => BADGE[props.kind]);
const ext = computed(() => {
  const e = extensionOf(props.name).toUpperCase();
  return e && e.length <= 4 ? e : kindInfo(props.kind).label.toUpperCase().slice(0, 4);
});
</script>

<template>
  <span class="relative inline-flex aspect-[56/72] h-full items-center justify-center" aria-hidden="true">
    <svg viewBox="0 0 56 72" class="absolute inset-0 h-full w-full drop-shadow-[0_2px_6px_rgb(var(--shadow-color)/0.10)]">
      <path
        d="M10 1.25h27.5l17.25 17.25V62A8.75 8.75 0 0 1 46 70.75H10A8.75 8.75 0 0 1 1.25 62V10A8.75 8.75 0 0 1 10 1.25Z"
        class="fill-surface-raised stroke-line"
        stroke-width="1.5"
      />
      <path d="M37.5 1.25V12.5a6 6 0 0 0 6 6h11.25" class="fill-canvas-subtle stroke-line" stroke-width="1.5" stroke-linejoin="round" />
    </svg>
    <component :is="kindInfo(kind).icon" class="relative -mt-[18%] h-[30%] w-[30%]" :class="style.icon" :stroke-width="1.75" />
    <span
      class="absolute -left-[12%] bottom-[16%] rounded-[5px] px-[0.4em] py-[0.12em] text-[clamp(9px,0.9vw,11px)] font-bold leading-tight tracking-wide text-white shadow-sm"
      :class="style.badge"
    >
      {{ ext }}
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { FileKind } from "../files/fileTypes";
import { kindInfo } from "../files/fileTypes";
import { extensionOf } from "./previewTypes";

// Illustration for files without a thumbnail: a document sheet with a folded corner and
// a coloured type label on a tinted backdrop, instead of a bare icon.
const props = defineProps<{ name: string; kind: FileKind }>();

const STYLE: Record<FileKind, { backdrop: string; label: string; accent: string }> = {
  folder: { backdrop: "from-amber-500/20 to-amber-500/5", label: "bg-amber-500", accent: "bg-amber-500/25" },
  image: { backdrop: "from-emerald-500/20 to-emerald-500/5", label: "bg-emerald-600", accent: "bg-emerald-500/25" },
  video: { backdrop: "from-violet-500/25 to-violet-500/5", label: "bg-violet-600", accent: "bg-violet-500/25" },
  audio: { backdrop: "from-pink-500/20 to-pink-500/5", label: "bg-pink-600", accent: "bg-pink-500/30" },
  pdf: { backdrop: "from-rose-500/20 to-rose-500/5", label: "bg-rose-600", accent: "bg-rose-500/25" },
  doc: { backdrop: "from-blue-500/20 to-blue-500/5", label: "bg-blue-600", accent: "bg-blue-500/25" },
  sheet: { backdrop: "from-green-600/20 to-green-600/5", label: "bg-green-700", accent: "bg-green-600/25" },
  slides: { backdrop: "from-orange-500/20 to-orange-500/5", label: "bg-orange-600", accent: "bg-orange-500/25" },
  archive: { backdrop: "from-slate-500/20 to-slate-500/5", label: "bg-slate-600", accent: "bg-slate-500/25" },
  code: { backdrop: "from-sky-500/20 to-sky-500/5", label: "bg-sky-600", accent: "bg-sky-500/25" },
  other: { backdrop: "from-slate-400/20 to-slate-400/5", label: "bg-slate-500", accent: "bg-slate-400/25" },
};
const style = computed(() => STYLE[props.kind]);
const ext = computed(() => extensionOf(props.name).slice(0, 4).toUpperCase() || "FILE");
const icon = computed(() => kindInfo(props.kind).icon);
</script>

<template>
  <span class="absolute inset-0 flex items-center justify-center bg-gradient-to-br" :class="style.backdrop" aria-hidden="true">
    <span class="relative aspect-[3/4] h-[68%] rounded-md bg-surface-raised shadow-md ring-1 ring-black/5 transition-transform duration-slow ease-out group-hover:-translate-y-1 group-hover:rotate-[-2deg] [clip-path:polygon(0_0,72%_0,100%_22%,100%_100%,0_100%)]">
      <!-- folded corner -->
      <span class="absolute right-0 top-0 h-[22%] w-[28%] rounded-bl-sm bg-line [clip-path:polygon(0_0,100%_100%,0_100%)]" />
      <!-- content -->
      <span v-if="kind === 'audio'" class="absolute inset-x-[16%] top-[30%] flex h-[26%] items-end gap-[6%]">
        <span v-for="h in [40, 75, 55, 95, 65, 35, 80]" :key="h" class="flex-1 rounded-full" :class="style.label" :style="{ height: `${h}%`, opacity: 0.7 }" />
      </span>
      <span v-else-if="kind === 'sheet'" class="absolute inset-x-[14%] top-[24%] grid grid-cols-3 gap-[3px]">
        <span v-for="i in 12" :key="i" class="h-[5px] rounded-[1px]" :class="i <= 3 ? style.label : style.accent" :style="i <= 3 ? { opacity: 0.7 } : undefined" />
      </span>
      <span v-else class="absolute inset-x-[16%] top-[24%] flex flex-col gap-[5px]">
        <component :is="icon" :size="16" :stroke-width="2" class="mb-1 opacity-80" :class="style.label.replace('bg-', 'text-')" />
        <span class="h-[4px] w-[85%] rounded-full" :class="style.accent" />
        <span class="h-[4px] w-full rounded-full" :class="style.accent" />
        <span class="h-[4px] w-[70%] rounded-full" :class="style.accent" />
      </span>
      <!-- type label -->
      <span class="absolute -left-1.5 bottom-[14%] rounded-[4px] px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-white shadow-sm" :class="style.label">{{ ext }}</span>
    </span>
  </span>
</template>

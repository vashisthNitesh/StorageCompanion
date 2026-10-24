<script setup lang="ts">
import { Folder, Clock, Trash2, Upload, Lock, Play, FileText, Image as ImageIcon, Film, Check, Search } from "lucide-vue-next";

// Decorative product preview for the landing page (hidden from assistive tech).
// "Photos" are CSS gradients so the page ships no image assets.
const files = [
  { name: "DSC_0412.ARW", meta: "48.2 MB", kind: "photo", art: "sunset" },
  { name: "Highlights_4K_final.mov", meta: "3.4 GB", kind: "video", art: "dusk", duration: "4:12" },
  { name: "Contract_signed.pdf", meta: "412 KB", kind: "pdf" },
  { name: "Mehndi_0098.jpg", meta: "12.6 MB", kind: "photo", art: "lake" },
  { name: "Pheras_wide.jpg", meta: "18.1 MB", kind: "photo", art: "warm" },
  { name: "Teaser_vertical.mp4", meta: "286 MB", kind: "video", art: "night", duration: "0:58" },
] as const;

const ART: Record<string, string> = {
  sunset: "linear-gradient(180deg, #fbcfe8 0%, #fdba74 42%, #ea580c 60%, #431407 100%)",
  dusk: "linear-gradient(160deg, #1e1b4b 0%, #6d28d9 45%, #f472b6 100%)",
  lake: "linear-gradient(180deg, #bae6fd 0%, #7dd3fc 40%, #0e7490 62%, #083344 100%)",
  warm: "linear-gradient(135deg, #fde68a 0%, #f59e0b 40%, #b45309 75%, #451a03 100%)",
  night: "linear-gradient(200deg, #0f172a 0%, #1d4ed8 55%, #22d3ee 100%)",
};
</script>

<template>
  <div class="relative" aria-hidden="true">
    <!-- Glow -->
    <div class="pointer-events-none absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-tr from-primary/25 via-violet-400/15 to-emerald-300/20 blur-2xl" />

    <div class="overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl ring-1 ring-black/5">
      <!-- Window chrome -->
      <div class="flex items-center gap-3 border-b border-line bg-canvas-subtle px-4 py-2.5">
        <span class="flex gap-1.5"><span class="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" /><span class="h-2.5 w-2.5 rounded-full bg-[#febc2e]" /><span class="h-2.5 w-2.5 rounded-full bg-[#28c840]" /></span>
        <span class="mx-auto flex items-center gap-1.5 rounded-md bg-surface px-3 py-1 text-xs text-fg-subtle shadow-xs"><Lock :size="11" /> smartspacedata.com/app/files</span>
        <span class="w-[46px]" />
      </div>

      <div class="grid md:grid-cols-[176px_minmax(0,1fr)]">
        <!-- Sidebar -->
        <aside class="hidden flex-col gap-1 border-r border-line bg-surface p-3 md:flex">
          <span class="mb-2 flex h-8 items-center justify-center gap-1.5 rounded-md bg-primary text-xs font-medium text-primary-fg"><Upload :size="13" /> Upload</span>
          <span class="flex items-center gap-2 rounded-md bg-primary-soft px-2 py-1.5 text-xs font-medium text-primary"><Folder :size="14" /> My files</span>
          <span class="flex items-center gap-2 px-2 py-1.5 text-xs text-fg-muted"><Clock :size="14" /> Recent</span>
          <span class="flex items-center gap-2 px-2 py-1.5 text-xs text-fg-muted"><Trash2 :size="14" /> Trash</span>
          <div class="mt-auto rounded-lg border border-line p-2.5">
            <p class="text-[11px] font-medium text-fg">Storage</p>
            <div class="mt-1.5 h-1 overflow-hidden rounded-full bg-canvas-subtle"><div class="h-full w-[38%] rounded-full bg-primary" /></div>
            <p class="mt-1.5 text-[10px] text-fg-subtle">76 GB of 200 GB</p>
          </div>
        </aside>

        <!-- Main -->
        <div class="min-w-0 bg-canvas p-3 sm:p-4">
          <div class="flex items-center justify-between gap-3">
            <p class="truncate text-sm font-semibold text-fg"><span class="text-fg-subtle">My files /</span> Wedding — Mehta 2026</p>
            <span class="hidden items-center gap-1.5 rounded-md border border-line bg-surface px-2 py-1 text-[11px] text-fg-subtle sm:flex"><Search :size="11" /> Search</span>
          </div>

          <div class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
            <span v-for="f in ['Ceremony', 'Reception', 'Haldi']" :key="f" class="flex items-center gap-2 rounded-lg bg-tile px-2.5 py-2 text-xs font-medium text-fg last:hidden sm:last:flex">
              <Folder :size="15" class="shrink-0 text-amber-500" fill="currentColor" fill-opacity="0.2" /> {{ f }}
            </span>
          </div>

          <div class="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
            <div
              v-for="(f, i) in files"
              :key="f.name"
              class="rounded-xl px-1 pb-1"
              :class="[i === 1 ? 'bg-primary-soft ring-1 ring-primary/40' : 'bg-tile', i > 3 ? 'hidden sm:block' : '']"
            >
              <div class="flex items-center gap-1.5 px-1 py-1.5">
                <span v-if="i === 1" class="flex h-3 w-3 shrink-0 items-center justify-center rounded-[3px] bg-primary text-primary-fg"><Check :size="8" :stroke-width="3" /></span>
                <component
                  :is="f.kind === 'pdf' ? FileText : f.kind === 'video' ? Film : ImageIcon"
                  v-else
                  :size="12"
                  class="shrink-0"
                  :class="f.kind === 'pdf' ? 'text-red-600' : f.kind === 'video' ? 'text-violet-600' : 'text-emerald-600'"
                />
                <p class="truncate text-[11px] font-medium text-fg">{{ f.name }}</p>
              </div>
              <div class="relative aspect-[4/3] overflow-hidden rounded-md bg-surface-sunken">
                <div v-if="f.kind !== 'pdf'" class="absolute inset-0" :style="{ background: ART[f.art!] }">
                  <!-- hills -->
                  <div class="absolute inset-x-0 bottom-0 h-1/2 bg-black/25 [clip-path:polygon(0_60%,22%_25%,40%_55%,62%_10%,82%_45%,100%_20%,100%_100%,0_100%)]" />
                </div>
                <div v-else class="absolute inset-0 flex justify-center pt-2.5">
                  <div class="w-3/5 space-y-1.5 rounded-sm bg-white p-2 shadow-sm">
                    <div class="h-1.5 w-1/2 rounded bg-slate-300" />
                    <div v-for="n in 5" :key="n" class="h-1 rounded bg-slate-200" :class="n === 5 ? 'w-2/3' : ''" />
                  </div>
                </div>
                <span v-if="f.kind === 'video'" class="absolute bottom-1 left-1 flex items-center gap-0.5 rounded-full bg-black/55 py-px pl-1 pr-1.5 text-[9px] font-medium text-white">
                  <Play :size="7" fill="currentColor" /> {{ f.duration }}
                </span>
              </div>
              <p class="px-1 pt-1 text-[10px] text-fg-subtle">{{ f.meta }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Floating chips -->
    <div class="absolute -top-4 right-6 hidden animate-float items-center gap-2 rounded-full border border-line bg-surface px-3 py-2 text-xs font-medium text-fg shadow-lg sm:flex">
      <span class="flex h-6 w-6 items-center justify-center rounded-full bg-success-soft text-success"><Lock :size="13" /></span>
      Encrypted on your device
    </div>
    <div class="absolute -bottom-5 right-3 w-56 animate-float rounded-xl border border-line bg-surface p-3 shadow-lg [animation-delay:-3s] sm:right-6 lg:-right-6">
      <div class="flex items-center justify-between text-xs">
        <span class="flex items-center gap-1.5 font-medium text-fg"><Upload :size="13" class="text-primary" /> Uploading 3 files</span>
        <span class="text-fg-subtle">4K</span>
      </div>
      <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-canvas-subtle"><div class="h-full animate-progress-loop rounded-full bg-primary" /></div>
      <p class="mt-1.5 text-[11px] text-fg-subtle">Original quality · no compression</p>
    </div>
  </div>
</template>

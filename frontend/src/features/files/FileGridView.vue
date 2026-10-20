<script setup lang="ts">
import { Download, Loader2, MoreVertical } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";
import { formatBytes } from "../../lib/format";
import { kindInfo, kindOf } from "./fileTypes";
import FileName from "./FileName.vue";
import { useFileDownload } from "./useFileDownload";

defineProps<{ items: FileNode[]; selectedId: string | null }>();
const emit = defineEmits<{
  select: [node: FileNode];
  open: [node: FileNode];
  menu: [node: FileNode, x: number, y: number];
}>();
const { downloadFile, isDownloading, progressOf } = useFileDownload();

function menuFromButton(node: FileNode, e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  emit("menu", node, rect.right - 224, rect.bottom + 4);
}
</script>

<template>
  <ul role="listbox" aria-label="Files and folders" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
    <li
      v-for="node in items"
      :key="node.id"
      role="option"
      :aria-selected="selectedId === node.id"
      tabindex="0"
      class="group relative flex cursor-default flex-col rounded-xl border bg-white p-3 transition-shadow"
      :class="selectedId === node.id ? 'border-brand-400 ring-2 ring-brand-100' : 'border-slate-200 hover:shadow-card hover:border-slate-300'"
      @click="emit('select', node)"
      @dblclick="emit('open', node)"
      @keydown.enter="emit('open', node)"
      @contextmenu.prevent="emit('menu', node, $event.clientX, $event.clientY)"
    >
      <div class="flex aspect-[4/3] items-center justify-center rounded-lg" :class="kindInfo(kindOf(node)).tint">
        <component :is="kindInfo(kindOf(node)).icon" class="h-10 w-10" :class="{ 'fill-amber-400/30': node.type === 'folder' }" />
      </div>
      <div class="mt-3 flex items-start gap-1">
        <div class="min-w-0 flex-1">
          <FileName :name="node.name" :is-folder="node.type === 'folder'" class="text-sm font-medium text-slate-900" />
          <p class="mt-0.5 text-xs text-slate-500">
            {{ node.type === "folder" ? "Folder" : formatBytes(node.size_bytes) }}
          </p>
        </div>
        <button class="icon-btn -mr-1 h-8 w-8 shrink-0" title="More actions" :aria-label="`More actions for ${node.name}`" @click.stop="menuFromButton(node, $event)">
          <MoreVertical class="h-4 w-4" />
        </button>
      </div>
      <button
        v-if="node.type === 'file'"
        class="absolute right-5 top-5 inline-flex h-8 items-center gap-1 rounded-lg bg-white/95 px-2 text-xs font-medium text-slate-700 shadow-card transition-opacity hover:text-brand-700 focus:opacity-100"
        :class="isDownloading(node) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 [@media(hover:none)]:opacity-100'"
        :title="`Download ${node.name}`"
        :disabled="isDownloading(node)"
        @click.stop="downloadFile(node)"
      >
        <Loader2 v-if="isDownloading(node)" class="h-3.5 w-3.5 animate-spin" />
        <Download v-else class="h-3.5 w-3.5" />
        {{ isDownloading(node) ? `${progressOf(node)}%` : "Download" }}
      </button>
    </li>
  </ul>
</template>

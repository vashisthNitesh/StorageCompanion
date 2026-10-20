<script setup lang="ts">
import { Download, Loader2, MoreVertical } from "lucide-vue-next";
import type { FileNode } from "../../stores/files";
import { formatBytes, formatRelative } from "../../lib/format";
import { kindInfo, kindOf } from "./fileTypes";
import FileName from "./FileName.vue";
import { useFileDownload } from "./useFileDownload";

defineProps<{ items: (FileNode & { location?: string })[]; selectedId: string | null; showLocation?: boolean }>();
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
  <div class="card overflow-hidden">
    <div class="hidden grid-cols-[minmax(0,1fr)_120px_140px_88px] gap-4 border-b border-slate-200 bg-slate-50 px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-slate-500 md:grid">
      <span>Name</span>
      <span>Size</span>
      <span>Modified</span>
      <span class="sr-only">Actions</span>
    </div>
    <ul role="listbox" aria-label="Files and folders">
      <li
        v-for="node in items"
        :key="node.id"
        role="option"
        :aria-selected="selectedId === node.id"
        tabindex="0"
        class="group grid cursor-default grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-slate-100 px-4 py-2.5 last:border-0 md:grid-cols-[minmax(0,1fr)_120px_140px_88px]"
        :class="selectedId === node.id ? 'bg-brand-50' : 'hover:bg-slate-50'"
        @click="emit('select', node)"
        @dblclick="emit('open', node)"
        @keydown.enter="emit('open', node)"
        @contextmenu.prevent="emit('menu', node, $event.clientX, $event.clientY)"
      >
        <div class="flex min-w-0 items-center gap-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" :class="kindInfo(kindOf(node)).tint">
            <component :is="kindInfo(kindOf(node)).icon" class="h-[18px] w-[18px]" :class="{ 'fill-amber-400/30': node.type === 'folder' }" />
          </span>
          <div class="min-w-0">
            <button
              v-if="node.type === 'folder'"
              class="block max-w-full text-left text-sm font-medium text-slate-900 hover:text-brand-700 hover:underline"
              @click.stop="emit('open', node)"
            >
              <FileName :name="node.name" is-folder />
            </button>
            <FileName v-else :name="node.name" class="text-sm font-medium text-slate-900" />
            <p class="truncate text-xs text-slate-500">
              <template v-if="showLocation && node.location">{{ node.location }}</template>
              <template v-else>
                <span class="md:hidden">{{ node.type === "folder" ? "Folder" : formatBytes(node.size_bytes) }} · {{ formatRelative(node.updated_at) }}</span>
                <span class="hidden md:inline">{{ kindInfo(kindOf(node)).label }}</span>
              </template>
            </p>
          </div>
        </div>
        <span class="hidden text-sm text-slate-600 md:block">{{ node.type === "folder" ? "—" : formatBytes(node.size_bytes) }}</span>
        <span class="hidden text-sm text-slate-600 md:block" :title="node.updated_at">{{ formatRelative(node.updated_at) }}</span>
        <div class="flex items-center justify-end gap-1">
          <button
            v-if="node.type === 'file'"
            class="icon-btn"
            :class="{ 'w-auto px-2 text-brand-700': isDownloading(node) }"
            :title="`Download ${node.name}`"
            :aria-label="`Download ${node.name}`"
            :disabled="isDownloading(node)"
            @click.stop="downloadFile(node)"
          >
            <template v-if="isDownloading(node)">
              <Loader2 class="h-4 w-4 animate-spin" /><span class="ml-1 text-xs">{{ progressOf(node) }}%</span>
            </template>
            <Download v-else class="h-4 w-4" />
          </button>
          <button class="icon-btn" title="More actions" :aria-label="`More actions for ${node.name}`" @click.stop="menuFromButton(node, $event)">
            <MoreVertical class="h-4 w-4" />
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

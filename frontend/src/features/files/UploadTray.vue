<script setup lang="ts">
import { useUploadStore } from "../../stores/upload";
import {
  UploadCloud,
  ChevronDown,
  ChevronUp,
  X,
  Pause,
  Play,
  CheckCircle2,
  AlertCircle,
} from "lucide-vue-next";

const uploadStore = useUploadStore();
</script>

<template>
  <div
    v-if="uploadStore.uploads.length > 0"
    class="fixed bottom-6 right-6 w-96 max-w-[calc(100vw-3rem)] z-50 transition-all duration-300"
  >
    <div class="glass-panel rounded-2xl shadow-2xl overflow-hidden border border-slate-700/60 bg-[#0c1427]/95">
      <!-- Header -->
      <div
        class="flex items-center justify-between px-4 py-3 bg-slate-900/80 cursor-pointer border-b border-slate-800/80"
        @click="uploadStore.toggleTray"
      >
        <div class="flex items-center space-x-2.5">
          <UploadCloud class="w-5 h-5 text-brand-400" />
          <span class="text-sm font-semibold text-slate-100">
            Uploads ({{ uploadStore.activeCount }} active)
          </span>
        </div>
        <div class="flex items-center space-x-2 text-slate-400">
          <span v-if="uploadStore.activeCount > 0" class="text-xs font-mono">
            {{ uploadStore.totalProgress }}%
          </span>
          <component
            :is="uploadStore.isTrayOpen ? ChevronDown : ChevronUp"
            class="w-4 h-4 hover:text-white"
          />
        </div>
      </div>

      <!-- Upload Items List -->
      <div v-if="uploadStore.isTrayOpen" class="max-h-80 overflow-y-auto divide-y divide-slate-800/50 p-2">
        <div
          v-for="item in uploadStore.uploads"
          :key="item.id"
          class="p-2.5 hover:bg-slate-800/40 rounded-xl transition-colors space-y-1.5"
        >
          <div class="flex items-center justify-between text-xs">
            <span class="font-medium text-slate-200 truncate max-w-[200px]" :title="item.name">
              {{ item.name }}
            </span>
            <div class="flex items-center space-x-1.5">
              <span v-if="item.status === 'uploading'" class="text-slate-400 font-mono text-[10px]">
                {{ item.speedMBs }} MB/s
              </span>
              <button
                class="p-1 hover:bg-slate-700/50 rounded text-slate-400 hover:text-white"
                @click="uploadStore.cancelUpload(item.id)"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="{
                'bg-brand-500': item.status === 'uploading' || item.status === 'encrypting',
                'bg-emerald-500': item.status === 'completed',
                'bg-rose-500': item.status === 'error',
                'bg-amber-500': item.status === 'paused'
              }"
              :style="{ width: `${item.progress}%` }"
            ></div>
          </div>

          <!-- Status Indicator -->
          <div class="flex items-center justify-between text-[11px] text-slate-400">
            <div class="flex items-center space-x-1">
              <CheckCircle2 v-if="item.status === 'completed'" class="w-3.5 h-3.5 text-emerald-400" />
              <AlertCircle v-else-if="item.status === 'error'" class="w-3.5 h-3.5 text-rose-400" />
              <span class="capitalize">{{ item.status }}</span>
            </div>
            <span>{{ item.progress }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUploadStore } from "../../stores/upload";
import {
  UploadCloud,
  ChevronDown,
  ChevronUp,
  X,
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
    <div class="rounded-2xl shadow-2xl overflow-hidden border border-slate-200 bg-white">
      <!-- Header -->
      <div
        class="flex items-center justify-between px-4 py-3 bg-slate-50 cursor-pointer border-b border-slate-200 select-none hover:bg-slate-100/70 transition-colors"
        @click="uploadStore.toggleTray"
      >
        <div class="flex items-center space-x-2.5">
          <UploadCloud class="w-4 h-4 text-brand-600" />
          <span class="text-xs font-semibold text-slate-900">
            Encrypted Uploads ({{ uploadStore.activeCount }} active)
          </span>
        </div>
        <div class="flex items-center space-x-2 text-slate-500">
          <span v-if="uploadStore.activeCount > 0" class="text-xs font-mono font-bold text-brand-600">
            {{ uploadStore.totalProgress }}%
          </span>
          <component
            :is="uploadStore.isTrayOpen ? ChevronDown : ChevronUp"
            class="w-4 h-4 hover:text-slate-900 transition-colors"
          />
        </div>
      </div>

      <!-- Upload Items List -->
      <div v-if="uploadStore.isTrayOpen" class="max-h-80 overflow-y-auto divide-y divide-slate-100 p-2 space-y-1 bg-white">
        <div
          v-for="item in uploadStore.uploads"
          :key="item.id"
          class="p-2.5 hover:bg-slate-50 rounded-xl transition-colors space-y-1.5"
        >
          <div class="flex items-center justify-between text-xs">
            <span class="font-medium text-slate-800 truncate max-w-[200px]" :title="item.name">
              {{ item.name }}
            </span>
            <div class="flex items-center space-x-2">
              <span v-if="item.status === 'uploading'" class="text-slate-500 font-mono text-[10px]">
                {{ item.speedMBs }} MB/s
              </span>
              <button
                class="p-1 hover:bg-slate-200 rounded-lg text-slate-400 hover:text-slate-700 transition-colors"
                @click="uploadStore.cancelUpload(item.id)"
                title="Cancel upload"
              >
                <X class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="{
                'bg-brand-600': item.status === 'uploading' || item.status === 'encrypting' || item.status === 'completing',
                'bg-emerald-500': item.status === 'completed',
                'bg-rose-500': item.status === 'error',
                'bg-amber-500': item.status === 'paused'
              }"
              :style="{ width: `${item.progress}%` }"
            ></div>
          </div>

          <!-- Status Indicator -->
          <div class="flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <div class="flex items-center space-x-1 max-w-[280px] truncate">
              <CheckCircle2 v-if="item.status === 'completed'" class="w-3 h-3 text-emerald-600 shrink-0" />
              <AlertCircle v-else-if="item.status === 'error'" class="w-3 h-3 text-rose-500 shrink-0" />
              <span
                class="capitalize truncate"
                :class="{ 'text-rose-600 font-medium': item.status === 'error' }"
                :title="item.status === 'error' && item.errorMessage ? item.errorMessage : item.status"
              >
                {{ item.status === 'error' && item.errorMessage ? item.errorMessage : item.status }}
              </span>
            </div>
            <span>{{ item.progress }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

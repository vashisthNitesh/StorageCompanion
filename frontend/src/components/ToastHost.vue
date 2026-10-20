<script setup lang="ts">
import { CheckCircle2, AlertCircle, Info, X } from "lucide-vue-next";
import { useToastStore } from "../stores/toast";

const toast = useToastStore();
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 top-4 z-[60] flex flex-col items-center gap-2 px-4" aria-live="polite">
    <TransitionGroup
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="-translate-y-2 opacity-0"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0"
    >
      <div
        v-for="t in toast.toasts"
        :key="t.id"
        class="pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-xl bg-slate-900 px-4 py-3 text-sm text-white shadow-pop"
        :role="t.tone === 'error' ? 'alert' : 'status'"
      >
        <CheckCircle2 v-if="t.tone === 'success'" class="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
        <AlertCircle v-else-if="t.tone === 'error'" class="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
        <Info v-else class="mt-0.5 h-4 w-4 shrink-0 text-sky-400" />
        <span class="flex-1">{{ t.message }}</span>
        <button class="-mr-1 rounded p-0.5 text-slate-400 hover:text-white" aria-label="Dismiss" @click="toast.dismiss(t.id)">
          <X class="h-4 w-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

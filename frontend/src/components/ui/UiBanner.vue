<script setup lang="ts">
import { computed, type Component } from "vue";
import { Info, AlertTriangle, AlertCircle, CheckCircle2, X } from "lucide-vue-next";

const props = withDefaults(defineProps<{ tone?: "info" | "warning" | "danger" | "success"; dismissible?: boolean; icon?: Component; inline?: boolean }>(), {
  tone: "info",
});
const emit = defineEmits<{ dismiss: [] }>();
const iconFor = computed(() => props.icon ?? { info: Info, warning: AlertTriangle, danger: AlertCircle, success: CheckCircle2 }[props.tone]);
</script>

<template>
  <div
    :role="tone === 'danger' ? 'alert' : 'status'"
    class="flex items-start gap-3 text-base"
    :class="[
      inline ? 'rounded-lg border px-4 py-3' : 'border-b px-4 py-2.5 sm:px-6',
      {
        info: 'border-primary/20 bg-primary-soft text-primary-soft-fg',
        warning: 'border-warning/25 bg-warning-soft text-warning',
        danger: 'border-danger/25 bg-danger-soft text-danger',
        success: 'border-success/25 bg-success-soft text-success',
      }[tone],
    ]"
  >
    <component :is="iconFor" :size="16" :stroke-width="2" class="mt-0.5 shrink-0" aria-hidden="true" />
    <div class="min-w-0 flex-1"><slot /></div>
    <div v-if="$slots.action" class="shrink-0"><slot name="action" /></div>
    <button
      v-if="dismissible"
      type="button"
      class="-mr-1 shrink-0 rounded p-0.5 opacity-70 hover:opacity-100"
      aria-label="Dismiss"
      @click="emit('dismiss')"
    >
      <X :size="16" :stroke-width="2" />
    </button>
  </div>
</template>

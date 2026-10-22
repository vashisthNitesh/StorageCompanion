<script setup lang="ts">
import { computed } from "vue";
import { ChevronLeft, ChevronRight } from "lucide-vue-next";
import UiButton from "./UiButton.vue";

const page = defineModel<number>({ required: true });
const props = defineProps<{ total: number; pageSize: number; label?: string }>();
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));
const from = computed(() => (props.total ? (page.value - 1) * props.pageSize + 1 : 0));
const to = computed(() => Math.min(props.total, page.value * props.pageSize));
</script>

<template>
  <nav v-if="total > pageSize" class="flex items-center justify-between gap-4 text-sm text-fg-muted" :aria-label="label ?? 'Pagination'">
    <span class="tabular">{{ from }}–{{ to }} of {{ total }}</span>
    <div class="flex items-center gap-1">
      <UiButton variant="ghost" size="sm" icon-only :icon="ChevronLeft" aria-label="Previous page" :disabled="page <= 1" @click="page--" />
      <span class="tabular px-2">Page {{ page }} of {{ pages }}</span>
      <UiButton variant="ghost" size="sm" icon-only :icon="ChevronRight" aria-label="Next page" :disabled="page >= pages" @click="page++" />
    </div>
  </nav>
</template>

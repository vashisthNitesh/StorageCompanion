<script setup lang="ts">
import { computed } from "vue";
import { splitFileName } from "../../lib/format";

const props = defineProps<{ name: string; isFolder?: boolean }>();

// Truncate in the middle and keep the end of the name plus the extension visible, so
// IMG_20200130_191233.jpg and IMG_20200130_191240.jpg stay distinguishable.
const parts = computed(() => {
  const { stem, ext } = props.isFolder ? { stem: props.name, ext: "" } : splitFileName(props.name);
  const keep = stem.length > 16 ? 7 : 0;
  return { head: keep ? stem.slice(0, -keep) : stem, tail: (keep ? stem.slice(-keep) : "") + ext };
});
</script>

<template>
  <span class="relative flex min-w-0" :title="name">
    <span class="sr-only">{{ name }}</span>
    <span class="truncate" aria-hidden="true">{{ parts.head }}</span>
    <span v-if="parts.tail" class="shrink-0 whitespace-pre" aria-hidden="true">{{ parts.tail }}</span>
  </span>
</template>

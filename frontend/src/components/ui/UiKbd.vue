<script setup lang="ts">
withDefaults(defineProps<{ tone?: "default" | "inverse" }>(), { tone: "default" });
</script>

<template>
  <kbd
    class="inline-flex h-5 min-w-5 items-center justify-center rounded-sm border px-1 font-sans text-xs font-medium"
    :class="tone === 'inverse' ? 'border-canvas/25 text-canvas/80' : 'border-line bg-canvas-subtle text-fg-muted'"
  ><slot /></kbd>
</template>

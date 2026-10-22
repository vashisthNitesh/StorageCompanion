<script setup lang="ts">
defineProps<{ label: string }>();
</script>

<template>
  <div class="my-6 flex items-center gap-3 text-xs font-medium text-fg-subtle" role="separator">
    <span class="h-px flex-1 bg-line" />
    {{ label }}
    <span class="h-px flex-1 bg-line" />
  </div>
</template>

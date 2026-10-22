<script setup lang="ts">
defineProps<{ class?: string }>();
</script>

<template>
  <span class="skeleton block" :class="$props.class" aria-hidden="true" />
</template>

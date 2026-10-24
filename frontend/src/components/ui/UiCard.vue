<script setup lang="ts">
withDefaults(defineProps<{ padded?: boolean; title?: string; description?: string }>(), { padded: true });
</script>

<template>
  <section class="rounded-lg border border-line bg-surface shadow-xs">
    <div v-if="title || $slots.actions" class="flex flex-col gap-3 px-5 pt-4 sm:flex-row sm:items-start sm:justify-between">
      <div class="min-w-0">
        <h2 v-if="title" class="text-md font-semibold text-fg">{{ title }}</h2>
        <p v-if="description" class="mt-1 text-base text-fg-muted">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 flex-wrap gap-2"><slot name="actions" /></div>
    </div>
    <div :class="padded ? 'px-5 py-4' : ''"><slot /></div>
  </section>
</template>

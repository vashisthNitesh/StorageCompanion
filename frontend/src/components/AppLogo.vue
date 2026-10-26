<script setup lang="ts">
withDefaults(defineProps<{ size?: "sm" | "md" | "lg"; showName?: boolean; tone?: "dark" | "light" }>(), {
  size: "md",
  showName: true,
  tone: "dark",
});
</script>

<template>
  <span class="group inline-flex items-center gap-2.5 select-none">
    <img
      src="/logo.svg"
      :alt="showName ? '' : 'SmartSpace'"
      class="shrink-0 object-contain transition-all duration-300 ease-out group-hover:scale-105 group-hover:drop-shadow-[0_4px_12px_rgb(var(--logo-accent)/0.3)]"
      :class="size === 'sm' ? 'h-7 w-7' : size === 'lg' ? 'h-10 w-10' : 'h-8 w-8'"
    />
    <span
      v-if="showName"
      class="font-bold tracking-tight transition-colors"
      :class="[size === 'lg' ? 'text-xl' : 'text-[17px]', tone === 'light' ? 'text-white' : 'text-fg']"
    >
      Smart<span :class="tone === 'light' ? 'text-[rgb(var(--logo-accent-inverse))]' : 'text-[rgb(var(--logo-accent))]'">Space</span>
    </span>
  </span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: "sm" | "md" | "lg"; showName?: boolean; tone?: "dark" | "light" }>(), {
  size: "md",
  showName: true,
  tone: "dark",
});
</script>

<template>
  <span class="inline-flex items-center gap-2.5">
    <svg
      viewBox="0 0 32 32"
      :class="size === 'sm' ? 'h-7 w-7' : size === 'lg' ? 'h-10 w-10' : 'h-8 w-8'"
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="8" fill="#2563eb" />
      <path d="M22.5 22H11a5 5 0 1 1 .9-9.92A6.5 6.5 0 0 1 24.3 14.6 3.75 3.75 0 0 1 22.5 22Z" fill="#fff" />
      <rect x="14" y="15.5" width="6" height="4.5" rx="1" fill="#2563eb" />
      <path d="M15.2 15.5v-1.2a1.8 1.8 0 0 1 3.6 0v1.2" fill="none" stroke="#2563eb" stroke-width="1.3" />
    </svg>
    <span
      v-if="showName"
      class="font-semibold tracking-tight"
      :class="[size === 'lg' ? 'text-xl' : 'text-[17px]', tone === 'light' ? 'text-white' : 'text-slate-900']"
    >
      SmartSpace
    </span>
  </span>
</template>

<script setup lang="ts">
import type { Component } from "vue";
import { ChevronDown } from "lucide-vue-next";
import UiButton from "./UiButton.vue";
import UiDropdownMenu from "./UiDropdownMenu.vue";
import type { MenuEntry } from "./menuTypes";

withDefaults(
  defineProps<{ label: string; icon?: Component; items: MenuEntry[]; size?: "sm" | "md" | "lg"; block?: boolean; menuLabel?: string; tooltip?: string; shortcut?: string }>(),
  { size: "md", menuLabel: "More options" }
);
const emit = defineEmits<{ click: [] }>();
</script>

<template>
  <div class="inline-flex rounded shadow-xs" :class="{ 'w-full': block }" role="group">
    <UiButton
      variant="primary"
      :size="size"
      :icon="icon"
      class="flex-1 justify-start rounded-r-none shadow-none"
      :tooltip="tooltip"
      :shortcut="shortcut"
      @click="emit('click')"
    >
      {{ label }}
    </UiButton>
    <UiDropdownMenu :items="items" align="start">
      <UiButton
        variant="primary"
        :size="size"
        icon-only
        :icon="ChevronDown"
        :aria-label="menuLabel"
        class="rounded-l-none border-l border-primary-fg/20 shadow-none"
      />
    </UiDropdownMenu>
  </div>
</template>

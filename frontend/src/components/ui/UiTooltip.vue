<script setup lang="ts">
import { TooltipRoot, TooltipTrigger, TooltipPortal, TooltipContent } from "reka-ui";
import UiKbd from "./UiKbd.vue";

withDefaults(
  defineProps<{ content?: string; side?: "top" | "right" | "bottom" | "left"; shortcut?: string; disabled?: boolean }>(),
  { side: "top" }
);
</script>

<template>
  <TooltipRoot v-if="content && !disabled" :delay-duration="300">
    <TooltipTrigger as-child>
      <slot />
    </TooltipTrigger>
    <TooltipPortal>
      <TooltipContent
        :side="side"
        :side-offset="6"
        class="z-[70] flex max-w-xs items-center gap-2 rounded bg-fg px-2.5 py-1.5 text-sm text-canvas shadow-md animate-fade-in"
      >
        {{ content }}
        <UiKbd v-if="shortcut" tone="inverse">{{ shortcut }}</UiKbd>
      </TooltipContent>
    </TooltipPortal>
  </TooltipRoot>
  <slot v-else />
</template>

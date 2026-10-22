<script setup lang="ts">
import {
  DropdownMenuRoot,
  DropdownMenuTrigger,
  DropdownMenuPortal,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "reka-ui";
import UiKbd from "./UiKbd.vue";
import { cn } from "./cn";
import { menuContentClass, menuDangerClass, menuItemClass, type MenuEntry } from "./menuTypes";

withDefaults(defineProps<{ items: MenuEntry[]; align?: "start" | "center" | "end"; side?: "top" | "bottom" | "left" | "right"; contentClass?: string }>(), {
  align: "end",
  side: "bottom",
});
const open = defineModel<boolean>("open", { default: false });
</script>

<template>
  <DropdownMenuRoot v-model:open="open" :modal="false">
    <DropdownMenuTrigger as-child>
      <slot />
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent :align="align" :side="side" :side-offset="6" :class="cn(menuContentClass, contentClass)">
        <slot name="header" />
        <template v-for="(entry, i) in items" :key="i">
          <DropdownMenuSeparator v-if="'separator' in entry" class="my-1 h-px bg-line" />
          <DropdownMenuLabel v-else-if="'heading' in entry" class="px-2.5 pb-1 pt-2 text-xs font-medium text-fg-subtle">
            {{ entry.heading }}
          </DropdownMenuLabel>
          <DropdownMenuItem
            v-else
            :disabled="entry.disabled"
            :class="cn(menuItemClass, entry.danger && menuDangerClass)"
            @select="entry.onSelect"
          >
            <component :is="entry.icon" v-if="entry.icon" :size="16" :stroke-width="1.75" aria-hidden="true" />
            <span class="flex-1">{{ entry.label }}</span>
            <UiKbd v-if="entry.shortcut">{{ entry.shortcut }}</UiKbd>
          </DropdownMenuItem>
        </template>
        <slot name="footer" />
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>

<script setup lang="ts">
import {
  ContextMenuRoot,
  ContextMenuTrigger,
  ContextMenuPortal,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuLabel,
} from "reka-ui";
import UiKbd from "./UiKbd.vue";
import { cn } from "./cn";
import { menuContentClass, menuDangerClass, menuItemClass, type MenuEntry } from "./menuTypes";

defineProps<{ items: MenuEntry[]; disabled?: boolean }>();
const emit = defineEmits<{ open: [] }>();
</script>

<template>
  <ContextMenuRoot :modal="false" @update:open="(o: boolean) => o && emit('open')">
    <ContextMenuTrigger as-child :disabled="disabled">
      <slot />
    </ContextMenuTrigger>
    <ContextMenuPortal>
      <ContextMenuContent :class="menuContentClass">
        <template v-for="(entry, i) in items" :key="i">
          <ContextMenuSeparator v-if="'separator' in entry" class="my-1 h-px bg-line" />
          <ContextMenuLabel v-else-if="'heading' in entry" class="px-2.5 pb-1 pt-2 text-xs font-medium text-fg-subtle">
            {{ entry.heading }}
          </ContextMenuLabel>
          <ContextMenuItem
            v-else
            :disabled="entry.disabled"
            :class="cn(menuItemClass, entry.danger && menuDangerClass)"
            @select="entry.onSelect"
          >
            <component :is="entry.icon" v-if="entry.icon" :size="16" :stroke-width="1.75" aria-hidden="true" />
            <span class="flex-1">{{ entry.label }}</span>
            <UiKbd v-if="entry.shortcut">{{ entry.shortcut }}</UiKbd>
          </ContextMenuItem>
        </template>
      </ContextMenuContent>
    </ContextMenuPortal>
  </ContextMenuRoot>
</template>

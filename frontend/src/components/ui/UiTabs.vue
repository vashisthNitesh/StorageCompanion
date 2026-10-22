<script setup lang="ts">
import type { Component } from "vue";
import { TabsRoot, TabsList, TabsTrigger, TabsIndicator } from "reka-ui";

const model = defineModel<string>({ required: true });
defineProps<{ tabs: { value: string; label: string; icon?: Component }[]; label: string }>();
</script>

<template>
  <TabsRoot v-model="model" activation-mode="manual">
    <TabsList :aria-label="label" class="relative flex gap-6 overflow-x-auto border-b border-line">
      <TabsIndicator class="absolute bottom-0 left-0 h-0.5 w-[--reka-tabs-indicator-size] translate-x-[--reka-tabs-indicator-position] rounded-full bg-primary transition-[width,transform] duration-base ease-out" />
      <TabsTrigger
        v-for="t in tabs"
        :key="t.value"
        :value="t.value"
        class="inline-flex items-center gap-2 whitespace-nowrap pb-3 text-base font-medium text-fg-muted transition-colors hover:text-fg data-[state=active]:text-fg"
      >
        <component :is="t.icon" v-if="t.icon" :size="16" :stroke-width="1.75" aria-hidden="true" />
        {{ t.label }}
      </TabsTrigger>
    </TabsList>
    <slot />
  </TabsRoot>
</template>

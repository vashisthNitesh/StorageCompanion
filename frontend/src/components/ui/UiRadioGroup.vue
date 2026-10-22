<script setup lang="ts">
import { RadioGroupRoot, RadioGroupItem, RadioGroupIndicator } from "reka-ui";

const model = defineModel<string>();
defineProps<{ options: { value: string; label: string; description?: string; disabled?: boolean }[]; label?: string; orientation?: "vertical" | "horizontal" }>();
</script>

<template>
  <RadioGroupRoot v-model="model" :aria-label="label" :orientation="orientation ?? 'vertical'" class="flex gap-3" :class="orientation === 'horizontal' ? 'flex-row flex-wrap' : 'flex-col'">
    <label v-for="o in options" :key="o.value" class="flex cursor-pointer items-start gap-2.5" :class="{ 'opacity-50': o.disabled }">
      <RadioGroupItem
        :value="o.value"
        :disabled="o.disabled"
        class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-line-strong bg-surface shadow-xs hover:border-fg-subtle data-[state=checked]:border-primary"
      >
        <RadioGroupIndicator class="h-2 w-2 rounded-full bg-primary" />
      </RadioGroupItem>
      <span class="text-base leading-5 text-fg">
        {{ o.label }}
        <span v-if="o.description" class="block text-sm text-fg-subtle">{{ o.description }}</span>
      </span>
    </label>
  </RadioGroupRoot>
</template>

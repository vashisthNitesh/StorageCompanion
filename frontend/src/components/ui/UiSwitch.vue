<script setup lang="ts">
import { useId } from "vue";
import { SwitchRoot, SwitchThumb } from "reka-ui";

const model = defineModel<boolean>({ default: false });
const props = defineProps<{ label?: string; description?: string; disabled?: boolean; id?: string }>();
const id = props.id || `sw-${useId()}`;
</script>

<template>
  <div class="flex items-start justify-between gap-4">
    <label v-if="label" :for="id" class="cursor-pointer text-base text-fg">
      {{ label }}
      <span v-if="description" class="block text-sm text-fg-subtle">{{ description }}</span>
    </label>
    <SwitchRoot
      :id="id"
      v-model="model"
      :disabled="disabled"
      class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full bg-line-strong transition-colors duration-fast data-[state=checked]:bg-primary disabled:opacity-50"
    >
      <SwitchThumb class="block h-4 w-4 translate-x-0.5 rounded-full bg-white shadow-sm transition-transform duration-fast ease-out data-[state=checked]:translate-x-[18px]" />
    </SwitchRoot>
  </div>
</template>

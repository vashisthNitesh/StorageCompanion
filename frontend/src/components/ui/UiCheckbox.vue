<script setup lang="ts">
import { useId } from "vue";
import { CheckboxRoot, CheckboxIndicator } from "reka-ui";
import { Check, Minus } from "lucide-vue-next";

const model = defineModel<boolean | "indeterminate">({ default: false });
const props = defineProps<{ label?: string; description?: string; disabled?: boolean; invalid?: boolean; ariaLabel?: string; id?: string }>();
const id = props.id || `cb-${useId()}`;
</script>

<template>
  <div class="flex items-start gap-2.5">
    <CheckboxRoot
      :id="id"
      v-model="model"
      :disabled="disabled"
      :aria-label="label ? undefined : ariaLabel"
      :aria-invalid="invalid || undefined"
      class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border bg-surface shadow-xs transition-colors duration-fast data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=indeterminate]:border-primary data-[state=indeterminate]:bg-primary disabled:cursor-not-allowed disabled:opacity-50"
      :class="invalid ? 'border-danger' : 'border-line-strong hover:border-fg-subtle'"
      @click.stop
    >
      <CheckboxIndicator class="text-primary-fg">
        <Minus v-if="model === 'indeterminate'" :size="12" :stroke-width="3" />
        <Check v-else :size="12" :stroke-width="3" />
      </CheckboxIndicator>
    </CheckboxRoot>
    <label v-if="label || $slots.default" :for="id" class="cursor-pointer select-none text-base leading-5 text-fg">
      <slot>{{ label }}</slot>
      <span v-if="description" class="block text-sm text-fg-subtle">{{ description }}</span>
    </label>
  </div>
</template>

<script setup lang="ts">
import { computed, useId } from "vue";
import { AlertCircle } from "lucide-vue-next";
import { provideFormField } from "./formField";

const props = defineProps<{
  label?: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  optional?: boolean;
  id?: string;
  counter?: { value: number; max: number };
}>();

const id = props.id || `field-${useId()}`;
const hintId = `${id}-hint`;
const errorId = `${id}-error`;
const describedBy = computed(() => [props.error ? errorId : null, props.hint ? hintId : null].filter(Boolean).join(" ") || undefined);
const invalid = computed(() => !!props.error);

provideFormField({ id, describedBy, invalid, required: computed(() => !!props.required) });
</script>

<template>
  <div class="space-y-1.5">
    <div v-if="label || counter" class="flex items-baseline justify-between gap-3">
      <label v-if="label" :for="id" class="text-base font-medium text-fg">
        {{ label }}
        <span v-if="required" class="text-danger" aria-hidden="true">*</span>
        <span v-else-if="optional" class="font-normal text-fg-subtle">(optional)</span>
      </label>
      <span
        v-if="counter"
        class="tabular text-xs"
        :class="counter.value > counter.max ? 'text-danger' : 'text-fg-subtle'"
        aria-live="polite"
      >{{ counter.value }}/{{ counter.max }}</span>
    </div>
    <slot :id="id" :described-by="describedBy" :invalid="invalid" />
    <p v-if="error" :id="errorId" class="flex items-start gap-1.5 text-sm text-danger" role="alert">
      <AlertCircle :size="14" :stroke-width="2" class="mt-0.5 shrink-0" aria-hidden="true" />
      {{ error }}
    </p>
    <p v-else-if="hint" :id="hintId" class="text-sm text-fg-subtle">{{ hint }}</p>
  </div>
</template>

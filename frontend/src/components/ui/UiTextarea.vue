<script setup lang="ts">
import { computed } from "vue";
import { useFormField } from "./formField";
import { cn } from "./cn";

const model = defineModel<string>({ default: "" });
const props = defineProps<{ invalid?: boolean; rows?: number; id?: string }>();
const field = useFormField();
const isInvalid = computed(() => props.invalid || !!field?.invalid.value);
</script>

<template>
  <textarea
    :id="id || field?.id"
    v-model="model"
    :rows="rows ?? 4"
    :aria-invalid="isInvalid || undefined"
    :aria-describedby="field?.describedBy.value"
    :class="
      cn(
        'block w-full rounded border bg-surface px-3 py-2 text-base text-fg shadow-xs placeholder:text-fg-subtle focus:outline-none focus:ring-4',
        isInvalid ? 'border-danger focus:ring-danger/15' : 'border-line-strong focus:border-primary focus:ring-primary/15'
      )
    "
  />
</template>

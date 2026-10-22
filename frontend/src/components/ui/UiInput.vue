<script setup lang="ts">
import { computed, ref, type Component } from "vue";
import { useFormField } from "./formField";
import { inputClasses } from "./inputClasses";

defineOptions({ inheritAttrs: false });
const model = defineModel<string>({ default: "" });
const props = withDefaults(
  defineProps<{ invalid?: boolean; size?: "sm" | "md" | "lg"; icon?: Component; type?: string; id?: string }>(),
  { size: "md", type: "text" }
);
const field = useFormField();
const isInvalid = computed(() => props.invalid || !!field?.invalid.value);
const el = ref<HTMLInputElement | null>(null);
defineExpose({ focus: () => el.value?.focus(), select: () => el.value?.select(), el });
</script>

<template>
  <div class="relative" :class="$attrs.class as string">
    <component
      :is="icon"
      v-if="icon"
      :size="16"
      :stroke-width="1.75"
      class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle"
      aria-hidden="true"
    />
    <input
      :id="id || field?.id"
      ref="el"
      v-model="model"
      v-bind="{ ...$attrs, class: undefined }"
      :type="type"
      :class="inputClasses({ invalid: isInvalid, size, extra: [icon ? 'pl-9' : '', $slots.trailing ? 'pr-10' : ''].join(' ') })"
      :aria-invalid="isInvalid || undefined"
      :aria-describedby="field?.describedBy.value"
      :aria-required="field?.required.value || undefined"
    />
    <div v-if="$slots.trailing" class="absolute inset-y-0 right-1 flex items-center">
      <slot name="trailing" />
    </div>
  </div>
</template>

<script setup lang="ts" generic="T extends string">
import { computed, type Component } from "vue";
import {
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectIcon,
  SelectPortal,
  SelectContent,
  SelectViewport,
  SelectItem,
  SelectItemText,
  SelectItemIndicator,
  ComboboxRoot,
  ComboboxAnchor,
  ComboboxInput,
  ComboboxTrigger,
  ComboboxPortal,
  ComboboxContent,
  ComboboxViewport,
  ComboboxEmpty,
  ComboboxItem,
  ComboboxItemIndicator,
} from "reka-ui";
import { Check, ChevronDown, Search } from "lucide-vue-next";
import { useFormField } from "./formField";
import { inputClasses } from "./inputClasses";
import { cn } from "./cn";

export interface SelectOption<V extends string = string> {
  value: V;
  label: string;
  description?: string;
  icon?: Component;
}

const model = defineModel<T>();
const props = withDefaults(
  defineProps<{
    options: SelectOption<T>[];
    placeholder?: string;
    /** Searchable combobox; defaults to on when there are more than 8 options. */
    searchable?: boolean;
    size?: "sm" | "md" | "lg";
    invalid?: boolean;
    disabled?: boolean;
    ariaLabel?: string;
    id?: string;
    /** Text shown before the value inside the trigger, e.g. "Sort:". */
    prefix?: string;
    triggerClass?: string;
    /** Full-width trigger (forms). Toolbars pass false to size to content. */
    block?: boolean;
  }>(),
  { placeholder: "Select…", size: "md", searchable: undefined, block: true }
);
const emit = defineEmits<{ blur: [] }>();

// Reka Select reserves "" for "no value", so empty-string options are mapped to a sentinel.
const EMPTY = "__empty__";
const inner = computed({
  get: () => (model.value === "" ? EMPTY : (model.value as string | undefined)),
  set: (v) => (model.value = (v === EMPTY ? "" : v) as T),
});
const mapped = computed(() => props.options.map((o) => ({ ...o, key: o.value === "" ? EMPTY : o.value })));
const selected = computed(() => props.options.find((o) => o.value === model.value));
const useCombobox = computed(() => props.searchable ?? props.options.length > 8);

const field = useFormField();
const isInvalid = computed(() => props.invalid || !!field?.invalid.value);
const triggerId = computed(() => props.id || field?.id);
const trigger = computed(() =>
  inputClasses({
    invalid: isInvalid.value,
    size: props.size,
    block: props.block,
    extra: cn(props.block ? "flex" : "", "items-center justify-between gap-2 whitespace-nowrap text-left data-[placeholder]:text-fg-subtle", props.triggerClass),
  })
);
const content =
  "z-[60] max-h-[min(var(--reka-select-content-available-height,320px),320px)] min-w-[var(--reka-select-trigger-width)] overflow-hidden rounded-lg border border-line bg-surface-raised p-1 shadow-md animate-pop-in";
const item =
  "relative flex h-8 cursor-default select-none items-center gap-2 rounded pl-2.5 pr-8 text-base text-fg outline-none data-[disabled]:opacity-50 data-[highlighted]:bg-canvas-subtle";
</script>

<template>
  <!-- Searchable variant (long lists) -->
  <ComboboxRoot
    v-if="useCombobox"
    v-model="inner"
    :disabled="disabled"
    :open-on-click="true"
    :reset-search-term-on-blur="true"
    @update:open="(o: boolean) => !o && emit('blur')"
  >
    <ComboboxAnchor :class="cn(trigger, 'px-0')">
      <Search :size="16" :stroke-width="1.75" class="ml-3 shrink-0 text-fg-subtle" aria-hidden="true" />
      <ComboboxInput
        :id="triggerId"
        class="h-full min-w-0 flex-1 bg-transparent text-fg outline-none placeholder:text-fg-subtle"
        :placeholder="placeholder"
        :display-value="(v: string) => mapped.find((o) => o.key === v)?.label ?? ''"
        :aria-label="ariaLabel"
        :aria-invalid="isInvalid || undefined"
        :aria-describedby="field?.describedBy.value"
      />
      <ComboboxTrigger class="mr-1 flex h-7 w-7 items-center justify-center rounded text-fg-subtle hover:text-fg" aria-label="Show options">
        <ChevronDown :size="16" :stroke-width="1.75" />
      </ComboboxTrigger>
    </ComboboxAnchor>
    <ComboboxPortal>
      <ComboboxContent
        position="popper"
        :side-offset="4"
        class="z-[60] max-h-72 w-[var(--reka-combobox-trigger-width)] overflow-hidden rounded-lg border border-line bg-surface-raised p-1 shadow-md animate-pop-in"
      >
        <ComboboxViewport class="max-h-64 overflow-y-auto scrollbar-thin">
          <ComboboxEmpty class="px-2.5 py-6 text-center text-sm text-fg-subtle">No matches</ComboboxEmpty>
          <ComboboxItem v-for="o in mapped" :key="o.key" :value="o.key" :text-value="o.label" :class="item">
            <component :is="o.icon" v-if="o.icon" :size="16" :stroke-width="1.75" class="text-fg-subtle" />
            {{ o.label }}
            <ComboboxItemIndicator class="absolute right-2.5 text-primary">
              <Check :size="16" :stroke-width="2" />
            </ComboboxItemIndicator>
          </ComboboxItem>
        </ComboboxViewport>
      </ComboboxContent>
    </ComboboxPortal>
  </ComboboxRoot>

  <SelectRoot v-else v-model="inner" :disabled="disabled" @update:open="(o: boolean) => !o && emit('blur')">
    <SelectTrigger
      :id="triggerId"
      :class="trigger"
      :aria-label="ariaLabel"
      :aria-invalid="isInvalid || undefined"
      :aria-describedby="field?.describedBy.value"
    >
      <span class="flex min-w-0 items-center gap-2">
        <span v-if="prefix" class="shrink-0 text-fg-subtle">{{ prefix }}</span>
        <component :is="selected.icon" v-if="selected?.icon" :size="16" :stroke-width="1.75" class="shrink-0 text-fg-subtle" />
        <SelectValue :placeholder="placeholder" class="truncate">{{ selected?.label }}</SelectValue>
      </span>
      <SelectIcon as-child>
        <ChevronDown :size="16" :stroke-width="1.75" class="shrink-0 text-fg-subtle" />
      </SelectIcon>
    </SelectTrigger>
    <SelectPortal>
      <SelectContent position="popper" :side-offset="4" :class="content">
        <SelectViewport>
          <SelectItem v-for="o in mapped" :key="o.key" :value="o.key" :class="cn(item, o.description && 'h-auto py-1.5')">
            <component :is="o.icon" v-if="o.icon" :size="16" :stroke-width="1.75" class="shrink-0 text-fg-subtle" />
            <span class="flex flex-col">
              <SelectItemText>{{ o.label }}</SelectItemText>
              <span v-if="o.description" class="text-xs text-fg-subtle">{{ o.description }}</span>
            </span>
            <SelectItemIndicator class="absolute right-2.5 text-primary">
              <Check :size="16" :stroke-width="2" />
            </SelectItemIndicator>
          </SelectItem>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
  </SelectRoot>
</template>

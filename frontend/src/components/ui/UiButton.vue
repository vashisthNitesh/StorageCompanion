<script setup lang="ts">
import { computed, type Component } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";
import UiSpinner from "./UiSpinner.vue";
import UiTooltip from "./UiTooltip.vue";
import { cn } from "./cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "danger-ghost" | "link";

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    variant?: ButtonVariant;
    size?: "sm" | "md" | "lg";
    type?: "button" | "submit" | "reset";
    icon?: Component;
    iconRight?: Component;
    /** Icon-only button: `ariaLabel` is required and doubles as the tooltip. */
    iconOnly?: boolean;
    ariaLabel?: string;
    tooltip?: string;
    shortcut?: string;
    loading?: boolean;
    disabled?: boolean;
    block?: boolean;
    to?: RouteLocationRaw;
    href?: string;
  }>(),
  { variant: "secondary", size: "md", type: "button" }
);

const tag = computed(() => (props.to ? RouterLink : props.href ? "a" : "button"));
const tooltipText = computed(() => props.tooltip ?? (props.iconOnly ? props.ariaLabel : undefined));

const classes = computed(() =>
  cn(
    "relative inline-flex shrink-0 select-none items-center justify-center gap-2 whitespace-nowrap rounded font-medium",
    "transition-[background-color,border-color,color,box-shadow,transform] duration-fast ease-out active:translate-y-px",
    "disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50",
    props.variant !== "link" &&
      (props.size === "sm" ? "h-8 text-sm" : props.size === "lg" ? "h-11 text-md" : "h-9 text-base"),
    props.variant !== "link" &&
      (props.iconOnly
        ? props.size === "sm" ? "w-8" : props.size === "lg" ? "w-11" : "w-9"
        : props.size === "sm" ? "px-3" : props.size === "lg" ? "px-5" : "px-3.5"),
    {
      primary: "bg-primary text-primary-fg shadow-xs hover:bg-primary-hover",
      secondary: "border border-line bg-surface text-fg shadow-xs hover:border-line-strong hover:bg-canvas-subtle",
      ghost: "text-fg-muted hover:bg-canvas-subtle hover:text-fg",
      danger: "bg-danger text-danger-fg shadow-xs hover:bg-danger-hover",
      "danger-ghost": "text-danger hover:bg-danger-soft",
      link: "h-auto px-0 text-primary underline-offset-4 hover:underline",
    }[props.variant],
    props.block && "w-full"
  )
);
const iconSize = computed(() => (props.size === "lg" ? 18 : 16));
</script>

<template>
  <UiTooltip :content="tooltipText" :shortcut="shortcut">
    <!-- Disabled buttons don't receive pointer events, so wrap them to keep the tooltip working. -->
    <span v-if="disabled && tooltipText" class="inline-flex" tabindex="0" :class="{ 'w-full': block }">
      <component
        :is="tag"
        v-bind="$attrs"
        :type="tag === 'button' ? type : undefined"
        :class="classes"
        disabled
        :aria-label="ariaLabel"
      >
        <span class="inline-flex items-center gap-2">
          <component :is="icon" v-if="icon" :size="iconSize" :stroke-width="1.75" aria-hidden="true" />
          <slot v-if="!iconOnly" />
        </span>
      </component>
    </span>
    <component
      v-else
      :is="tag"
      v-bind="$attrs"
      :to="to"
      :href="href"
      :type="tag === 'button' ? type : undefined"
      :class="classes"
      :disabled="tag === 'button' ? disabled || loading : undefined"
      :aria-disabled="tag !== 'button' && disabled ? 'true' : undefined"
      :aria-label="ariaLabel"
      :aria-busy="loading || undefined"
    >
      <span class="inline-flex items-center gap-2" :class="{ invisible: loading }">
        <component :is="icon" v-if="icon" :size="iconSize" :stroke-width="1.75" aria-hidden="true" />
        <slot v-if="!iconOnly" />
        <component :is="iconRight" v-if="iconRight" :size="iconSize" :stroke-width="1.75" aria-hidden="true" />
      </span>
      <span v-if="loading" class="absolute inset-0 flex items-center justify-center">
        <UiSpinner :size="iconSize" />
      </span>
    </component>
  </UiTooltip>
</template>

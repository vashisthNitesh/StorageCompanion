<script setup lang="ts">
import { computed } from "vue";
import { Sun, Moon, Monitor, Check } from "lucide-vue-next";
import UiButton from "./ui/UiButton.vue";
import UiDropdownMenu from "./ui/UiDropdownMenu.vue";
import UiSegmented from "./ui/UiSegmented.vue";
import type { MenuEntry } from "./ui/menuTypes";
import { useThemeStore, type ThemePreference } from "../stores/theme";

// Light / Dark / System switcher for pages outside the app (website, sign-in).
// "menu" is an icon button with a dropdown; "inline" is a segmented control for mobile menus.
withDefaults(defineProps<{ variant?: "menu" | "inline" }>(), { variant: "menu" });
const theme = useThemeStore();

const OPTIONS: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];
const current = computed(() => OPTIONS.find((o) => o.value === theme.preference) ?? OPTIONS[2]);
const items = computed<MenuEntry[]>(() =>
  OPTIONS.map((o) => ({ label: o.label, icon: theme.preference === o.value ? Check : o.icon, onSelect: () => (theme.preference = o.value) }))
);
</script>

<template>
  <UiDropdownMenu v-if="variant === 'menu'" :items="items" content-class="min-w-[160px]">
    <UiButton variant="ghost" icon-only :icon="current.icon" :aria-label="`Theme: ${current.label}. Change theme`" />
  </UiDropdownMenu>
  <UiSegmented
    v-else
    v-model="theme.preference"
    label="Theme"
    :options="OPTIONS.map((o) => ({ value: o.value, label: o.label, icon: o.icon }))"
  />
</template>

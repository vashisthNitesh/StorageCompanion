<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { Sun, Moon, Monitor, Check, CreditCard, ShieldCheck, Keyboard, LogOut } from "lucide-vue-next";
import UiDropdownMenu from "../components/ui/UiDropdownMenu.vue";
import UiAvatar from "../components/ui/UiAvatar.vue";
import UiBadge from "../components/ui/UiBadge.vue";
import type { MenuEntry } from "../components/ui/menuTypes";
import { useAuthStore } from "../stores/auth";
import { useThemeStore, type ThemePreference } from "../stores/theme";
import { emitAppEvent } from "../lib/events";

const emit = defineEmits<{ signOut: [] }>();
const router = useRouter();
const authStore = useAuthStore();
const theme = useThemeStore();
const user = computed(() => authStore.user);

const themeItem = (value: ThemePreference, label: string, icon: any): MenuEntry => ({
  label,
  icon: theme.preference === value ? Check : icon,
  onSelect: () => (theme.preference = value),
});

const items = computed<MenuEntry[]>(() => [
  { heading: "Theme" },
  themeItem("light", "Light", Sun),
  themeItem("dark", "Dark", Moon),
  themeItem("system", "System", Monitor),
  { separator: true },
  ...(!authStore.isMasterAdmin ? [{ label: "Plan & billing", icon: CreditCard, onSelect: () => router.push("/app/billing") }] : []),
  { label: "Security", icon: ShieldCheck, onSelect: () => router.push("/app/settings") },
  { label: "Keyboard shortcuts", icon: Keyboard, shortcut: "?", onSelect: () => emitAppEvent("shortcuts-help") },
  { separator: true },
  { label: "Sign out", icon: LogOut, onSelect: () => emit("signOut") },
]);
</script>

<template>
  <UiDropdownMenu :items="items" content-class="w-64">
    <button type="button" class="flex items-center rounded-full p-0.5 hover:ring-4 hover:ring-canvas-subtle" aria-label="Account menu">
      <UiAvatar :name="user?.full_name" :email="user?.email" />
    </button>
    <template #header>
      <div class="flex items-center gap-3 px-2.5 py-2">
        <UiAvatar :name="user?.full_name" :email="user?.email" size="lg" />
        <div class="min-w-0">
          <p class="truncate text-base font-medium text-fg">{{ user?.full_name || "Your account" }}</p>
          <p class="truncate text-sm text-fg-muted">{{ user?.email }}</p>
          <UiBadge v-if="authStore.isMasterAdmin" tone="primary" class="mt-1">Administrator</UiBadge>
        </div>
      </div>
      <div class="my-1 h-px bg-line" />
    </template>
  </UiDropdownMenu>
</template>

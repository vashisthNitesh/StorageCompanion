<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { Folder, Clock, Trash2, CreditCard, ShieldCheck, LayoutDashboard, Upload, FolderUp, FolderPlus, PanelLeftClose, PanelLeftOpen } from "lucide-vue-next";
import AppLogo from "../components/AppLogo.vue";
import UiSplitButton from "../components/ui/UiSplitButton.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiDropdownMenu from "../components/ui/UiDropdownMenu.vue";
import UiTooltip from "../components/ui/UiTooltip.vue";
import StorageCard from "./StorageCard.vue";
import type { MenuEntry } from "../components/ui/menuTypes";
import { useAuthStore } from "../stores/auth";
import { emitAppEvent } from "../lib/events";

const props = defineProps<{ collapsed: boolean; collapsible: boolean }>();
const emit = defineEmits<{ toggle: []; navigate: [] }>();
const route = useRoute();
const authStore = useAuthStore();

const isCustomer = computed(() => !authStore.isMasterAdmin);
const primaryNav = computed(() =>
  isCustomer.value
    ? [
        { to: "/app/files", label: "My files", icon: Folder },
        { to: "/app/recent", label: "Recent", icon: Clock },
        { to: "/app/trash", label: "Trash", icon: Trash2 },
      ]
    : [{ to: "/app/admin", label: "Admin console", icon: LayoutDashboard }]
);
const secondaryNav = computed(() =>
  isCustomer.value
    ? [
        { to: "/app/billing", label: "Plan & billing", icon: CreditCard },
        { to: "/app/settings", label: "Security", icon: ShieldCheck },
      ]
    : [{ to: "/app/settings", label: "Security", icon: ShieldCheck }]
);

const uploadItems: MenuEntry[] = [
  { label: "Upload files", icon: Upload, shortcut: "U", onSelect: () => emitAppEvent("upload-files") },
  { label: "Upload folder", icon: FolderUp, onSelect: () => emitAppEvent("upload-folder") },
  { separator: true },
  { label: "New folder", icon: FolderPlus, shortcut: "N", onSelect: () => emitAppEvent("new-folder") },
];

const isActive = (to: string) => route.path === to || route.path.startsWith(`${to}/`);
const linkClass = (to: string) =>
  [
    "group relative flex h-9 items-center gap-3 rounded text-base font-medium transition-colors duration-fast",
    props.collapsed ? "justify-center px-0" : "px-3",
    isActive(to) ? "bg-primary-soft text-primary-soft-fg" : "text-fg-muted hover:bg-canvas-subtle hover:text-fg",
  ].join(" ");
</script>

<template>
  <div class="flex h-full flex-col bg-surface">
    <div class="flex h-14 shrink-0 items-center px-4" :class="collapsed ? 'justify-center px-0' : 'justify-between'">
      <router-link :to="isCustomer ? '/app/files' : '/app/admin'" aria-label="SmartSpace home" @click="emit('navigate')">
        <AppLogo :show-name="!collapsed" size="sm" />
      </router-link>
      <UiButton
        v-if="collapsible && !collapsed"
        variant="ghost"
        size="sm"
        icon-only
        :icon="PanelLeftClose"
        aria-label="Collapse sidebar"
        @click="emit('toggle')"
      />
    </div>

    <div v-if="isCustomer" class="px-3 pb-2 pt-1">
      <UiDropdownMenu v-if="collapsed" :items="uploadItems" side="right" align="start">
        <UiButton variant="primary" icon-only :icon="Upload" aria-label="Upload or create" class="mx-auto flex" />
      </UiDropdownMenu>
      <UiSplitButton v-else block label="Upload" :icon="Upload" :items="uploadItems" menu-label="More upload options" @click="emitAppEvent('upload-files')" />
    </div>

    <nav class="flex-1 overflow-y-auto px-3 py-2 scrollbar-thin" aria-label="Main">
      <ul class="space-y-0.5">
        <li v-for="item in primaryNav" :key="item.to">
          <UiTooltip :content="collapsed ? item.label : undefined" side="right">
            <router-link :to="item.to" :class="linkClass(item.to)" :aria-current="isActive(item.to) ? 'page' : undefined" @click="emit('navigate')">
              <span v-if="isActive(item.to)" class="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary" aria-hidden="true" />
              <component :is="item.icon" :size="20" :stroke-width="1.75" aria-hidden="true" />
              <span v-if="!collapsed">{{ item.label }}</span>
              <span v-else class="sr-only">{{ item.label }}</span>
            </router-link>
          </UiTooltip>
        </li>
      </ul>
      <div class="my-3 h-px bg-line" role="separator" />
      <ul class="space-y-0.5">
        <li v-for="item in secondaryNav" :key="item.to">
          <UiTooltip :content="collapsed ? item.label : undefined" side="right">
            <router-link :to="item.to" :class="linkClass(item.to)" :aria-current="isActive(item.to) ? 'page' : undefined" @click="emit('navigate')">
              <span v-if="isActive(item.to)" class="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary" aria-hidden="true" />
              <component :is="item.icon" :size="20" :stroke-width="1.75" aria-hidden="true" />
              <span v-if="!collapsed">{{ item.label }}</span>
              <span v-else class="sr-only">{{ item.label }}</span>
            </router-link>
          </UiTooltip>
        </li>
      </ul>
    </nav>

    <div v-if="isCustomer" class="shrink-0 p-3">
      <StorageCard :compact="collapsed" />
    </div>
    <div v-if="collapsible && collapsed" class="shrink-0 pb-3 text-center">
      <UiButton variant="ghost" size="sm" icon-only :icon="PanelLeftOpen" aria-label="Expand sidebar" @click="emit('toggle')" />
    </div>
  </div>
</template>

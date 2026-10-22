<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch, type Component } from "vue";
import { useRouter } from "vue-router";
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription } from "reka-ui";
import {
  Search,
  Upload,
  FolderUp,
  FolderPlus,
  Folder,
  Clock,
  Trash2,
  CreditCard,
  KeyRound,
  ShieldCheck,
  SunMoon,
  Keyboard,
  LogOut,
  CornerDownLeft,
  FileSearch,
} from "lucide-vue-next";
import UiKbd from "./ui/UiKbd.vue";
import UiSpinner from "./ui/UiSpinner.vue";
import { useFilesStore, type SearchResult } from "../stores/files";
import { useAuthStore } from "../stores/auth";
import { useThemeStore } from "../stores/theme";
import { emitAppEvent, onAppEvent } from "../lib/events";
import { kindInfo, kindOf } from "../features/files/fileTypes";

const emit = defineEmits<{ signOut: [] }>();
const router = useRouter();
const filesStore = useFilesStore();
const authStore = useAuthStore();
const theme = useThemeStore();

const open = ref(false);
const query = ref("");
const active = ref(0);
const results = ref<SearchResult[]>([]);
const searching = ref(false);
const input = ref<HTMLInputElement | null>(null);
const list = ref<HTMLElement | null>(null);

interface Item {
  id: string;
  group: string;
  label: string;
  hint?: string;
  icon: Component;
  iconClass?: string;
  shortcut?: string;
  run: () => void;
}

const actions = computed<Item[]>(() => {
  const customer = !authStore.isMasterAdmin;
  const go = (path: string) => () => router.push(path);
  const list: Item[] = [];
  if (customer) {
    list.push(
      { id: "a-upload", group: "Actions", label: "Upload files", icon: Upload, shortcut: "U", run: () => emitAppEvent("upload-files") },
      { id: "a-upload-folder", group: "Actions", label: "Upload folder", icon: FolderUp, run: () => emitAppEvent("upload-folder") },
      { id: "a-new-folder", group: "Actions", label: "New folder", icon: FolderPlus, shortcut: "N", run: () => emitAppEvent("new-folder") },
      { id: "n-files", group: "Go to", label: "My files", icon: Folder, run: go("/app/files") },
      { id: "n-recent", group: "Go to", label: "Recent", icon: Clock, run: go("/app/recent") },
      { id: "n-trash", group: "Go to", label: "Trash", icon: Trash2, run: go("/app/trash") },
      { id: "n-billing", group: "Go to", label: "Plan & billing", icon: CreditCard, run: go("/app/billing") }
    );
  }
  list.push(
    { id: "s-password", group: "Settings", label: "Change password", icon: KeyRound, run: go("/app/settings#password") },
    { id: "s-2fa", group: "Settings", label: "Two-step verification", icon: ShieldCheck, run: go("/app/settings#two-step") },
    {
      id: "s-theme",
      group: "Settings",
      label: `Switch to ${theme.preference === "dark" ? "light" : "dark"} theme`,
      icon: SunMoon,
      run: () => (theme.preference = theme.preference === "dark" ? "light" : "dark"),
    },
    { id: "s-keys", group: "Settings", label: "Keyboard shortcuts", icon: Keyboard, shortcut: "?", run: () => emitAppEvent("shortcuts-help") },
    { id: "s-signout", group: "Settings", label: "Sign out", icon: LogOut, run: () => emit("signOut") }
  );
  return list;
});

const items = computed<Item[]>(() => {
  const q = query.value.trim().toLowerCase();
  const matchedActions = q ? actions.value.filter((a) => a.label.toLowerCase().includes(q)) : actions.value;
  const fileItems: Item[] = results.value.map((n) => ({
    id: `f-${n.id}`,
    group: "Files and folders",
    label: n.name,
    hint: n.location,
    icon: kindInfo(kindOf(n)).icon,
    iconClass: kindInfo(kindOf(n)).tint,
    run: () => {
      router.push("/app/files");
      if (n.type === "folder") void filesStore.openFolderFromSearch(n.id);
      else void filesStore.revealNode(n);
    },
  }));
  const searchAll: Item[] =
    q && !authStore.isMasterAdmin
      ? [
          {
            id: "search-all",
            group: "Files and folders",
            label: `Search all files for “${query.value.trim()}”`,
            icon: FileSearch,
            run: () => {
              router.push("/app/files");
              void filesStore.search(query.value.trim());
            },
          },
        ]
      : [];
  return [...fileItems, ...searchAll, ...matchedActions];
});

const groups = computed(() => {
  const map = new Map<string, Item[]>();
  for (const item of items.value) map.set(item.group, [...(map.get(item.group) ?? []), item]);
  return [...map.entries()];
});

let seq = 0;
let timer: ReturnType<typeof setTimeout> | undefined;
watch(query, (q) => {
  active.value = 0;
  clearTimeout(timer);
  if (!q.trim() || authStore.isMasterAdmin || !authStore.masterKey) {
    results.value = [];
    searching.value = false;
    return;
  }
  searching.value = true;
  const mine = ++seq;
  timer = setTimeout(async () => {
    try {
      const found = await filesStore.findNodes(q, 8);
      if (mine === seq) results.value = found;
    } catch {
      if (mine === seq) results.value = [];
    } finally {
      if (mine === seq) searching.value = false;
    }
  }, 150);
});

function run(item: Item | undefined) {
  if (!item) return;
  open.value = false;
  item.run();
}

function onKey(e: KeyboardEvent) {
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const n = items.value.length;
    if (!n) return;
    active.value = (active.value + (e.key === "ArrowDown" ? 1 : -1) + n) % n;
    nextTick(() => list.value?.querySelector(`[data-index="${active.value}"]`)?.scrollIntoView({ block: "nearest" }));
  } else if (e.key === "Enter") {
    e.preventDefault();
    run(items.value[active.value]);
  }
}

let off: (() => void) | null = null;
onMounted(() => {
  off = onAppEvent("command-palette", () => {
    query.value = "";
    results.value = [];
    open.value = true;
  });
});
onUnmounted(() => off?.());
</script>

<template>
  <DialogRoot v-model:open="open">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-overlay/40 data-[state=open]:animate-fade-in" />
      <DialogContent
        class="fixed left-1/2 top-[10vh] z-50 flex max-h-[70vh] w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 flex-col overflow-hidden rounded-xl border border-line bg-surface-raised shadow-xl focus:outline-none data-[state=open]:animate-scale-in"
        @open-auto-focus.prevent="input?.focus()"
      >
        <DialogTitle class="sr-only">Search and commands</DialogTitle>
        <DialogDescription class="sr-only">Type to search files, folders and actions. Use the arrow keys and Enter.</DialogDescription>
        <div class="flex items-center gap-3 border-b border-line px-4">
          <Search :size="18" :stroke-width="1.75" class="shrink-0 text-fg-subtle" aria-hidden="true" />
          <input
            ref="input"
            v-model="query"
            class="h-12 flex-1 bg-transparent text-md text-fg outline-none placeholder:text-fg-subtle"
            placeholder="Search files, folders and actions"
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-list"
            :aria-activedescendant="items[active] ? `palette-${items[active].id}` : undefined"
            @keydown="onKey"
          />
          <UiSpinner v-if="searching" :size="16" class="text-fg-subtle" />
          <UiKbd>Esc</UiKbd>
        </div>
        <div id="palette-list" ref="list" role="listbox" class="min-h-0 flex-1 overflow-y-auto p-2 scrollbar-thin">
          <p v-if="!items.length" class="px-3 py-10 text-center text-base text-fg-muted">No results for “{{ query }}”</p>
          <template v-for="[group, groupItems] in groups" :key="group">
            <p class="px-2.5 pb-1 pt-2 text-xs font-medium text-fg-subtle">{{ group }}</p>
            <div
              v-for="item in groupItems"
              :id="`palette-${item.id}`"
              :key="item.id"
              role="option"
              :data-index="items.indexOf(item)"
              :aria-selected="items.indexOf(item) === active"
              class="flex cursor-default items-center gap-3 rounded px-2.5 py-2"
              :class="items.indexOf(item) === active ? 'bg-canvas-subtle' : ''"
              @mousemove="active = items.indexOf(item)"
              @click="run(item)"
            >
              <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded" :class="item.iconClass ?? 'text-fg-muted'">
                <component :is="item.icon" :size="16" :stroke-width="1.75" aria-hidden="true" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-base text-fg">{{ item.label }}</span>
                <span v-if="item.hint" class="block truncate text-xs text-fg-subtle">{{ item.hint }}</span>
              </span>
              <UiKbd v-if="item.shortcut">{{ item.shortcut }}</UiKbd>
              <CornerDownLeft v-else-if="items.indexOf(item) === active" :size="14" class="text-fg-subtle" aria-hidden="true" />
            </div>
          </template>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

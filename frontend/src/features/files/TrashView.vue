<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RotateCcw, Trash2, CloudOff, MoreHorizontal, X } from "lucide-vue-next";
import UiPageHeader from "../../components/ui/UiPageHeader.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiEmptyState from "../../components/ui/UiEmptyState.vue";
import UiDropdownMenu from "../../components/ui/UiDropdownMenu.vue";
import UiTooltip from "../../components/ui/UiTooltip.vue";
import type { MenuEntry } from "../../components/ui/menuTypes";
import { useAuthStore } from "../../stores/auth";
import { useFilesStore, type FileNode } from "../../stores/files";
import { confirmDialog } from "../../lib/confirm";
import { normalizeApiError } from "../../lib/errors";
import { reportError } from "../../lib/reportError";
import { toast } from "../../lib/toast";
import { formatBytes, formatDateTime, formatRelative } from "../../lib/format";
import { useMediaQuery } from "../../composables/useMediaQuery";
import { kindInfo, kindOf } from "./fileTypes";
import FileName from "./FileName.vue";

const authStore = useAuthStore();
const files = useFilesStore();
const isWide = useMediaQuery("(min-width: 768px)");

const items = ref<FileNode[]>([]);
const loading = ref(true);
const error = ref<unknown>(null);
const selected = ref<Set<string>>(new Set());

const sorted = computed(() => [...items.value].sort((a, b) => new Date(b.trashed_at ?? 0).getTime() - new Date(a.trashed_at ?? 0).getTime()));
const selectedNodes = computed(() => sorted.value.filter((n) => selected.value.has(n.id)));
const allState = computed<boolean | "indeterminate">(() =>
  !selected.value.size ? false : selected.value.size === items.value.length ? true : "indeterminate"
);
const plural = (n: number, one: string) => `${n} ${n === 1 ? one : `${one}s`}`;

async function load() {
  if (!authStore.masterKey) return;
  loading.value = true;
  error.value = null;
  try {
    items.value = await files.fetchTrash();
  } catch (err) {
    error.value = err;
  } finally {
    loading.value = false;
  }
}

function toggle(node: FileNode) {
  const next = new Set(selected.value);
  if (next.has(node.id)) next.delete(node.id);
  else next.add(node.id);
  selected.value = next;
}
function toggleAll() {
  selected.value = selected.value.size === items.value.length ? new Set() : new Set(items.value.map((n) => n.id));
}

async function restore(nodes: FileNode[]) {
  const results = await Promise.allSettled(nodes.map((n) => files.restoreNode(n)));
  const done = nodes.filter((_, i) => results[i].status === "fulfilled");
  items.value = items.value.filter((n) => !done.includes(n));
  selected.value = new Set([...selected.value].filter((id) => !done.some((n) => n.id === id)));
  if (done.length) {
    const label = done.length === 1 ? `“${done[0].name}” restored` : `${plural(done.length, "item")} restored`;
    toast.undoable(label, async () => {
      const again = await Promise.allSettled(done.map((n) => files.trashNode(n)));
      items.value = [...items.value, ...done.filter((_, i) => again[i].status === "fulfilled")];
    });
  }
  const failed = results.find((r): r is PromiseRejectedResult => r.status === "rejected");
  if (failed) {
    const n = reportError(failed.reason);
    if (n.kind === "not_found") void load();
  }
}

async function deleteNodes(nodes: FileNode[]) {
  for (const node of nodes) {
    await files.permanentDeleteNode(node.id);
    items.value = items.value.filter((n) => n.id !== node.id);
  }
  selected.value = new Set();
}

async function deleteForever(nodes: FileNode[]) {
  const one = nodes.length === 1;
  const ok = await confirmDialog({
    title: one ? `Delete “${nodes[0].name}” forever?` : `Delete ${nodes.length} items forever?`,
    body: one
      ? nodes[0].type === "folder"
        ? "This folder and everything in it will be permanently deleted. This can't be undone."
        : "This file will be permanently deleted. This can't be undone."
      : "These items will be permanently deleted. This can't be undone.",
    confirmLabel: one ? "Delete forever" : `Delete ${nodes.length} items`,
    danger: true,
    typeToConfirm: one ? undefined : "delete",
    action: () => deleteNodes(nodes),
  });
  if (ok) toast.success(one ? `“${nodes[0].name}” deleted forever` : `${nodes.length} items deleted forever`);
}

async function emptyTrash() {
  const all = [...items.value];
  const ok = await confirmDialog({
    title: "Empty trash?",
    body: `${plural(all.length, "item")} will be permanently deleted. This can't be undone.`,
    confirmLabel: `Delete ${plural(all.length, "item")}`,
    danger: true,
    typeToConfirm: all.length > 1 ? "delete" : undefined,
    action: () => deleteNodes(all),
  });
  if (ok) toast.success("Trash emptied");
}

function menuFor(node: FileNode): MenuEntry[] {
  return [
    { label: "Restore", icon: RotateCcw, onSelect: () => void restore([node]) },
    { separator: true },
    { label: "Delete forever", icon: Trash2, danger: true, onSelect: () => void deleteForever([node]) },
  ];
}

onMounted(load);
watch(() => authStore.masterKey, (k) => k && load());
</script>

<template>
  <div>
    <UiPageHeader title="Trash" description="Deleted items don't count towards your storage. They stay here until you restore them or delete them forever.">
      <template #actions>
        <UiButton v-if="items.length" variant="danger-ghost" :icon="Trash2" @click="emptyTrash">Empty trash</UiButton>
      </template>
    </UiPageHeader>

    <div class="mt-6">
      <div v-if="!authStore.masterKey || loading" class="overflow-hidden rounded-lg border border-line bg-surface" aria-busy="true" aria-label="Loading trash">
        <div class="h-10 border-b border-line bg-surface-sunken" />
        <div v-for="i in 5" :key="i" class="flex h-11 items-center gap-3 border-b border-line px-3 last:border-0">
          <UiSkeleton class="h-4 w-4" />
          <UiSkeleton class="h-8 w-8" />
          <UiSkeleton class="h-3.5 w-1/3" />
          <UiSkeleton class="ml-auto hidden h-3 w-20 md:block" />
        </div>
      </div>

      <div v-else-if="error" class="rounded-lg border border-line bg-surface">
        <UiEmptyState :icon="CloudOff" tone="danger" title="Couldn't load the trash" :description="normalizeApiError(error).message">
          <UiButton @click="load">Try again</UiButton>
        </UiEmptyState>
      </div>

      <div v-else-if="!items.length" class="rounded-lg border border-dashed border-line-strong bg-surface">
        <UiEmptyState :icon="Trash2" tone="neutral" title="Trash is empty" description="Items you delete appear here." />
      </div>

      <div v-else class="overflow-hidden rounded-lg border border-line bg-surface">
        <div
          class="grid h-10 items-center gap-3 border-b border-line bg-surface-sunken px-3 text-sm font-medium text-fg-muted"
          :class="isWide ? 'grid-cols-[24px_minmax(0,1fr)_160px_96px_200px]' : 'grid-cols-[24px_minmax(0,1fr)_40px]'"
        >
          <UiCheckbox :model-value="allState" aria-label="Select all" @update:model-value="toggleAll" />
          <span>Name</span>
          <template v-if="isWide">
            <span>Deleted</span>
            <span class="justify-self-end">Size</span>
            <span class="sr-only">Actions</span>
          </template>
        </div>
        <ul aria-label="Items in trash">
          <li
            v-for="node in sorted"
            :key="node.id"
            class="group grid min-h-11 items-center gap-3 border-b border-line px-3 py-1.5 last:border-0"
            :class="[isWide ? 'grid-cols-[24px_minmax(0,1fr)_160px_96px_200px]' : 'grid-cols-[24px_minmax(0,1fr)_40px]', selected.has(node.id) ? 'bg-primary-soft/70' : 'hover:bg-canvas-subtle']"
          >
            <UiCheckbox :model-value="selected.has(node.id)" :aria-label="`Select ${node.name}`" @update:model-value="toggle(node)" />
            <div class="flex min-w-0 items-center gap-3">
              <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded" :class="kindInfo(kindOf(node)).tint">
                <component :is="kindInfo(kindOf(node)).icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
              </span>
              <div class="min-w-0">
                <FileName :name="node.name" :is-folder="node.type === 'folder'" class="text-base text-fg" />
                <p v-if="!isWide" class="tabular truncate text-xs text-fg-subtle">Deleted {{ formatRelative(node.trashed_at) }}</p>
                <p v-else-if="node.type === 'folder'" class="text-xs text-fg-subtle">Folder and its contents</p>
              </div>
            </div>
            <template v-if="isWide">
              <UiTooltip :content="formatDateTime(node.trashed_at)">
                <span class="tabular justify-self-start text-sm text-fg-muted">{{ formatRelative(node.trashed_at) }}</span>
              </UiTooltip>
              <span class="tabular justify-self-end text-sm text-fg-muted">{{ node.type === "folder" ? "—" : formatBytes(node.size_bytes) }}</span>
              <div class="flex justify-end gap-1">
                <UiButton size="sm" variant="ghost" :icon="RotateCcw" :aria-label="`Restore ${node.name}`" @click="restore([node])">Restore</UiButton>
                <UiButton size="sm" variant="danger-ghost" :icon="Trash2" :aria-label="`Delete ${node.name} forever`" @click="deleteForever([node])">Delete</UiButton>
              </div>
            </template>
            <UiDropdownMenu v-else :items="menuFor(node)">
              <UiButton variant="ghost" size="sm" icon-only :icon="MoreHorizontal" :aria-label="`Actions for ${node.name}`" />
            </UiDropdownMenu>
          </li>
        </ul>
      </div>
    </div>

    <Transition enter-active-class="animate-slide-up" leave-active-class="animate-fade-out">
      <div
        v-if="selected.size"
        class="fixed inset-x-0 bottom-0 z-30 flex items-center gap-1 border-t border-line bg-surface-raised px-3 py-2 shadow-xl sm:inset-x-auto sm:bottom-6 sm:left-1/2 sm:-translate-x-1/2 sm:rounded-xl sm:border"
        role="toolbar"
        aria-label="Selection actions"
      >
        <span class="tabular px-2 text-base font-medium text-fg" aria-live="polite">{{ selected.size }} selected</span>
        <span class="mx-1 h-5 w-px bg-line" aria-hidden="true" />
        <UiButton variant="ghost" size="sm" :icon="RotateCcw" @click="restore(selectedNodes)">Restore</UiButton>
        <UiButton variant="danger-ghost" size="sm" :icon="Trash2" @click="deleteForever(selectedNodes)">Delete forever</UiButton>
        <span class="mx-1 h-5 w-px bg-line" aria-hidden="true" />
        <UiButton variant="ghost" size="sm" icon-only :icon="X" aria-label="Clear selection" @click="selected = new Set()" />
      </div>
    </Transition>
  </div>
</template>

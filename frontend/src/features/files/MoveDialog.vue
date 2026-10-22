<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { ChevronRight, Folder, FolderPlus, Home } from "lucide-vue-next";
import UiModal from "../../components/ui/UiModal.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { useFilesStore, type FileNode } from "../../stores/files";
import { normalizeApiError } from "../../lib/errors";

const open = defineModel<boolean>("open", { default: false });
const props = defineProps<{ nodes: FileNode[] }>();
const emit = defineEmits<{ move: [destination: { id: string | null; name: string }] }>();
const files = useFilesStore();

const folders = ref<FileNode[]>([]);
const loading = ref(false);
const loadError = ref("");
const target = ref<string | null>(null);
const expanded = ref<Set<string>>(new Set());
const creating = ref(false);
const newName = ref("");
const newError = ref("");
const creatingBusy = ref(false);

// Moving a folder into itself or its own subfolders isn't allowed.
const blocked = computed(() => {
  const ids = new Set(props.nodes.filter((n) => n.type === "folder").map((n) => n.id));
  let grew = true;
  while (grew) {
    grew = false;
    for (const f of folders.value) {
      if (f.parent && ids.has(f.parent) && !ids.has(f.id)) {
        ids.add(f.id);
        grew = true;
      }
    }
  }
  return ids;
});
const children = computed(() => {
  const map = new Map<string | null, FileNode[]>();
  for (const f of folders.value) {
    if (blocked.value.has(f.id)) continue;
    map.set(f.parent, [...(map.get(f.parent) ?? []), f]);
  }
  for (const list of map.values()) list.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  return map;
});
const byId = computed(() => new Map(folders.value.map((f) => [f.id, f])));
const rows = computed(() => {
  const out: { node: FileNode; depth: number; hasChildren: boolean }[] = [];
  const walk = (parent: string | null, depth: number) => {
    for (const f of children.value.get(parent) ?? []) {
      const hasChildren = !!children.value.get(f.id)?.length;
      out.push({ node: f, depth, hasChildren });
      if (expanded.value.has(f.id)) walk(f.id, depth + 1);
    }
  };
  walk(null, 1);
  return out;
});
const path = computed(() => {
  const parts: string[] = [];
  let id = target.value;
  while (id) {
    const f = byId.value.get(id);
    if (!f) break;
    parts.unshift(f.name);
    id = f.parent;
  }
  return ["My files", ...parts];
});
const currentParent = computed(() => (props.nodes.every((n) => n.parent === props.nodes[0]?.parent) ? props.nodes[0]?.parent ?? null : undefined));
const title = computed(() => (props.nodes.length === 1 ? `Move “${props.nodes[0].name}”` : `Move ${props.nodes.length} items`));

watch(open, async (o) => {
  if (!o) return;
  target.value = props.nodes[0]?.parent ?? null;
  creating.value = false;
  loadError.value = "";
  loading.value = true;
  try {
    folders.value = await files.folderTree();
    // Expand the path to the current folder.
    const ex = new Set<string>();
    let id = target.value;
    while (id) {
      const f = folders.value.find((x) => x.id === id);
      if (!f?.parent) break;
      ex.add(f.parent);
      id = f.parent;
    }
    expanded.value = ex;
  } catch (err) {
    loadError.value = normalizeApiError(err).message;
  } finally {
    loading.value = false;
  }
});

function toggle(id: string) {
  const next = new Set(expanded.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expanded.value = next;
}

function onTreeKey(e: KeyboardEvent, row: { node: FileNode; hasChildren: boolean }) {
  if (e.key === "ArrowRight" && row.hasChildren && !expanded.value.has(row.node.id)) toggle(row.node.id);
  else if (e.key === "ArrowLeft" && expanded.value.has(row.node.id)) toggle(row.node.id);
  else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const items = Array.from(document.querySelectorAll<HTMLElement>("[data-tree-item]"));
    const i = items.indexOf(e.currentTarget as HTMLElement);
    items[i + (e.key === "ArrowDown" ? 1 : -1)]?.focus();
  }
}

async function startCreate() {
  creating.value = true;
  newName.value = "";
  newError.value = "";
  await nextTick();
  (document.getElementById("move-new-folder") as HTMLInputElement | null)?.focus();
}

async function createHere() {
  const name = newName.value.trim();
  if (!name) return (newError.value = "Enter a folder name.");
  if (/[\\/]/.test(name)) return (newError.value = "Names can't contain / or \\.");
  if (folders.value.some((f) => f.parent === target.value && f.name.toLowerCase() === name.toLowerCase())) {
    return (newError.value = "A folder with this name already exists here.");
  }
  creatingBusy.value = true;
  try {
    const created = await files.createFolder(name, target.value);
    folders.value = [...folders.value, created];
    if (target.value) expanded.value = new Set([...expanded.value, target.value]);
    target.value = created.id;
    creating.value = false;
  } catch (err) {
    newError.value = normalizeApiError(err).message;
  } finally {
    creatingBusy.value = false;
  }
}

function confirm() {
  emit("move", { id: target.value, name: target.value ? byId.value.get(target.value)?.name ?? "folder" : "My files" });
  open.value = false;
}
</script>

<template>
  <UiModal v-model:open="open" :title="title" size="md">
    <p class="text-sm text-fg-muted">Move to: <span class="font-medium text-fg">{{ path.join(" / ") }}</span></p>
    <div class="mt-3 rounded-lg border border-line">
      <div v-if="loading" class="space-y-2 p-3" aria-busy="true">
        <UiSkeleton v-for="i in 5" :key="i" class="h-7" :class="i % 2 ? 'w-2/3' : 'w-1/2'" />
      </div>
      <UiAlert v-else-if="loadError" class="m-3">{{ loadError }}</UiAlert>
      <ul v-else role="tree" aria-label="Folders" class="max-h-72 overflow-y-auto p-1 scrollbar-thin">
        <li role="none">
          <button
            data-tree-item
            role="treeitem"
            :aria-selected="target === null"
            class="flex h-8 w-full items-center gap-2 rounded px-2 text-left text-base"
            :class="target === null ? 'bg-primary-soft text-primary-soft-fg' : 'text-fg hover:bg-canvas-subtle'"
            @click="target = null"
            @keydown="(e) => (e.key === 'ArrowDown' || e.key === 'ArrowUp') && onTreeKey(e, { node: { id: '' } as FileNode, hasChildren: false })"
          >
            <Home :size="16" :stroke-width="1.75" /> My files
            <span v-if="currentParent === null" class="ml-auto text-xs text-fg-subtle">Current</span>
          </button>
        </li>
        <li v-for="row in rows" :key="row.node.id" role="none">
          <div class="flex items-center" :style="{ paddingLeft: `${(row.depth - 1) * 18}px` }">
            <button
              v-if="row.hasChildren"
              type="button"
              class="flex h-8 w-6 shrink-0 items-center justify-center text-fg-subtle hover:text-fg"
              :aria-label="expanded.has(row.node.id) ? `Collapse ${row.node.name}` : `Expand ${row.node.name}`"
              tabindex="-1"
              @click="toggle(row.node.id)"
            >
              <ChevronRight :size="14" class="transition-transform" :class="{ 'rotate-90': expanded.has(row.node.id) }" />
            </button>
            <span v-else class="w-6 shrink-0" />
            <button
              data-tree-item
              role="treeitem"
              :aria-selected="target === row.node.id"
              :aria-expanded="row.hasChildren ? expanded.has(row.node.id) : undefined"
              :aria-level="row.depth + 1"
              class="flex h-8 min-w-0 flex-1 items-center gap-2 rounded px-2 text-left text-base"
              :class="target === row.node.id ? 'bg-primary-soft text-primary-soft-fg' : 'text-fg hover:bg-canvas-subtle'"
              @click="target = row.node.id"
              @keydown="onTreeKey($event, row)"
            >
              <Folder :size="16" :stroke-width="1.75" class="shrink-0 text-amber-500" />
              <span class="truncate">{{ row.node.name }}</span>
              <span v-if="currentParent === row.node.id" class="ml-auto shrink-0 text-xs text-fg-subtle">Current</span>
            </button>
          </div>
        </li>
      </ul>
    </div>

    <form v-if="creating" novalidate class="mt-3 flex items-start gap-2" @submit.prevent="createHere">
      <div class="flex-1">
        <input
          id="move-new-folder"
          v-model="newName"
          class="h-9 w-full rounded border bg-surface px-3 text-base text-fg outline-none focus:ring-4"
          :class="newError ? 'border-danger focus:ring-danger/15' : 'border-line-strong focus:border-primary focus:ring-primary/15'"
          placeholder="New folder name"
          aria-label="New folder name"
          :aria-invalid="!!newError || undefined"
          aria-describedby="move-new-folder-error"
          @input="newError = ''"
          @keydown.esc.stop="creating = false"
        />
        <p v-if="newError" id="move-new-folder-error" class="mt-1 text-sm text-danger" role="alert">{{ newError }}</p>
      </div>
      <UiButton type="submit" variant="secondary" :loading="creatingBusy">Create</UiButton>
    </form>

    <template #footer>
      <UiButton v-if="!creating" variant="ghost" :icon="FolderPlus" class="sm:mr-auto" @click="startCreate">New folder</UiButton>
      <UiButton @click="open = false">Cancel</UiButton>
      <UiButton variant="primary" :disabled="loading || target === currentParent" @click="confirm">Move here</UiButton>
    </template>
  </UiModal>
</template>

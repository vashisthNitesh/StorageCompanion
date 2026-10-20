<script setup lang="ts">
import { ref, watch } from "vue";
import { Folder, Home, Loader2 } from "lucide-vue-next";
import BaseModal from "../../components/BaseModal.vue";
import { useFilesStore, type FileNode } from "../../stores/files";

const props = defineProps<{ open: boolean; node: FileNode | null }>();
const emit = defineEmits<{ close: []; moved: [] }>();
const filesStore = useFilesStore();

const folders = ref<{ id: string | null; name: string; depth: number }[]>([]);
const target = ref<string | null>(null);
const loading = ref(false);
const busy = ref(false);
const error = ref("");

watch(
  () => props.open,
  async (open) => {
    if (!open || !props.node) return;
    error.value = "";
    target.value = props.node.parent;
    loading.value = true;
    try {
      folders.value = await filesStore.listFolders(props.node.type === "folder" ? props.node.id : undefined);
    } catch (err: any) {
      error.value = err.message || "Couldn't load your folders.";
    } finally {
      loading.value = false;
    }
  }
);

async function move() {
  if (!props.node) return;
  busy.value = true;
  error.value = "";
  try {
    await filesStore.moveNode(props.node.id, target.value);
    emit("moved");
    emit("close");
  } catch (err: any) {
    error.value = err.message || "Couldn't move this item.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <BaseModal :open="open" :title="`Move “${node?.name ?? ''}”`" @close="emit('close')">
    <p class="mb-3 text-sm text-slate-600">Choose a destination folder.</p>
    <div v-if="loading" class="flex items-center gap-2 py-8 text-sm text-slate-500 justify-center">
      <Loader2 class="h-4 w-4 animate-spin" /> Loading folders…
    </div>
    <div v-else class="max-h-72 overflow-y-auto rounded-lg border border-slate-200 p-1" role="radiogroup">
      <label
        v-for="f in folders"
        :key="f.id ?? 'root'"
        class="flex cursor-pointer items-center gap-2 rounded-md py-2 pr-3 text-sm hover:bg-slate-50"
        :class="target === f.id ? 'bg-brand-50 text-brand-800' : 'text-slate-700'"
        :style="{ paddingLeft: `${12 + f.depth * 16}px` }"
      >
        <input v-model="target" type="radio" :value="f.id" class="sr-only" />
        <Home v-if="f.id === null" class="h-4 w-4 shrink-0 text-slate-500" />
        <Folder v-else class="h-4 w-4 shrink-0 text-amber-500" />
        <span class="truncate">{{ f.name }}</span>
        <span v-if="f.id === node?.parent" class="ml-auto shrink-0 text-xs text-slate-400">current</span>
      </label>
    </div>
    <div v-if="error" class="alert-error mt-3">{{ error }}</div>
    <template #footer>
      <button class="btn-secondary" @click="emit('close')">Cancel</button>
      <button class="btn-primary" :disabled="busy || loading || target === node?.parent" @click="move">
        <Loader2 v-if="busy" class="h-4 w-4 animate-spin" /> Move here
      </button>
    </template>
  </BaseModal>
</template>

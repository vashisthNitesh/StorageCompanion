<script setup lang="ts">
import { ref, watch } from "vue";
import { Loader2 } from "lucide-vue-next";
import BaseModal from "../../components/BaseModal.vue";

const props = defineProps<{
  open: boolean;
  title: string;
  label: string;
  initial?: string;
  confirmLabel: string;
  submit: (name: string) => Promise<unknown>;
}>();
const emit = defineEmits<{ close: [] }>();

const name = ref("");
const busy = ref(false);
const error = ref("");
const input = ref<HTMLInputElement | null>(null);

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    name.value = props.initial || "";
    error.value = "";
    // Select the name without its extension, like a desktop file manager.
    setTimeout(() => {
      const el = input.value;
      if (!el) return;
      el.focus();
      const dot = name.value.lastIndexOf(".");
      el.setSelectionRange(0, dot > 0 ? dot : name.value.length);
    }, 50);
  }
);

async function save() {
  const value = name.value.trim();
  if (!value) {
    error.value = "Please enter a name.";
    return;
  }
  if (/[\\/]/.test(value)) {
    error.value = "Names can't contain / or \\.";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await props.submit(value);
    emit("close");
  } catch (err: any) {
    error.value = err.message || "Couldn't save. Please try again.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <BaseModal :open="open" :title="title" size="sm" @close="emit('close')">
    <form id="name-dialog-form" @submit.prevent="save">
      <label for="name-dialog-input" class="label">{{ label }}</label>
      <input id="name-dialog-input" ref="input" v-model="name" class="input" maxlength="255" autocomplete="off" />
      <p v-if="error" class="mt-2 text-sm text-rose-600">{{ error }}</p>
    </form>
    <template #footer>
      <button type="button" class="btn-secondary" @click="emit('close')">Cancel</button>
      <button type="submit" form="name-dialog-form" class="btn-primary" :disabled="busy">
        <Loader2 v-if="busy" class="h-4 w-4 animate-spin" />
        {{ confirmLabel }}
      </button>
    </template>
  </BaseModal>
</template>

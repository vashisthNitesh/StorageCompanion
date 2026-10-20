<script setup lang="ts">
import { ref } from "vue";
import { Loader2 } from "lucide-vue-next";
import BaseModal from "./BaseModal.vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    danger?: boolean;
    action: () => Promise<unknown>;
  }>(),
  { confirmLabel: "Confirm", danger: false }
);
const emit = defineEmits<{ close: []; done: [] }>();
const busy = ref(false);
const error = ref("");

async function confirm() {
  busy.value = true;
  error.value = "";
  try {
    await props.action();
    emit("done");
    emit("close");
  } catch (err: any) {
    error.value = err.message || "Something went wrong.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <BaseModal :open="open" :title="title" size="sm" @close="emit('close')">
    <p class="text-sm text-slate-600">{{ message }}</p>
    <div v-if="error" class="alert-error mt-4">{{ error }}</div>
    <template #footer>
      <button class="btn-secondary" :disabled="busy" @click="emit('close')">Cancel</button>
      <button :class="danger ? 'btn-danger' : 'btn-primary'" :disabled="busy" @click="confirm">
        <Loader2 v-if="busy" class="h-4 w-4 animate-spin" />
        {{ confirmLabel }}
      </button>
    </template>
  </BaseModal>
</template>

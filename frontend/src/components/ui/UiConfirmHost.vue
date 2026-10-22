<script setup lang="ts">
import { computed, ref, watch } from "vue";
import UiModal from "./UiModal.vue";
import UiButton from "./UiButton.vue";
import UiInput from "./UiInput.vue";
import UiFormField from "./UiFormField.vue";
import UiAlert from "./UiAlert.vue";
import { confirmState, settleConfirm } from "../../lib/confirm";
import { normalizeApiError } from "../../lib/errors";

const typed = ref("");
const busy = ref(false);
const error = ref("");
const opts = computed(() => confirmState.options);
const canConfirm = computed(() => !opts.value?.typeToConfirm || typed.value.trim() === opts.value.typeToConfirm);

watch(
  () => confirmState.open,
  (open) => {
    if (open) {
      typed.value = "";
      error.value = "";
      busy.value = false;
    }
  }
);

async function confirm() {
  if (!canConfirm.value || busy.value) return;
  if (!opts.value?.action) return settleConfirm(true);
  busy.value = true;
  error.value = "";
  try {
    await opts.value.action();
    settleConfirm(true);
  } catch (err) {
    error.value = normalizeApiError(err).message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <UiModal
    :open="confirmState.open"
    :title="opts?.title ?? ''"
    size="sm"
    :dismissible="!busy"
    @update:open="(o) => !o && settleConfirm(false)"
  >
    <form novalidate class="space-y-4" @submit.prevent="confirm">
      <p v-if="opts?.body" class="text-base text-fg-muted">{{ opts.body }}</p>
      <UiFormField v-if="opts?.typeToConfirm" :label="`Type “${opts.typeToConfirm}” to confirm`">
        <UiInput v-model="typed" autocomplete="off" autofocus />
      </UiFormField>
      <UiAlert v-if="error">{{ error }}</UiAlert>
      <!-- Hidden submit so Enter confirms from the type-to-confirm field. -->
      <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
    </form>
    <template #footer>
      <UiButton :disabled="busy" @click="settleConfirm(false)">{{ opts?.cancelLabel ?? "Cancel" }}</UiButton>
      <UiButton :variant="opts?.danger ? 'danger' : 'primary'" :loading="busy" :disabled="!canConfirm" @click="confirm">
        {{ opts?.confirmLabel }}
      </UiButton>
    </template>
  </UiModal>
</template>

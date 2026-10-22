<script setup lang="ts">
import { LockKeyhole } from "lucide-vue-next";
import UiModal from "../../components/ui/UiModal.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { useAuthStore } from "../../stores/auth";
import { rules, useForm } from "../../composables/useForm";

defineProps<{ open: boolean }>();
const emit = defineEmits<{ signOut: [] }>();
const authStore = useAuthStore();
const form = useForm({ password: "" }, { password: [rules.required("Enter your password.")] });

async function unlock() {
  await form.submit(async (v) => {
    try {
      await authStore.unlockVault(v.password);
      form.reset();
    } catch {
      form.errors.password = "That password didn't unlock your files. Try again.";
      throw new Error("handled");
    }
  });
  if (form.formError.value) form.formError.value = "";
}
</script>

<template>
  <UiModal :open="open" title="Unlock your files" size="sm" :dismissible="false">
    <form :ref="(el) => (form.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="unlock">
      <p class="flex gap-2.5 text-base text-fg-muted">
        <LockKeyhole :size="18" :stroke-width="1.75" class="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
        Your files are encrypted with your password. Enter it to open them on this device.
      </p>
      <UiFormField label="Password" :error="form.errors.password">
        <UiPasswordInput v-model="form.values.password" autocomplete="current-password" autofocus @blur="form.blur('password')" />
      </UiFormField>
      <UiAlert v-if="form.formError.value">{{ form.formError.value }}</UiAlert>
      <div class="flex items-center justify-between gap-3 pt-1">
        <UiButton variant="ghost" @click="emit('signOut')">Sign out</UiButton>
        <UiButton type="submit" variant="primary" :loading="form.submitting.value">Unlock</UiButton>
      </div>
    </form>
  </UiModal>
</template>

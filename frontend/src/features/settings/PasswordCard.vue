<script setup lang="ts">
import { computed } from "vue";
import { Check, X, KeyRound } from "lucide-vue-next";
import UiCard from "../../components/ui/UiCard.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest } from "../../lib/api";
import { toast } from "../../lib/toast";
import { deriveKEK, DEFAULT_KDF_PARAMS, generateRandomSalt } from "../../lib/crypto/kdf";
import { wrapKey } from "../../lib/crypto/keys";
import { rules, useForm } from "../../composables/useForm";
import { passwordStrength } from "./passwordStrength";

const emit = defineEmits<{ changed: [] }>();
const authStore = useAuthStore();
const isGoogleOnly = computed(() => !!authStore.user?.has_google && !authStore.user?.wrapped_master_key);

const form = useForm(
  { current: "", next: "", confirm: "" },
  {
    current: [rules.required("Enter your current password.")],
    next: [
      rules.required("Enter a new password."),
      (v: string, all) => (passwordStrength(v, all.current).checks.every((c) => c.ok) ? null : "Choose a password that meets all the requirements below."),
    ],
    confirm: [rules.required("Re-enter the new password."), (v: string, all) => (v && v !== all.next ? "The passwords don't match." : null)],
  },
  { serverFieldMap: { current_password: "current", new_password: "next" } }
);
const strength = computed(() => passwordStrength(form.values.next, form.values.current));
const canSubmit = computed(() => !!form.values.current && strength.value.checks.every((c) => c.ok) && form.values.confirm === form.values.next);
const barTone = computed(() => ["bg-danger", "bg-danger", "bg-warning", "bg-success", "bg-success"][strength.value.score]);

async function submit() {
  if (authStore.user?.wrapped_master_key && !authStore.masterKey) {
    form.formError.value = "Unlock your files first (open My files), then change your password.";
    return;
  }
  const ok = await form.submit(async (v) => {
    const payload: Record<string, unknown> = { current_password: v.current, new_password: v.next };
    if (authStore.masterKey && authStore.user?.wrapped_master_key) {
      // Re-wrap the vault key with the new password; files don't need re-encrypting.
      const salt = generateRandomSalt(16);
      payload.new_wrapped_master_key = await wrapKey(await deriveKEK(v.next, salt, DEFAULT_KDF_PARAMS), authStore.masterKey);
      payload.new_kdf_salt = salt;
      payload.new_kdf_params = DEFAULT_KDF_PARAMS;
    }
    await apiRequest("/api/v1/auth/password", { method: "POST", body: JSON.stringify(payload) });
  });
  if (ok) {
    form.reset();
    toast.success("Password updated. Other devices were signed out.");
    await authStore.fetchProfile();
    emit("changed");
  } else if (/current password/i.test(form.formError.value)) {
    // The API reports a wrong current password as a general error; show it on the field.
    form.formError.value = "";
    form.errors.current = "That's not your current password.";
  }
}
</script>

<template>
  <UiCard id="password" title="Password" description="Your password also encrypts your files. Changing it doesn't re-upload anything.">
    <template #actions><KeyRound :size="18" :stroke-width="1.75" class="hidden text-fg-subtle sm:block" aria-hidden="true" /></template>
    <p v-if="isGoogleOnly" class="text-base text-fg-muted">
      You sign in with Google, so there's no SmartSpace password to change. Manage your Google account's security at
      <a href="https://myaccount.google.com/security" target="_blank" rel="noopener" class="font-medium text-primary hover:underline">myaccount.google.com</a>.
    </p>
    <form v-else :ref="(el) => (form.formEl.value = el as HTMLFormElement)" novalidate class="grid gap-5 lg:grid-cols-2" @submit.prevent="submit">
      <UiFormField class="lg:col-span-2 lg:max-w-[calc(50%-10px)]" label="Current password" :error="form.errors.current">
        <UiPasswordInput v-model="form.values.current" autocomplete="current-password" @blur="form.blur('current')" />
      </UiFormField>
      <div class="space-y-3">
        <UiFormField label="New password" :error="form.errors.next">
          <UiPasswordInput v-model="form.values.next" autocomplete="new-password" @blur="form.blur('next')" />
        </UiFormField>
        <div v-if="form.values.next" aria-live="polite">
          <div class="flex items-center gap-3">
            <div class="flex flex-1 gap-1" aria-hidden="true">
              <span v-for="i in 4" :key="i" class="h-1.5 flex-1 rounded-full" :class="i <= strength.score ? barTone : 'bg-line'" />
            </div>
            <span class="text-sm font-medium text-fg-muted">{{ strength.label }}</span>
          </div>
        </div>
        <ul class="space-y-1.5" aria-label="Password requirements">
          <li v-for="c in strength.checks" :key="c.label" class="flex items-center gap-2 text-sm" :class="c.ok ? 'text-success' : 'text-fg-subtle'">
            <Check v-if="c.ok" :size="14" :stroke-width="2.5" aria-hidden="true" />
            <X v-else :size="14" :stroke-width="2.5" aria-hidden="true" />
            {{ c.label }}<span class="sr-only">{{ c.ok ? " (met)" : " (not met)" }}</span>
          </li>
        </ul>
      </div>
      <UiFormField label="Confirm new password" :error="form.errors.confirm">
        <UiPasswordInput v-model="form.values.confirm" autocomplete="new-password" @blur="form.blur('confirm')" />
        <p v-if="form.values.confirm && form.values.confirm === form.values.next && !form.errors.confirm" class="mt-1.5 flex items-center gap-1.5 text-sm text-success">
          <Check :size="14" :stroke-width="2.5" aria-hidden="true" /> Passwords match
        </p>
      </UiFormField>
      <UiAlert v-if="form.formError.value" class="lg:col-span-2">{{ form.formError.value }}</UiAlert>
      <div class="flex justify-end lg:col-span-2">
        <UiButton type="submit" variant="primary" :loading="form.submitting.value" :disabled="!canSubmit">Update password</UiButton>
      </div>
    </form>
  </UiCard>
</template>

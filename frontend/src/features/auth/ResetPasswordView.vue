<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { AlertTriangle, CheckCircle2, KeyRound, LinkIcon } from "lucide-vue-next";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiSpinner from "../../components/ui/UiSpinner.vue";
import { rules, useForm } from "../../composables/useForm";
import { normalizeApiError } from "../../lib/errors";
import { InvalidRecoveryKey } from "../../lib/crypto/recoveryKey";
import { passwordStrength } from "../settings/passwordStrength";
import { useAuthStore } from "../../stores/auth";
import AuthShell from "./AuthShell.vue";
import PasswordRequirements from "./PasswordRequirements.vue";
import {
  RecoveryKeyMismatch,
  checkResetLink,
  readResetLink,
  resetWithRecoveryKey,
  resetWithoutRecoveryKey,
  type ResetInfo,
  type ResetLink,
} from "./passwordReset";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const link = ref<ResetLink | null>(null);
const info = ref<ResetInfo | null>(null);
const state = ref<"loading" | "invalid" | "form" | "done">("loading");
const invalidMessage = ref("");
/** "key": re-wrap with the recovery key. "nokey": new empty vault after an explicit warning. */
const mode = ref<"key" | "nokey">("key");
const doneMode = ref<"key" | "nokey">("key");

const strongEnough = (pw: string) => passwordStrength(pw).checks.filter((c) => !/current/.test(c.label)).every((c) => c.ok);
const form = useForm(
  { recoveryKey: "", password: "", confirm: "", acknowledged: false },
  {
    recoveryKey: [(v: string) => (mode.value === "key" && !v.trim() ? "Enter your recovery key." : null)],
    password: [rules.required("Choose a new password."), (v: string) => (strongEnough(v) ? null : "Choose a password that meets the requirements below.")],
    confirm: [rules.required("Re-enter the new password."), (v: string, all) => (v && v !== all.password ? "The passwords don't match." : null)],
    acknowledged: [(v: boolean) => (mode.value === "nokey" && !v ? "Confirm you understand before continuing." : null)],
  }
);

const title = computed(
  () => ({ loading: "Reset your password", invalid: "This link doesn't work", form: "Choose a new password", done: "Password changed" })[state.value]
);

onMounted(async () => {
  link.value = readResetLink(route.hash || window.location.hash);
  // Drop the token from the address bar and history.
  if (route.hash) void router.replace({ path: route.path, hash: "" });
  if (!link.value) {
    state.value = "invalid";
    invalidMessage.value = "The link is incomplete. Open it straight from the email, or ask for a new one.";
    return;
  }
  try {
    info.value = await checkResetLink(link.value);
    mode.value = info.value.has_recovery_key ? "key" : "nokey";
    state.value = "form";
  } catch (err) {
    state.value = "invalid";
    invalidMessage.value = normalizeApiError(err).message;
  }
});

function switchMode(next: "key" | "nokey") {
  mode.value = next;
  form.formError.value = "";
  delete form.errors.recoveryKey;
  delete form.errors.acknowledged;
}

async function submit() {
  if (!link.value || !info.value) return;
  let keyProblem = "";
  const ok = await form.submit(async (v) => {
    try {
      if (mode.value === "key") await resetWithRecoveryKey(link.value!, info.value!, v.recoveryKey, v.password);
      else await resetWithoutRecoveryKey(link.value!, v.password);
    } catch (err) {
      if (err instanceof RecoveryKeyMismatch || err instanceof InvalidRecoveryKey) keyProblem = err.message;
      throw err;
    }
  });
  if (keyProblem) {
    form.formError.value = "";
    form.errors.recoveryKey = keyProblem;
    return;
  }
  if (!ok) return;
  // Every session was signed out, this tab included.
  if (authStore.isAuthenticated) await authStore.logout();
  doneMode.value = mode.value;
  state.value = "done";
}
</script>

<template>
  <AuthShell :title="title" :subtitle="state === 'form' && info ? `For ${info.email}` : undefined">
    <div v-if="state === 'loading'" class="flex justify-center py-6"><UiSpinner /></div>

    <div v-else-if="state === 'invalid'" class="space-y-4">
      <p class="flex gap-3 text-base text-fg-muted">
        <LinkIcon :size="20" :stroke-width="1.75" class="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
        <span>{{ invalidMessage }}</span>
      </p>
      <UiButton variant="primary" size="lg" block to="/forgot-password">Send a new link</UiButton>
    </div>

    <div v-else-if="state === 'done'" class="space-y-4">
      <p class="flex gap-3 text-base text-fg-muted">
        <CheckCircle2 :size="20" :stroke-width="1.75" class="mt-0.5 shrink-0 text-success" aria-hidden="true" />
        <span v-if="doneMode === 'key'">Your password is changed and your files are safe. All devices were signed out.</span>
        <span v-else>Your password is changed and all devices were signed out. After you sign in, you'll create a new recovery key.</span>
      </p>
      <UiButton variant="primary" size="lg" block to="/login">Sign in</UiButton>
    </div>

    <form v-else :ref="(el) => (form.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="submit">
      <div v-if="info?.has_recovery_key" class="grid grid-cols-2 gap-1 rounded-lg bg-canvas-subtle p-1" role="tablist" aria-label="How to reset">
        <button
          v-for="opt in [{ v: 'key', l: 'I have my recovery key' }, { v: 'nokey', l: 'I don’t have it' }] as const"
          :key="opt.v"
          type="button"
          role="tab"
          :aria-selected="mode === opt.v"
          class="rounded-md px-2 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          :class="mode === opt.v ? 'bg-surface text-fg shadow-xs' : 'text-fg-muted hover:text-fg'"
          @click="switchMode(opt.v)"
        >
          {{ opt.l }}
        </button>
      </div>

      <UiAlert v-if="form.formError.value">{{ form.formError.value }}</UiAlert>

      <template v-if="mode === 'key'">
        <UiFormField label="Recovery key" :error="form.errors.recoveryKey" hint="32 letters and numbers, from when you set up your account.">
          <UiInput
            v-model="form.values.recoveryKey"
            :icon="KeyRound"
            class="font-mono uppercase tracking-wider"
            autocomplete="off"
            autocapitalize="characters"
            spellcheck="false"
            placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
            @blur="form.blur('recoveryKey')"
          />
        </UiFormField>
      </template>
      <div v-else class="rounded-lg border border-danger/40 bg-danger-soft p-4" role="alert">
        <p class="flex items-start gap-2 text-base font-semibold text-danger">
          <AlertTriangle :size="18" class="mt-0.5 shrink-0" aria-hidden="true" />Your existing files can't be decrypted
        </p>
        <p class="mt-2 text-base text-fg">
          Without your recovery key, nobody can unlock the files you've already uploaded, not even us. You'll get back into your account with an empty vault;
          old files stay listed but can't be opened or downloaded.
        </p>
        <div class="mt-3">
          <UiCheckbox
            v-model="form.values.acknowledged"
            :invalid="!!form.errors.acknowledged"
            label="I understand my existing files will be lost"
            @update:model-value="form.blur('acknowledged')"
          />
          <p v-if="form.errors.acknowledged" class="mt-2 pl-6 text-sm text-danger" role="alert">{{ form.errors.acknowledged }}</p>
        </div>
      </div>

      <div class="space-y-3">
        <UiFormField label="New password" :error="form.errors.password">
          <UiPasswordInput v-model="form.values.password" autocomplete="new-password" @blur="form.blur('password')" />
        </UiFormField>
        <PasswordRequirements :password="form.values.password" />
      </div>
      <UiFormField label="Confirm new password" :error="form.errors.confirm">
        <UiPasswordInput v-model="form.values.confirm" autocomplete="new-password" @blur="form.blur('confirm')" />
      </UiFormField>

      <UiButton type="submit" :variant="mode === 'key' ? 'primary' : 'danger'" size="lg" block :loading="form.submitting.value">
        {{ mode === "key" ? "Reset password" : "Reset password and lose old files" }}
      </UiButton>
    </form>

    <template v-if="state === 'form'" #footer>
      <router-link to="/login" class="font-medium text-primary hover:underline">Back to sign in</router-link>
    </template>
  </AuthShell>
</template>

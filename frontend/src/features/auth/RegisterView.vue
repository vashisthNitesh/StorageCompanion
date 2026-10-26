<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { rules, useForm } from "../../composables/useForm";
import { normalizeApiError } from "../../lib/errors";
import { passwordStrength } from "../settings/passwordStrength";
import AuthShell from "./AuthShell.vue";
import OrDivider from "./OrDivider.vue";
import MfaStep from "./MfaStep.vue";
import GoogleSignInButton from "./GoogleSignInButton.vue";
import RecoveryKeyPanel from "./RecoveryKeyPanel.vue";
import PasswordRequirements from "./PasswordRequirements.vue";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const meetsRequirements = (pw: string) => passwordStrength(pw).checks.every((c) => c.ok);
const form = useForm(
  { fullName: "", email: "", password: "", acknowledged: false },
  {
    fullName: [rules.maxLength(120, "Keep your name under 120 characters.")],
    email: [rules.required("Enter your email."), rules.email()],
    password: [rules.required("Choose a password."), (v: string) => (meetsRequirements(v) ? null : "Choose a password that meets the requirements below.")],
    acknowledged: [(v: boolean) => (v ? null : "Please confirm you understand before continuing.")],
  },
  { serverFieldMap: { full_name: "fullName" } }
);

// After the account is created, the recovery key is shown once before continuing.
const recoveryKey = ref<string | null>(null);
const recoverySaved = ref(false);
const confirming = ref(false);
const confirmError = ref("");

const googleMfaCredential = ref<string | null>(null);
const googleBusy = ref(false);
const googleError = ref("");

function goNext() {
  const plan = typeof route.query.plan === "string" ? route.query.plan : "";
  const interval = route.query.interval === "monthly" ? "monthly" : "yearly";
  router.replace(plan ? { name: "checkout", query: { plan, interval } } : "/app/files");
}

async function submit() {
  await form.submit(async (v) => {
    const res = await authStore.register(v.email.trim().toLowerCase(), v.password, v.fullName.trim());
    if (res.recoveryKey) recoveryKey.value = res.recoveryKey;
    else goNext();
  });
}

async function confirmRecovery() {
  confirming.value = true;
  confirmError.value = "";
  try {
    await authStore.confirmRecoveryKey();
    goNext();
  } catch (err) {
    confirmError.value = normalizeApiError(err).message;
  } finally {
    confirming.value = false;
  }
}

async function onGoogleCredential(credential: string) {
  googleBusy.value = true;
  googleError.value = "";
  try {
    const res = await authStore.loginWithGoogle(credential);
    if ("mfaRequired" in res) googleMfaCredential.value = credential;
    else goNext();
  } catch (err) {
    googleError.value = normalizeApiError(err).message;
  } finally {
    googleBusy.value = false;
  }
}

async function verifyGoogleMfa(code: string) {
  if (!googleMfaCredential.value) return;
  const res = await authStore.loginWithGoogle(googleMfaCredential.value, code);
  if (!("mfaRequired" in res)) goNext();
}
</script>

<template>
  <AuthShell
    :title="recoveryKey ? 'Save your recovery key' : googleMfaCredential ? 'Two-step verification' : 'Create your account'"
    :subtitle="
      recoveryKey
        ? 'Your account is ready. One last step: keep this key safe.'
        : googleMfaCredential
          ? 'This Google account already uses two-step verification. Enter the code from your authenticator app.'
          : 'Pick a plan after you sign up. You can look around first.'
    "
  >
    <form v-if="recoveryKey" class="space-y-4" novalidate @submit.prevent="confirmRecovery">
      <RecoveryKeyPanel v-model:saved="recoverySaved" :recovery-key="recoveryKey" :email="authStore.user?.email" />
      <UiAlert v-if="confirmError">{{ confirmError }}</UiAlert>
      <UiButton type="submit" variant="primary" size="lg" block :disabled="!recoverySaved" :loading="confirming">Continue</UiButton>
    </form>

    <MfaStep v-else-if="googleMfaCredential" :verify="verifyGoogleMfa" @cancel="googleMfaCredential = null" />

    <template v-else>
      <GoogleSignInButton text="signup_with" :disabled="googleBusy || form.submitting.value" @credential="onGoogleCredential" />
      <UiAlert v-if="googleError" class="mt-3">{{ googleError }}</UiAlert>
      <OrDivider label="or with email" />

      <form :ref="(el) => (form.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="submit">
        <UiAlert v-if="form.formError.value">{{ form.formError.value }}</UiAlert>
        <UiFormField label="Full name" optional :error="form.errors.fullName">
          <UiInput v-model="form.values.fullName" autocomplete="name" @blur="form.blur('fullName')" />
        </UiFormField>
        <UiFormField label="Email" :error="form.errors.email">
          <UiInput v-model="form.values.email" type="email" autocomplete="email" inputmode="email" placeholder="you@example.com" @blur="form.blur('email')" />
        </UiFormField>
        <div class="space-y-3">
          <UiFormField label="Password" :error="form.errors.password">
            <UiPasswordInput v-model="form.values.password" autocomplete="new-password" @blur="form.blur('password')" />
          </UiFormField>
          <PasswordRequirements :password="form.values.password" />
        </div>
        <div class="rounded-lg bg-warning-soft p-3">
          <UiCheckbox
            v-model="form.values.acknowledged"
            :invalid="!!form.errors.acknowledged"
            label="I understand my password encrypts my files"
            description="If I forget it, I'll need the recovery key shown next to keep my files."
            @update:model-value="form.blur('acknowledged')"
          />
          <p v-if="form.errors.acknowledged" class="mt-2 pl-6 text-sm text-danger" role="alert">{{ form.errors.acknowledged }}</p>
        </div>
        <UiButton type="submit" variant="primary" size="lg" block :loading="form.submitting.value">
          {{ form.submitting.value ? "Creating your encrypted vault…" : "Create account" }}
        </UiButton>
        <p class="text-center text-sm text-fg-subtle">
          By continuing you agree to the <router-link to="/legal" class="underline hover:text-fg">terms and privacy policy</router-link>.
        </p>
      </form>
    </template>

    <template v-if="!recoveryKey" #footer>
      Already have an account?
      <router-link to="/login" class="font-medium text-primary hover:underline">Sign in</router-link>
    </template>
  </AuthShell>
</template>

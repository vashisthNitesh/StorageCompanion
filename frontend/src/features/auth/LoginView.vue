<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { homeFor } from "../../router";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { rules, useForm } from "../../composables/useForm";
import { normalizeApiError } from "../../lib/errors";
import AuthShell from "./AuthShell.vue";
import OrDivider from "./OrDivider.vue";
import MfaStep from "./MfaStep.vue";
import GoogleSignInButton from "./GoogleSignInButton.vue";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const form = useForm(
  { email: "", password: "" },
  { email: [rules.required("Enter your email.")], password: [rules.required("Enter your password.")] }
);
// When 2FA is required we remember which method started the sign-in.
const mfaFor = ref<null | { kind: "password" } | { kind: "google"; credential: string }>(null);
const useBackup = ref(false);
const googleBusy = ref(false);
const googleError = ref("");

function goNext() {
  const redirect = typeof route.query.redirect === "string" && route.query.redirect.startsWith("/app") ? route.query.redirect : null;
  router.replace(redirect || homeFor(authStore.isMasterAdmin));
}

/** Sign-in failures get one honest, non-revealing message. */
function signInError(err: unknown): string {
  const n = normalizeApiError(err);
  if (n.kind === "validation" || n.kind === "auth") return "Email or password is incorrect.";
  if (err instanceof Error && /vault/.test(err.message)) return "Your password was accepted, but your files couldn't be unlocked. Please contact support.";
  return n.message;
}

async function submitPassword() {
  await form.submit(async (v) => {
    try {
      const res = await authStore.login(v.email.trim(), v.password);
      if ("mfaRequired" in res) {
        mfaFor.value = { kind: "password" };
        return;
      }
      goNext();
    } catch (err) {
      form.formError.value = signInError(err);
    }
  });
}

async function onGoogleCredential(credential: string) {
  googleBusy.value = true;
  googleError.value = "";
  try {
    const res = await authStore.loginWithGoogle(credential);
    if ("mfaRequired" in res) mfaFor.value = { kind: "google", credential };
    else goNext();
  } catch (err) {
    googleError.value = normalizeApiError(err).message;
  } finally {
    googleBusy.value = false;
  }
}

async function verifyMfa(code: string) {
  const pending = mfaFor.value;
  if (!pending) return;
  const res =
    pending.kind === "google"
      ? await authStore.loginWithGoogle(pending.credential, code)
      : await authStore.login(form.values.email.trim(), form.values.password, code);
  if (!("mfaRequired" in res)) goNext();
}
</script>

<template>
  <AuthShell
    :title="mfaFor ? 'Two-step verification' : 'Sign in to SmartSpace'"
    :subtitle="mfaFor ? (useBackup ? 'Enter one of your recovery codes.' : 'Enter the 6-digit code from your authenticator app.') : 'Welcome back.'"
  >
    <MfaStep v-if="mfaFor" :verify="verifyMfa" @cancel="mfaFor = null; useBackup = false" @update:use-backup="useBackup = $event" />

    <template v-else>
      <GoogleSignInButton text="signin_with" :disabled="googleBusy || form.submitting.value" @credential="onGoogleCredential" />
      <UiAlert v-if="googleError" class="mt-3">{{ googleError }}</UiAlert>
      <OrDivider label="or with email" />
      <form :ref="(el) => (form.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="submitPassword">
        <UiAlert v-if="form.formError.value">{{ form.formError.value }}</UiAlert>
        <UiFormField label="Email" :error="form.errors.email">
          <UiInput v-model="form.values.email" type="email" autocomplete="username" inputmode="email" placeholder="you@example.com" @blur="form.blur('email')" />
        </UiFormField>
        <div>
          <UiFormField label="Password" :error="form.errors.password">
            <UiPasswordInput v-model="form.values.password" autocomplete="current-password" @blur="form.blur('password')" />
          </UiFormField>
          <div class="mt-1.5 text-right">
            <router-link to="/forgot-password" class="text-sm font-medium text-primary hover:underline">Forgot password?</router-link>
          </div>
        </div>
        <UiButton type="submit" variant="primary" size="lg" block :loading="form.submitting.value">Sign in</UiButton>
      </form>
    </template>

    <template #footer>
      New to SmartSpace?
      <router-link to="/register" class="font-medium text-primary hover:underline">Create an account</router-link>
    </template>
  </AuthShell>
</template>

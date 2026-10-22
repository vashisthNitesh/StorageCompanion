<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Check, X } from "lucide-vue-next";
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
const strength = computed(() => passwordStrength(form.values.password));
// "Different from your current password" doesn't apply to a new account.
const checks = computed(() => strength.value.checks.filter((c) => !/current/.test(c.label)));
const barTone = computed(() => ["bg-danger", "bg-danger", "bg-warning", "bg-success", "bg-success"][strength.value.score]);

const googleMfaCredential = ref<string | null>(null);
const googleBusy = ref(false);
const googleError = ref("");

function goNext() {
  const plan = typeof route.query.plan === "string" ? route.query.plan : "";
  router.replace(plan ? { path: "/app/billing", query: { plan } } : "/app/files");
}

async function submit() {
  await form.submit(async (v) => {
    await authStore.register(v.email.trim().toLowerCase(), v.password, v.fullName.trim());
    goNext();
  });
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
    :title="googleMfaCredential ? 'Two-step verification' : 'Create your account'"
    :subtitle="googleMfaCredential ? 'This Google account already uses two-step verification. Enter the code from your authenticator app.' : 'Pick a plan after you sign up. You can look around first.'"
  >
    <MfaStep v-if="googleMfaCredential" :verify="verifyGoogleMfa" @cancel="googleMfaCredential = null" />

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
          <div v-if="form.values.password" class="flex items-center gap-3" aria-live="polite">
            <div class="flex flex-1 gap-1" aria-hidden="true">
              <span v-for="i in 4" :key="i" class="h-1.5 flex-1 rounded-full" :class="i <= strength.score ? barTone : 'bg-line'" />
            </div>
            <span class="text-sm font-medium text-fg-muted">{{ strength.label }}</span>
          </div>
          <ul class="space-y-1.5" aria-label="Password requirements">
            <li v-for="c in checks" :key="c.label" class="flex items-center gap-2 text-sm" :class="c.ok ? 'text-success' : 'text-fg-subtle'">
              <Check v-if="c.ok" :size="14" :stroke-width="2.5" aria-hidden="true" />
              <X v-else :size="14" :stroke-width="2.5" aria-hidden="true" />
              {{ c.label }}<span class="sr-only">{{ c.ok ? " (met)" : " (not met)" }}</span>
            </li>
          </ul>
        </div>
        <div class="rounded-lg bg-warning-soft p-3">
          <UiCheckbox
            v-model="form.values.acknowledged"
            :invalid="!!form.errors.acknowledged"
            label="I understand SmartSpace can't reset my password"
            description="Your password encrypts your files. If you forget it, your files can't be recovered."
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

    <template #footer>
      Already have an account?
      <router-link to="/login" class="font-medium text-primary hover:underline">Sign in</router-link>
    </template>
  </AuthShell>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { AlertCircle, Check, Loader2 } from "lucide-vue-next";
import { useAuthStore } from "../../stores/auth";
import AuthShell from "./AuthShell.vue";
import GoogleSignInButton from "./GoogleSignInButton.vue";
import PasswordInput from "./PasswordInput.vue";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const fullName = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const acknowledged = ref(false);
const errorMessage = ref("");
const busy = ref(false);
const googleMfaCredential = ref<string | null>(null);
const totpCode = ref("");

const checks = computed(() => [
  { label: "At least 10 characters", ok: password.value.length >= 10 },
  { label: "Passwords match", ok: !!password.value && password.value === confirmPassword.value },
]);
const canSubmit = computed(() => checks.value.every((c) => c.ok) && acknowledged.value && !busy.value);

function goNext() {
  const plan = typeof route.query.plan === "string" ? route.query.plan : "";
  router.replace(plan ? { path: "/app/billing", query: { plan } } : "/app/files");
}

async function handleRegister() {
  if (!canSubmit.value) return;
  errorMessage.value = "";
  busy.value = true;
  try {
    await authStore.register(email.value.trim().toLowerCase(), password.value, fullName.value.trim());
    goNext();
  } catch (err: any) {
    errorMessage.value = err.message || "We couldn't create your account. Please check your details.";
  } finally {
    busy.value = false;
  }
}

async function onGoogleCredential(credential: string, code?: string) {
  errorMessage.value = "";
  busy.value = true;
  try {
    const res = await authStore.loginWithGoogle(credential, code);
    if ("mfaRequired" in res) {
      googleMfaCredential.value = credential;
      return;
    }
    goNext();
  } catch (err: any) {
    errorMessage.value = err.message || "Google sign-up failed. Please try again.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <AuthShell title="Create your account" subtitle="Choose a plan after you sign up. You can look around first.">
    <div v-if="errorMessage" class="alert-error mb-5" role="alert">
      <AlertCircle class="mt-0.5 h-4 w-4 shrink-0" />
      <span>{{ errorMessage }}</span>
    </div>

    <form v-if="googleMfaCredential" class="space-y-4" @submit.prevent="onGoogleCredential(googleMfaCredential!, totpCode)">
      <p class="text-sm text-slate-600">This Google account has two-step verification. Enter the code from your authenticator app.</p>
      <input v-model="totpCode" class="input h-12 text-center font-mono text-lg tracking-[0.3em]" inputmode="numeric" autocomplete="one-time-code" placeholder="000000" required autofocus />
      <button type="submit" class="btn-primary btn-lg w-full" :disabled="busy">Verify</button>
    </form>

    <template v-else>
      <GoogleSignInButton text="signup_with" :disabled="busy" @credential="onGoogleCredential" />

      <div class="my-6 flex items-center gap-3 text-xs uppercase tracking-wide text-slate-400">
        <span class="h-px flex-1 bg-slate-200"></span>
        or use email
        <span class="h-px flex-1 bg-slate-200"></span>
      </div>

      <form class="space-y-4" @submit.prevent="handleRegister">
        <div>
          <label for="name" class="label">Full name <span class="font-normal text-slate-400">(optional)</span></label>
          <input id="name" v-model="fullName" class="input" autocomplete="name" maxlength="120" />
        </div>
        <div>
          <label for="email" class="label">Email</label>
          <input id="email" v-model="email" class="input" type="email" autocomplete="email" placeholder="you@example.com" required />
        </div>
        <div>
          <label for="password" class="label">Password</label>
          <PasswordInput id="password" v-model="password" autocomplete="new-password" :minlength="10" required />
        </div>
        <div>
          <label for="confirm" class="label">Confirm password</label>
          <PasswordInput id="confirm" v-model="confirmPassword" autocomplete="new-password" required />
          <ul class="mt-2 space-y-1">
            <li v-for="c in checks" :key="c.label" class="flex items-center gap-1.5 text-xs" :class="c.ok ? 'text-emerald-700' : 'text-slate-500'">
              <Check class="h-3.5 w-3.5" :class="c.ok ? 'opacity-100' : 'opacity-30'" />
              {{ c.label }}
            </li>
          </ul>
        </div>
        <label class="flex items-start gap-2.5 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-inset ring-amber-600/20">
          <input v-model="acknowledged" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-amber-400 text-brand-600 focus:ring-brand-500" />
          <span>I understand my password encrypts my files. <strong>SmartSpace can't reset it</strong>, so if I forget it my files can't be recovered.</span>
        </label>
        <button type="submit" class="btn-primary btn-lg w-full" :disabled="!canSubmit">
          <Loader2 v-if="busy" class="h-4 w-4 animate-spin" />
          {{ busy ? "Creating your encrypted vault…" : "Create account" }}
        </button>
        <p class="text-center text-xs text-slate-500">
          By continuing you agree to the <router-link to="/legal" class="underline hover:text-slate-700">terms and privacy policy</router-link>.
        </p>
      </form>

      <p class="mt-8 text-center text-sm text-slate-500">
        Already have an account?
        <router-link to="/login" class="font-medium text-brand-600 hover:text-brand-700">Sign in</router-link>
      </p>
    </template>
  </AuthShell>
</template>

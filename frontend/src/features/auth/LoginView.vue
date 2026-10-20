<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { AlertCircle, Loader2, ShieldCheck } from "lucide-vue-next";
import { useAuthStore } from "../../stores/auth";
import { homeFor } from "../../router";
import AuthShell from "./AuthShell.vue";
import GoogleSignInButton from "./GoogleSignInButton.vue";
import PasswordInput from "./PasswordInput.vue";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const totpCode = ref("");
const errorMessage = ref("");
const busy = ref(false);
// When 2FA is required we remember which method started the sign-in.
const mfaFor = ref<null | { kind: "password" } | { kind: "google"; credential: string }>(null);

const sessionExpired = computed(() => route.query.expired === "1");

function goNext() {
  const redirect = typeof route.query.redirect === "string" && route.query.redirect.startsWith("/app") ? route.query.redirect : null;
  router.replace(redirect || homeFor(authStore.isMasterAdmin));
}

async function run(action: () => Promise<{ mfaRequired?: true; success?: true }>, onMfa: () => void) {
  errorMessage.value = "";
  busy.value = true;
  try {
    const res = await action();
    if ("mfaRequired" in res && res.mfaRequired) {
      onMfa();
      return;
    }
    goNext();
  } catch (err: any) {
    errorMessage.value = err.message || "Sign-in failed. Please try again.";
  } finally {
    busy.value = false;
  }
}

function submitPassword() {
  return run(
    () => authStore.login(email.value.trim(), password.value, totpCode.value || undefined),
    () => (mfaFor.value = { kind: "password" })
  );
}

function onGoogleCredential(credential: string) {
  return run(
    () => authStore.loginWithGoogle(credential),
    () => (mfaFor.value = { kind: "google", credential })
  );
}

function submitMfa() {
  const pending = mfaFor.value;
  if (!pending) return;
  if (pending.kind === "google") {
    return run(() => authStore.loginWithGoogle(pending.credential, totpCode.value), () => {});
  }
  return submitPassword();
}

function cancelMfa() {
  mfaFor.value = null;
  totpCode.value = "";
  errorMessage.value = "";
}
</script>

<template>
  <AuthShell
    :title="mfaFor ? 'Two-step verification' : 'Sign in'"
    :subtitle="mfaFor ? 'Enter the 6-digit code from your authenticator app, or one of your backup codes.' : 'Welcome back. Sign in to open your files.'"
  >
    <div v-if="sessionExpired && !errorMessage && !mfaFor" class="alert-info mb-5">
      <AlertCircle class="mt-0.5 h-4 w-4 shrink-0" />
      <span>Your session ended. Please sign in again.</span>
    </div>
    <div v-if="errorMessage" class="alert-error mb-5" role="alert">
      <AlertCircle class="mt-0.5 h-4 w-4 shrink-0" />
      <span>{{ errorMessage }}</span>
    </div>

    <form v-if="mfaFor" class="space-y-5" @submit.prevent="submitMfa">
      <div>
        <label for="totp" class="label">Verification code</label>
        <input
          id="totp"
          v-model="totpCode"
          class="input h-12 text-center font-mono text-lg tracking-[0.3em]"
          inputmode="numeric"
          autocomplete="one-time-code"
          placeholder="000000"
          maxlength="16"
          required
          autofocus
        />
      </div>
      <button type="submit" class="btn-primary btn-lg w-full" :disabled="busy || !totpCode.trim()">
        <Loader2 v-if="busy" class="h-4 w-4 animate-spin" />
        <ShieldCheck v-else class="h-4 w-4" />
        Verify and sign in
      </button>
      <button type="button" class="btn-ghost w-full" @click="cancelMfa">Use a different account</button>
    </form>

    <template v-else>
      <GoogleSignInButton text="signin_with" :disabled="busy" @credential="onGoogleCredential" />

      <div class="my-6 flex items-center gap-3 text-xs uppercase tracking-wide text-slate-400">
        <span class="h-px flex-1 bg-slate-200"></span>
        or sign in with email
        <span class="h-px flex-1 bg-slate-200"></span>
      </div>

      <form class="space-y-4" @submit.prevent="submitPassword">
        <div>
          <label for="email" class="label">Email</label>
          <input id="email" v-model="email" class="input" type="text" autocomplete="username" placeholder="you@example.com" required />
        </div>
        <div>
          <label for="password" class="label">Password</label>
          <PasswordInput id="password" v-model="password" autocomplete="current-password" required />
        </div>
        <button type="submit" class="btn-primary btn-lg w-full" :disabled="busy">
          <Loader2 v-if="busy" class="h-4 w-4 animate-spin" />
          {{ busy ? "Signing in…" : "Sign in" }}
        </button>
      </form>

      <p class="mt-8 text-center text-sm text-slate-500">
        New to SmartSpace?
        <router-link to="/register" class="font-medium text-brand-600 hover:text-brand-700">Create an account</router-link>
      </p>
    </template>
  </AuthShell>
</template>

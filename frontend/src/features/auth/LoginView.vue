<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { Lock, AlertTriangle, ArrowRight, RefreshCw, Eye, EyeOff } from "lucide-vue-next";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const showPassword = ref(false);
const totpCode = ref("");
const mfaRequired = ref(false);
const errorMessage = ref("");
const isGoogleLoading = ref(false);
const googleBtnRef = ref<HTMLElement | null>(null);

onMounted(async () => {
  if (authStore.isAuthenticated) {
    const target = authStore.isMasterAdmin ? "/app/admin" : "/app/files";
    router.replace((route.query.redirect as string) || target);
    return;
  }

  await authStore.fetchAuthConfig();
  setupGoogleSignIn();
});

function setupGoogleSignIn() {
  const google = (window as any).google;
  if (!google?.accounts?.id || !authStore.googleClientId) return;

  try {
    google.accounts.id.initialize({
      client_id: authStore.googleClientId,
      callback: handleGoogleCredentialResponse,
      auto_select: false,
      cancel_on_tap_outside: true,
    });

    if (googleBtnRef.value) {
      google.accounts.id.renderButton(googleBtnRef.value, {
        theme: "outline",
        size: "large",
        type: "standard",
        shape: "rectangular",
        text: "signin_with",
        logo_alignment: "left",
        width: 380,
      });
    }
  } catch (e) {
    console.warn("Failed to initialize Google Sign-In:", e);
  }
}

async function handleGoogleCredentialResponse(response: any) {
  if (!response?.credential) return;
  isGoogleLoading.value = true;
  errorMessage.value = "";
  try {
    await authStore.loginWithGoogle(response.credential);
    const defaultTarget = authStore.isMasterAdmin ? "/app/admin" : "/app/files";
    let redirectPath = (route.query.redirect as string) || defaultTarget;
    if (redirectPath.includes("gate=required") && authStore.hasActiveSubscription) {
      redirectPath = defaultTarget;
    }
    router.push(redirectPath);
  } catch (err: any) {
    errorMessage.value = err.message || "Google sign-in failed. Please try again.";
  } finally {
    isGoogleLoading.value = false;
  }
}

function triggerGooglePrompt() {
  const google = (window as any).google;
  if (google?.accounts?.id && authStore.googleClientId) {
    google.accounts.id.prompt();
  } else {
    // In dev / test environment without live Google client credentials, provide a mock login option
    const devToken = prompt("Enter Google Test Token (or click OK for default demo user):", "mock_token_user");
    if (devToken) {
      handleGoogleCredentialResponse({ credential: devToken });
    }
  }
}

async function handleLogin() {
  errorMessage.value = "";
  try {
    const res = await authStore.login(email.value, password.value, totpCode.value);
    if (res.mfaRequired) {
      mfaRequired.value = true;
      return;
    }

    const defaultTarget = authStore.isMasterAdmin ? "/app/admin" : "/app/files";
    let redirectPath = (route.query.redirect as string) || defaultTarget;
    if (redirectPath.includes("gate=required") && authStore.hasActiveSubscription) {
      redirectPath = defaultTarget;
    }
    router.push(redirectPath);
  } catch (err: any) {
    errorMessage.value = err.message || "Invalid credentials or vault decryption failure.";
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#F8FAFC] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 selection:bg-brand-600 selection:text-white">
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2">
      <router-link to="/" class="inline-flex items-center space-x-2.5 group">
        <div class="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center shadow-sm shadow-brand-500/30">
          <Lock class="w-4 h-4 text-white" />
        </div>
        <div class="flex flex-col text-left">
          <span class="text-lg font-bold tracking-tight text-slate-900 leading-none">SmartSpace</span>
          <span class="text-[9px] text-slate-500 font-mono">smartspacedata.com</span>
        </div>
      </router-link>
      <h2 class="text-xl font-bold tracking-tight text-slate-900">Sign in to your account</h2>
      <p class="text-xs text-slate-500">Access your zero-knowledge vault or administrative portal</p>
    </div>

    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xl space-y-5">
        <!-- Error alert -->
        <div v-if="errorMessage" class="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start space-x-2.5">
          <AlertTriangle class="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span class="leading-relaxed">{{ errorMessage }}</span>
        </div>

        <!-- Google Sign In -->
        <div class="space-y-3">
          <div ref="googleBtnRef" class="w-full flex justify-center"></div>
          <button
            v-if="!authStore.googleClientId"
            type="button"
            @click="triggerGooglePrompt"
            :disabled="isGoogleLoading"
            class="w-full py-2.5 px-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-medium text-xs flex items-center justify-center space-x-2.5 transition-all shadow-2xs cursor-pointer"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
            </svg>
            <span>{{ isGoogleLoading ? 'Connecting to Google...' : 'Sign in with Google' }}</span>
          </button>
        </div>

        <div class="relative flex items-center justify-center">
          <div class="border-t border-slate-200 w-full"></div>
          <span class="bg-white px-3 text-[11px] text-slate-400 uppercase tracking-wider font-medium">or continue with password</span>
          <div class="border-t border-slate-200 w-full"></div>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Email or Username</label>
            <input
              type="text"
              v-model="email"
              required
              placeholder="Enter your email or username"
              class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 text-xs placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-xs font-semibold text-slate-700">Password</label>
            </div>
            <div class="relative">
              <input
                :type="showPassword ? 'text' : 'password'"
                v-model="password"
                required
                placeholder="Enter your password"
                class="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 text-xs placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                :title="showPassword ? 'Hide password' : 'Show password'"
              >
                <EyeOff v-if="showPassword" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- MFA TOTP input if enabled -->
          <div v-if="mfaRequired" class="space-y-1">
            <label class="block text-xs font-semibold text-brand-600">Two-Factor Authentication Code</label>
            <input
              type="text"
              v-model="totpCode"
              required
              placeholder="000 000"
              class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-brand-500 text-slate-900 text-center font-mono tracking-widest text-base focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading || isGoogleLoading"
            class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-50 shadow-sm hover:shadow-md transition-all cursor-pointer"
          >
            <RefreshCw v-if="authStore.isLoading" class="w-4 h-4 animate-spin" />
            <span>{{ authStore.isLoading ? 'Authenticating...' : 'Unlock & Sign In' }}</span>
            <ArrowRight v-if="!authStore.isLoading" class="w-3.5 h-3.5" />
          </button>
        </form>

        <div class="text-center pt-1 border-t border-slate-100">
          <router-link to="/register" class="text-xs text-slate-600 hover:text-brand-600 font-medium transition-colors">
            Don't have an encrypted vault? Create an account
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>


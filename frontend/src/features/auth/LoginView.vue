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
  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden selection:bg-brand-600 selection:text-white">
    <!-- Ambient background soft glow -->
    <div class="absolute inset-0 pointer-events-none -z-10 flex items-center justify-center">
      <div class="w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-3xl"></div>
    </div>

    <!-- Header Branding -->
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2 relative z-10">
      <router-link to="/" class="inline-flex items-center space-x-2.5 group">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-500 flex items-center justify-center shadow-md shadow-brand-500/25 group-hover:scale-105 transition-transform duration-200">
          <Lock class="w-5 h-5 text-white" />
        </div>
        <div class="flex flex-col text-left">
          <span class="text-xl font-bold tracking-tight text-slate-900 leading-none">SmartSpace</span>
          <span class="text-[10px] text-slate-400 font-mono mt-0.5">smartspacedata.com</span>
        </div>
      </router-link>
      <h1 class="text-2xl font-bold tracking-tight text-slate-900 mt-2">Sign in to your account</h1>
      <p class="text-sm text-slate-500">Access your zero-knowledge vault or administrative portal</p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-[440px] relative z-10">
      <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xl shadow-slate-200/50 p-7 sm:p-9 space-y-6">
        <!-- Error alert -->
        <div v-if="errorMessage" class="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start space-x-2.5 animate-fadeIn">
          <AlertTriangle class="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span class="leading-relaxed">{{ errorMessage }}</span>
        </div>

        <!-- Google Sign In -->
        <div class="space-y-3">
          <div v-if="authStore.googleClientId" ref="googleBtnRef" class="w-full flex justify-center"></div>
          <button
            v-else
            type="button"
            @click="triggerGooglePrompt"
            :disabled="isGoogleLoading"
            class="w-full h-11 px-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-medium text-sm flex items-center justify-center space-x-3 transition-all shadow-xs hover:shadow-sm cursor-pointer active:scale-[0.99] disabled:opacity-50"
          >
            <svg class="w-5 h-5 shrink-0" width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
            </svg>
            <span>{{ isGoogleLoading ? 'Connecting to Google...' : 'Sign in with Google' }}</span>
          </button>
        </div>

        <!-- Clean Divider (Fix for squished vertical text) -->
        <div class="relative flex items-center my-6">
          <div class="grow border-t border-slate-200"></div>
          <span class="shrink-0 px-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider select-none whitespace-nowrap">
            Or continue with password
          </span>
          <div class="grow border-t border-slate-200"></div>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1.5">Email or Username</label>
            <input
              type="text"
              v-model="email"
              required
              placeholder="Enter your email or username"
              class="w-full h-11 px-3.5 rounded-xl bg-slate-50/70 border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-500/10 transition-all"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wide">Password</label>
            </div>
            <div class="relative">
              <input
                :type="showPassword ? 'text' : 'password'"
                v-model="password"
                required
                placeholder="Enter your password"
                class="w-full h-11 px-3.5 pr-11 rounded-xl bg-slate-50/70 border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-500/10 transition-all"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                tabindex="-1"
                class="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 active:bg-slate-200 focus:outline-none transition-colors cursor-pointer"
                :title="showPassword ? 'Hide password' : 'Show password'"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
              >
                <EyeOff v-if="showPassword" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- MFA TOTP input if enabled -->
          <div v-if="mfaRequired" class="space-y-1.5 pt-1">
            <label class="block text-xs font-semibold text-blue-600 uppercase tracking-wide">Two-Factor Authentication Code</label>
            <input
              type="text"
              v-model="totpCode"
              required
              placeholder="000 000"
              class="w-full h-12 px-4 rounded-xl bg-slate-50 border border-blue-500 text-slate-900 text-center font-mono tracking-[0.3em] text-lg font-bold focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
            />
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading || isGoogleLoading"
            class="w-full h-11 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-semibold flex items-center justify-center space-x-2 shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.99] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed group mt-2"
          >
            <RefreshCw v-if="authStore.isLoading" class="w-4 h-4 animate-spin" />
            <span>{{ authStore.isLoading ? 'Authenticating...' : 'Unlock & Sign In' }}</span>
            <ArrowRight v-if="!authStore.isLoading" class="w-4 h-4 ml-0.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </form>

        <div class="text-center pt-2 border-t border-slate-100">
          <p class="text-sm text-slate-500">
            Don't have an encrypted vault?
            <router-link to="/register" class="font-semibold text-blue-600 hover:text-blue-700 hover:underline transition-colors ml-1">
              Create an account
            </router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>


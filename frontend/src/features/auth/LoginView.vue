<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { Cloud, Lock, AlertTriangle, ArrowRight } from "lucide-vue-next";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const email = ref("demo@speedcloud.local");
const password = ref("SpeedCloud2026!");
const totpCode = ref("");
const mfaRequired = ref(false);
const errorMessage = ref("");

async function handleLogin() {
  errorMessage.value = "";
  try {
    const res = await authStore.login(email.value, password.value, totpCode.value);
    if (res.mfaRequired) {
      mfaRequired.value = true;
      return;
    }

    const redirectPath = (route.query.redirect as string) || "/app/files";
    router.push(redirectPath);
  } catch (err: any) {
    errorMessage.value = err.message || "Invalid credentials or vault unlock failure.";
  }
}
</script>

<template>
  <div class="min-h-screen bg-[#070D1A] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-3">
      <router-link to="/" class="inline-flex items-center space-x-2">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-accent-orange flex items-center justify-center shadow-lg shadow-brand-500/20">
          <Cloud class="w-6 h-6 text-white fill-white/20" />
        </div>
        <span class="text-2xl font-black text-white">SpeedCloud</span>
      </router-link>
      <h2 class="text-2xl font-extrabold text-white">Sign in to your vault</h2>
      <p class="text-xs text-slate-400">Zero-knowledge client decryption will run in your browser.</p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-6">
        <!-- Error alert -->
        <div v-if="errorMessage" class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle class="w-4 h-4 shrink-0" />
          <span>{{ errorMessage }}</span>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
            <input
              type="email"
              v-model="email"
              required
              class="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-xs font-semibold text-slate-300">Vault Password</label>
            </div>
            <input
              type="password"
              v-model="password"
              required
              class="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:border-brand-500"
            />
          </div>

          <!-- MFA TOTP input if enabled -->
          <div v-if="mfaRequired">
            <label class="block text-xs font-semibold text-brand-400 mb-1">Two-Factor Authentication Code</label>
            <input
              type="text"
              v-model="totpCode"
              required
              placeholder="6-digit code"
              class="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-brand-500 text-white text-center font-mono tracking-widest text-lg focus:outline-none"
            />
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading"
            class="w-full py-3.5 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 disabled:opacity-50 shadow-lg shadow-brand-600/30 transition-all flex items-center justify-center space-x-2"
          >
            <span>{{ authStore.isLoading ? 'Unwrapping Vault...' : 'Unlock & Sign In' }}</span>
            <ArrowRight class="w-4 h-4" />
          </button>
        </form>

        <!-- Demo Account Helper Box -->
        <div class="p-3.5 rounded-2xl bg-brand-950/40 border border-brand-800/50 text-xs text-slate-300 space-y-1">
          <div class="font-bold text-brand-400 flex items-center space-x-1.5">
            <Lock class="w-3.5 h-3.5" />
            <span>Pre-filled Demo Credentials</span>
          </div>
          <p class="text-[11px] text-slate-400">
            Email: <code class="text-white font-mono">demo@speedcloud.local</code><br />
            Password: <code class="text-white font-mono">SpeedCloud2026!</code>
          </p>
        </div>

        <div class="text-center pt-1">
          <router-link to="/register" class="text-xs text-slate-400 hover:text-brand-400">
            Don't have an account? Sign up
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

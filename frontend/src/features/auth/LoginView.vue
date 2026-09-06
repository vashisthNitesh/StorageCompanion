<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { Lock, AlertTriangle, ArrowRight, RefreshCw, KeyRound } from "lucide-vue-next";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const email = ref("demo@smartspacedata.com");
const password = ref("SmartSpace2026!");
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
    errorMessage.value = err.message || "Invalid credentials or vault decryption failure.";
  }
}
</script>

<template>
  <div class="min-h-screen bg-surface-ground flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 selection:bg-brand-600 selection:text-white">
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2">
      <router-link to="/" class="inline-flex items-center space-x-2.5 group">
        <div class="w-8 h-8 rounded-lg bg-brand-600 border border-white/20 flex items-center justify-center shadow-sm">
          <Lock class="w-4 h-4 text-white" />
        </div>
        <div class="flex flex-col text-left">
          <span class="text-lg font-bold tracking-tight text-white leading-none">SmartSpace</span>
          <span class="text-[9px] text-slate-400 font-mono">smartspacedata.com</span>
        </div>
      </router-link>
      <h1 class="text-xl font-bold text-white tracking-tight">Unlock your encrypted vault</h1>
      <p class="text-xs text-slate-400">Zero-knowledge client decryption will execute inside your browser.</p>
    </div>

    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="vault-panel p-6 sm:p-8 rounded-2xl border border-surface-border space-y-5">
        <!-- Error alert -->
        <div v-if="errorMessage" class="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex items-start space-x-2.5">
          <AlertTriangle class="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span class="leading-relaxed">{{ errorMessage }}</span>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
            <input
              type="email"
              v-model="email"
              required
              class="w-full px-3.5 py-2.5 rounded-lg bg-surface-card border border-surface-border text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-xs font-medium text-slate-300">Vault Password</label>
            </div>
            <input
              type="password"
              v-model="password"
              required
              class="w-full px-3.5 py-2.5 rounded-lg bg-surface-card border border-surface-border text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <!-- MFA TOTP input if enabled -->
          <div v-if="mfaRequired" class="space-y-1">
            <label class="block text-xs font-medium text-brand-400">Two-Factor Authentication Code</label>
            <input
              type="text"
              v-model="totpCode"
              required
              placeholder="000 000"
              class="w-full px-3.5 py-2.5 rounded-lg bg-surface-card border border-brand-500 text-white text-center font-mono tracking-widest text-base focus:outline-none"
            />
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading"
            class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw v-if="authStore.isLoading" class="w-4 h-4 animate-spin" />
            <span>{{ authStore.isLoading ? 'Unwrapping Vault...' : 'Unlock & Sign In' }}</span>
            <ArrowRight v-if="!authStore.isLoading" class="w-3.5 h-3.5" />
          </button>
        </form>

        <!-- Demo Credentials Callout -->
        <div class="p-3.5 rounded-xl bg-surface-card border border-surface-border text-xs text-slate-300 space-y-1">
          <div class="font-medium text-brand-400 flex items-center space-x-1.5">
            <KeyRound class="w-3.5 h-3.5" />
            <span>Creator Demo Credentials (Value Pack)</span>
          </div>
          <p class="text-[11px] text-slate-400">
            Email: <code class="text-white font-mono">demo@smartspacedata.com</code><br />
            Password: <code class="text-white font-mono">SmartSpace2026!</code>
          </p>
        </div>

        <div class="text-center pt-1 border-t border-surface-border/60">
          <router-link to="/register" class="text-xs text-slate-400 hover:text-white transition-colors">
            Don't have an encrypted vault? Select a plan
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

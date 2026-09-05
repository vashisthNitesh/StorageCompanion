<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore } from "../../stores/billing";
import {
  Lock,
  Key,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Download,
  AlertTriangle,
  ArrowRight,
  CreditCard,
  RefreshCw,
} from "lucide-vue-next";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const billingStore = useBillingStore();

const email = ref("");
const fullName = ref("");
const password = ref("");
const confirmPassword = ref("");
const selectedPlan = ref<string>((route.query.plan as string) || "personal");
const billingInterval = ref<"monthly" | "yearly">((route.query.interval as "monthly" | "yearly") || "monthly");

const step = ref<"details" | "recovery_phrase" | "subscription">("details");
const recoveryWords = ref<string[]>([]);
const hasSavedPhrase = ref(false);
const errorMessage = ref("");
const copied = ref(false);

async function handleRegister() {
  errorMessage.value = "";
  if (password.value !== confirmPassword.value) {
    errorMessage.value = "Passwords do not match.";
    return;
  }
  if (password.value.length < 10) {
    errorMessage.value = "Password must be at least 10 characters long.";
    return;
  }

  try {
    const result = await authStore.register(email.value, password.value, fullName.value);
    recoveryWords.value = result.recoveryWords;
    step.value = "recovery_phrase";
  } catch (err: any) {
    errorMessage.value = err.message || "Registration failed. Please verify your details.";
  }
}

function copyPhrase() {
  navigator.clipboard.writeText(recoveryWords.value.join(" "));
  copied.value = true;
  setTimeout(() => (copied.value = false), 2500);
}

function downloadPhraseFile() {
  const content = `SPEEDCLOUD 24-WORD ZERO-KNOWLEDGE RECOVERY PHRASE\n` +
    `====================================================\n` +
    `Account: ${email.value}\n` +
    `Generated: ${new Date().toUTCString()}\n\n` +
    `CRITICAL SECURITY NOTICE:\n` +
    `Keep these 24 words strictly private and offline.\n` +
    `SpeedCloud operators CANNOT reset your vault password or recover encrypted files.\n` +
    `This phrase is the mathematical root key to reconstruct your master decryption key.\n\n` +
    `${recoveryWords.value.map((w, i) => `${String(i + 1).padStart(2, "0")}. ${w}`).join("\n")}\n`;

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `speedcloud-recovery-phrase-${email.value.split("@")[0]}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

function proceedToSubscription() {
  if (!hasSavedPhrase.value) {
    errorMessage.value = "Please confirm you have safely stored your 24-word recovery phrase.";
    return;
  }
  errorMessage.value = "";
  step.value = "subscription";
}

async function initiateCheckout() {
  errorMessage.value = "";
  try {
    await billingStore.checkout(selectedPlan.value, billingInterval.value);
    // Verified payment completes subscription; navigate to vault
    router.push("/app/files");
  } catch (err: any) {
    errorMessage.value = err.message || "Payment could not be processed. Please retry.";
  }
}
</script>

<template>
  <div class="min-h-screen bg-surface-ground flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 selection:bg-brand-600 selection:text-white">
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center space-y-2.5">
      <router-link to="/" class="inline-flex items-center space-x-2.5 group">
        <div class="w-8 h-8 rounded-lg bg-brand-600 border border-white/20 flex items-center justify-center shadow-sm">
          <Lock class="w-4 h-4 text-white" />
        </div>
        <span class="text-xl font-bold tracking-tight text-white">SpeedCloud</span>
      </router-link>

      <h1 class="text-xl font-bold text-white tracking-tight">
        {{ step === 'details' ? 'Create your zero-knowledge vault' : step === 'recovery_phrase' ? 'Save your 24-word recovery key' : 'Activate your subscription' }}
      </h1>
      <p class="text-xs text-slate-400">
        {{ step === 'details' ? 'Your master encryption key is derived client-side with Argon2id.' : step === 'recovery_phrase' ? 'Your only way to restore account access if you lose your password.' : 'SpeedCloud is an ad-free, pure subscription service.' }}
      </p>
    </div>

    <!-- Step Progress Indicator -->
    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-md flex items-center justify-between px-6 text-xs text-slate-400 font-mono">
      <div class="flex items-center space-x-1.5" :class="step === 'details' ? 'text-brand-400 font-bold' : 'text-slate-500'">
        <span class="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">1</span>
        <span>Account</span>
      </div>
      <div class="h-px w-8 bg-surface-border"></div>
      <div class="flex items-center space-x-1.5" :class="step === 'recovery_phrase' ? 'text-brand-400 font-bold' : 'text-slate-500'">
        <span class="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">2</span>
        <span>Recovery</span>
      </div>
      <div class="h-px w-8 bg-surface-border"></div>
      <div class="flex items-center space-x-1.5" :class="step === 'subscription' ? 'text-brand-400 font-bold' : 'text-slate-500'">
        <span class="w-5 h-5 rounded-full border border-current flex items-center justify-center text-[10px]">3</span>
        <span>Subscription</span>
      </div>
    </div>

    <div class="mt-4 sm:mx-auto sm:w-full" :class="step === 'recovery_phrase' ? 'sm:max-w-2xl' : 'sm:max-w-md'">
      <div class="vault-panel p-6 sm:p-8 rounded-2xl border border-surface-border space-y-5">
        <!-- Error Alert -->
        <div v-if="errorMessage" class="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex items-start space-x-2.5">
          <AlertTriangle class="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span class="leading-relaxed">{{ errorMessage }}</span>
        </div>

        <!-- Step 1: Account Details -->
        <form v-if="step === 'details'" @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              v-model="fullName"
              placeholder="e.g. Rajesh Kumar"
              class="w-full px-3.5 py-2.5 rounded-lg bg-surface-card border border-surface-border text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Email Address</label>
            <input
              type="email"
              v-model="email"
              required
              placeholder="you@domain.com"
              class="w-full px-3.5 py-2.5 rounded-lg bg-surface-card border border-surface-border text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Vault Password</label>
            <input
              type="password"
              v-model="password"
              required
              minlength="10"
              placeholder="Minimum 10 characters"
              class="w-full px-3.5 py-2.5 rounded-lg bg-surface-card border border-surface-border text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
            <p class="text-[11px] text-slate-500 mt-1">This password derives your root 256-bit encryption key.</p>
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Confirm Password</label>
            <input
              type="password"
              v-model="confirmPassword"
              required
              minlength="10"
              placeholder="Re-enter password"
              class="w-full px-3.5 py-2.5 rounded-lg bg-surface-card border border-surface-border text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>

          <!-- Plan Picker -->
          <div class="pt-2">
            <label class="block text-xs font-medium text-slate-300 mb-2">Initial Subscription Tier</label>
            <div class="grid grid-cols-2 gap-3">
              <div
                @click="selectedPlan = 'personal'"
                class="p-3 rounded-xl border cursor-pointer transition-all text-xs"
                :class="selectedPlan === 'personal' ? 'border-brand-500 bg-brand-950/30' : 'border-surface-border bg-surface-card hover:border-slate-700'"
              >
                <div class="font-semibold text-white">Personal Plan</div>
                <div class="text-brand-400 font-mono font-bold mt-0.5">₹199 / mo</div>
                <div class="text-[10px] text-slate-400 mt-0.5">200 GB Storage</div>
              </div>

              <div
                @click="selectedPlan = 'business'"
                class="p-3 rounded-xl border cursor-pointer transition-all text-xs"
                :class="selectedPlan === 'business' ? 'border-brand-500 bg-brand-950/30' : 'border-surface-border bg-surface-card hover:border-slate-700'"
              >
                <div class="font-semibold text-white">Business Plan</div>
                <div class="text-brand-400 font-mono font-bold mt-0.5">₹499 / mo</div>
                <div class="text-[10px] text-slate-400 mt-0.5">2 TB Storage</div>
              </div>
            </div>
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading"
            class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <span>{{ authStore.isLoading ? 'Generating Keys (Argon2id)...' : 'Continue to Recovery Key' }}</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </form>

        <!-- Step 2: 24-Word Recovery Phrase -->
        <div v-else-if="step === 'recovery_phrase'" class="space-y-5">
          <div class="p-3.5 rounded-xl bg-amber-950/30 border border-amber-800/50 text-xs text-amber-200 space-y-1">
            <div class="flex items-center space-x-1.5 font-bold text-amber-400">
              <Key class="w-4 h-4" />
              <span>Offline Master Recovery Key</span>
            </div>
            <p class="leading-relaxed">
              Write down or save these 24 words in order. SpeedCloud cannot recover your files if you lose both your password and this phrase.
            </p>
          </div>

          <!-- Words Grid -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3.5 rounded-xl bg-surface-card border border-surface-border">
            <div
              v-for="(word, index) in recoveryWords"
              :key="index"
              class="px-2.5 py-1.5 rounded-lg bg-surface-elevated border border-surface-border flex items-center justify-between text-xs"
            >
              <span class="text-slate-500 font-mono text-[10px]">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="font-mono font-bold text-brand-300">{{ word }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center space-x-3">
            <button
              type="button"
              @click="copyPhrase"
              class="flex-1 btn-secondary py-2.5 rounded-lg text-xs font-medium text-slate-200 flex items-center justify-center space-x-1.5"
            >
              <Copy class="w-3.5 h-3.5 text-brand-400" />
              <span>{{ copied ? 'Copied to Clipboard' : 'Copy Words' }}</span>
            </button>
            <button
              type="button"
              @click="downloadPhraseFile"
              class="flex-1 btn-secondary py-2.5 rounded-lg text-xs font-medium text-slate-200 flex items-center justify-center space-x-1.5"
            >
              <Download class="w-3.5 h-3.5 text-brand-400" />
              <span>Download Backup (.txt)</span>
            </button>
          </div>

          <!-- Confirmation Checkbox -->
          <label class="flex items-start space-x-2.5 cursor-pointer pt-1">
            <input
              type="checkbox"
              v-model="hasSavedPhrase"
              class="mt-0.5 w-4 h-4 rounded border-surface-border bg-surface-card text-brand-600 focus:ring-brand-500"
            />
            <span class="text-xs text-slate-300 leading-relaxed">
              I have saved my 24 words in a secure location. I acknowledge that SpeedCloud cannot reset my vault password.
            </span>
          </label>

          <button
            type="button"
            @click="proceedToSubscription"
            :disabled="!hasSavedPhrase"
            class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Proceed to Subscription Checkout</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Step 3: Subscription & Razorpay Activation Gate -->
        <div v-else-if="step === 'subscription'" class="space-y-5">
          <div class="p-4 rounded-xl bg-surface-card border border-surface-border space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-white">
                {{ selectedPlan === 'personal' ? 'Personal Vault (200 GB)' : 'Business Vault (2 TB)' }}
              </span>
              <span class="text-sm font-mono font-bold text-brand-400">
                ₹{{ billingInterval === 'yearly' ? (selectedPlan === 'personal' ? '1,999 / yr' : '4,999 / yr') : (selectedPlan === 'personal' ? '199 / mo' : '499 / mo') }}
              </span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Your cryptographic keys are prepared. Complete payment via Razorpay to activate your storage allocation and unlock your encrypted vault.
            </p>
          </div>

          <!-- Payment Methods Banner -->
          <div class="p-3 rounded-lg bg-surface-elevated border border-surface-border flex items-center justify-between text-[11px] text-slate-400">
            <div class="flex items-center space-x-1.5 text-slate-300">
              <CreditCard class="w-3.5 h-3.5 text-brand-400" />
              <span>Razorpay Instant Checkout</span>
            </div>
            <span>UPI • Cards • Netbanking</span>
          </div>

          <button
            type="button"
            @click="initiateCheckout"
            :disabled="billingStore.isLoading"
            class="w-full btn-primary py-3.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw v-if="billingStore.isLoading" class="w-4 h-4 animate-spin" />
            <span>{{ billingStore.isLoading ? 'Launching Razorpay...' : 'Pay with Razorpay / UPI' }}</span>
            <ArrowRight v-if="!billingStore.isLoading" class="w-3.5 h-3.5" />
          </button>

          <p class="text-[11px] text-center text-slate-500">
            100% money-back guarantee within 7 days. Cancel anytime.
          </p>
        </div>

        <div class="text-center pt-1 border-t border-surface-border/60">
          <router-link to="/login" class="text-xs text-slate-400 hover:text-white transition-colors">
            Already have an active account? Log in
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
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
  Zap,
} from "lucide-vue-next";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const billingStore = useBillingStore();

const email = ref("");
const fullName = ref("");
const password = ref("");
const confirmPassword = ref("");
const selectedPlan = ref<string>((route.query.plan as string) || "value");
const billingInterval = ref<"monthly" | "yearly">((route.query.interval as "monthly" | "yearly") || "monthly");

const step = ref<"details" | "recovery_phrase" | "subscription">("details");
const recoveryWords = ref<string[]>([]);
const hasSavedPhrase = ref(false);
const errorMessage = ref("");
const copied = ref(false);

const planDetailsMap: Record<string, { name: string; storage: string; monthly: string; yearly: string; desc: string }> = {
  entry: { name: "Entry Pack", storage: "25 GB", monthly: "₹39", yearly: "₹390", desc: "Essential documents & receipts" },
  smart: { name: "Smart Pack", storage: "100 GB", monthly: "₹89", yearly: "₹890", desc: "Student & creator archives" },
  value: { name: "Value Pack", storage: "200 GB", monthly: "₹149", yearly: "₹1,490", desc: "Hero pack: Wedding & 4K video" },
  super: { name: "Super Pack", storage: "400 GB", monthly: "₹249", yearly: "₹2,490", desc: "Studio & production teams" },
  mega: { name: "Mega Pack", storage: "1 TB", monthly: "₹449", yearly: "₹4,490", desc: "Max enterprise volume" },
};

const currentPlanInfo = computed(() => {
  return planDetailsMap[selectedPlan.value] || planDetailsMap["value"];
});

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
  const content = `SMARTSPACE DATA 24-WORD ZERO-KNOWLEDGE RECOVERY PHRASE\n` +
    `======================================================\n` +
    `Service: smartspacedata.com\n` +
    `Account: ${email.value}\n` +
    `Generated: ${new Date().toUTCString()}\n\n` +
    `CRITICAL PRIVACY NOTICE (DPDP Act Adherence):\n` +
    `Keep these 24 words strictly private and offline.\n` +
    `SmartSpace Data operators CANNOT reset your vault password or view your encrypted files.\n` +
    `This phrase is the mathematical root key to reconstruct your master decryption key.\n\n` +
    `${recoveryWords.value.map((w, i) => `${String(i + 1).padStart(2, "0")}. ${w}`).join("\n")}\n`;

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `smartspace-recovery-phrase-${email.value.split("@")[0]}.txt`;
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
    router.push("/app/files");
  } catch (err: any) {
    errorMessage.value = err.message || "Payment could not be processed. Please retry.";
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

      <h1 class="text-xl font-bold text-white tracking-tight">
        {{ step === 'details' ? 'Create your encrypted vault' : step === 'recovery_phrase' ? 'Save your 24-word recovery key' : 'Activate your subscription' }}
      </h1>
      <p class="text-xs text-slate-400">
        {{ step === 'details' ? 'Your master encryption key is derived client-side with Argon2id.' : step === 'recovery_phrase' ? 'Your only way to restore account access if you lose your password.' : 'SmartSpace Data is an uncompressed, zero-egress cloud service.' }}
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
        <span>Activation</span>
      </div>
    </div>

    <div class="mt-4 sm:mx-auto sm:w-full" :class="step === 'recovery_phrase' ? 'sm:max-w-2xl' : 'sm:max-w-lg'">
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
              placeholder="e.g. Aman Sharma"
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
            <p class="text-[11px] text-slate-500 mt-1">Derives your 256-bit zero-knowledge encryption key.</p>
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

          <!-- 5 Plan Selector Picker -->
          <div class="pt-2 space-y-2">
            <div class="flex items-center justify-between">
              <label class="block text-xs font-medium text-slate-300">Select 'Paisa Vasool' Plan</label>
              <span class="text-[10px] text-brand-400 font-mono font-semibold">100% RAW • Zero Egress</span>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <div
                v-for="(info, code) in planDetailsMap"
                :key="code"
                @click="selectedPlan = code"
                class="p-2.5 rounded-xl border cursor-pointer transition-all text-left flex flex-col justify-between"
                :class="selectedPlan === code ? 'border-brand-500 bg-brand-950/40 ring-1 ring-brand-500/50' : 'border-surface-border bg-surface-card hover:border-slate-700'"
              >
                <div>
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-white text-xs">{{ info.name }}</span>
                    <span v-if="code === 'value'" class="text-[8px] px-1 py-0.2 rounded bg-brand-600 text-white font-bold">HERO</span>
                  </div>
                  <div class="text-[10px] text-slate-400 mt-0.5">{{ info.storage }}</div>
                </div>
                <div class="text-brand-400 font-mono font-bold text-xs mt-1.5">
                  {{ info.monthly }} <span class="text-[9px] text-slate-500 font-normal">/mo</span>
                </div>
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
              Save these 24 words in order. SmartSpace Data cannot recover your files if you lose both your password and this phrase.
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
              I have saved my 24 words securely. I acknowledge that smartspacedata.com operates on zero-knowledge and cannot reset my vault password.
            </span>
          </label>

          <button
            type="button"
            @click="proceedToSubscription"
            :disabled="!hasSavedPhrase"
            class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Proceed to 1-Click UPI Activation</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Step 3: Subscription & Razorpay Activation Gate -->
        <div v-else-if="step === 'subscription'" class="space-y-5">
          <div class="p-4 rounded-xl bg-surface-card border border-surface-border space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-white">
                {{ currentPlanInfo.name }} ({{ currentPlanInfo.storage }})
              </span>
              <span class="text-sm font-mono font-bold text-brand-400">
                {{ billingInterval === 'yearly' ? currentPlanInfo.yearly + ' / yr' : currentPlanInfo.monthly + ' / mo' }}
              </span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              {{ currentPlanInfo.desc }}. Zero egress fees. Complete 1-Click payment via Razorpay to allocate your cloud storage.
            </p>
          </div>

          <!-- Payment Methods Banner -->
          <div class="p-3 rounded-lg bg-surface-elevated border border-surface-border flex items-center justify-between text-[11px] text-slate-400">
            <div class="flex items-center space-x-1.5 text-slate-300">
              <CreditCard class="w-3.5 h-3.5 text-brand-400" />
              <span>Razorpay 1-Click Native</span>
            </div>
            <span class="font-mono text-accent-emerald font-semibold">UPI • Cards • Netbanking</span>
          </div>

          <button
            type="button"
            @click="initiateCheckout"
            :disabled="billingStore.isLoading"
            class="w-full btn-primary py-3.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw v-if="billingStore.isLoading" class="w-4 h-4 animate-spin" />
            <span>{{ billingStore.isLoading ? 'Launching Razorpay Checkout...' : `Pay ${billingInterval === 'yearly' ? currentPlanInfo.yearly : currentPlanInfo.monthly} via UPI / Cards` }}</span>
            <ArrowRight v-if="!billingStore.isLoading" class="w-3.5 h-3.5" />
          </button>

          <div class="text-[11px] text-center text-slate-400 space-y-1">
            <p>₹149 means ₹149. All-inclusive (18% GST & Gateway charges included).</p>
            <p class="text-slate-500">Note: 15-day inactivity clean-up protocol applies to unrenewed accounts.</p>
          </div>
        </div>

        <div class="text-center pt-1 border-t border-surface-border/60">
          <router-link to="/login" class="text-xs text-slate-400 hover:text-white transition-colors">
            Already have an active account? Log In
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

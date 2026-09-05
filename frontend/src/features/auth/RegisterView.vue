<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore } from "../../stores/billing";
import {
  Cloud,
  Lock,
  Key,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Download,
  AlertTriangle,
  ArrowRight,
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
    errorMessage.value = "Password must be at least 10 characters.";
    return;
  }

  try {
    const result = await authStore.register(email.value, password.value, fullName.value);
    recoveryWords.value = result.recoveryWords;
    step.value = "recovery_phrase";
  } catch (err: any) {
    errorMessage.value = err.message || "Registration failed. Please try again.";
  }
}

function copyPhrase() {
  navigator.clipboard.writeText(recoveryWords.value.join(" "));
  copied.value = true;
  setTimeout(() => (copied.value = false), 2500);
}

function downloadPhraseFile() {
  const content = `SPEEDCLOUD 24-WORD ZERO-KNOWLEDGE RECOVERY PHRASE\n` +
    `Account: ${email.value}\n` +
    `Date: ${new Date().toISOString()}\n\n` +
    `WARNING: Keep these 24 words strictly private and offline.\n` +
    `SpeedCloud operators cannot reset your password without this phrase.\n\n` +
    `${recoveryWords.value.map((w, i) => `${i + 1}. ${w}`).join("\n")}\n`;

  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `SpeedCloud-Recovery-Phrase-${email.value.split("@")[0]}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

async function proceedToSubscription() {
  if (!hasSavedPhrase.value) {
    errorMessage.value = "You must confirm you have saved your recovery phrase.";
    return;
  }
  step.value = "subscription";
}

async function initiateCheckout() {
  try {
    await billingStore.checkout(selectedPlan.value, billingInterval.value);
    // On successful payment, navigate to files
    router.push("/app/files");
  } catch (err: any) {
    errorMessage.value = err.message || "Payment checkout failed.";
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
      <h2 class="text-2xl font-extrabold text-white">
        {{ step === 'details' ? 'Create your encrypted vault' : step === 'recovery_phrase' ? 'Save your 24-word recovery key' : 'Activate your subscription' }}
      </h2>
      <p class="text-xs text-slate-400">
        {{ step === 'details' ? 'End-to-end client-side encryption. No free tier compromises.' : step === 'recovery_phrase' ? 'This is your ONLY way to recover your files if you forget your password.' : 'Select your plan and complete setup via Razorpay.' }}
      </p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full" :class="step === 'recovery_phrase' ? 'sm:max-w-2xl' : 'sm:max-w-md'">
      <div class="glass-panel p-8 rounded-3xl border border-slate-800 shadow-2xl space-y-6">
        <!-- Error Alert -->
        <div v-if="errorMessage" class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle class="w-4 h-4 shrink-0" />
          <span>{{ errorMessage }}</span>
        </div>

        <!-- Step 1: Account Details -->
        <form v-if="step === 'details'" @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              v-model="fullName"
              placeholder="e.g. Rajesh Kumar"
              class="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
            <input
              type="email"
              v-model="email"
              required
              placeholder="you@example.com"
              class="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Vault Password</label>
            <input
              type="password"
              v-model="password"
              required
              minlength="10"
              placeholder="At least 10 characters"
              class="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:border-brand-500"
            />
            <p class="text-[11px] text-slate-500 mt-1">Used to derive your 256-bit KEK via Argon2id WebAssembly.</p>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Confirm Password</label>
            <input
              type="password"
              v-model="confirmPassword"
              required
              minlength="10"
              placeholder="Confirm password"
              class="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:border-brand-500"
            />
          </div>

          <!-- Plan Selection Picker -->
          <div class="pt-2">
            <label class="block text-xs font-semibold text-slate-300 mb-2">Select Subscription Plan</label>
            <div class="grid grid-cols-2 gap-3">
              <div
                @click="selectedPlan = 'personal'"
                class="p-3 rounded-xl border cursor-pointer transition-all text-xs"
                :class="selectedPlan === 'personal' ? 'border-brand-500 bg-brand-500/10' : 'border-slate-800 bg-slate-900/40'"
              >
                <div class="font-bold text-white">Personal Plan</div>
                <div class="text-brand-400 font-mono font-bold mt-1">₹199 / mo</div>
                <div class="text-[10px] text-slate-400 mt-0.5">200 GB Storage</div>
              </div>

              <div
                @click="selectedPlan = 'business'"
                class="p-3 rounded-xl border cursor-pointer transition-all text-xs"
                :class="selectedPlan === 'business' ? 'border-brand-500 bg-brand-500/10' : 'border-slate-800 bg-slate-900/40'"
              >
                <div class="font-bold text-white">Business Plan</div>
                <div class="text-brand-400 font-mono font-bold mt-1">₹499 / mo</div>
                <div class="text-[10px] text-slate-400 mt-0.5">2 TB Storage</div>
              </div>
            </div>
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading"
            class="w-full py-3.5 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 disabled:opacity-50 shadow-lg shadow-brand-600/30 transition-all flex items-center justify-center space-x-2"
          >
            <span>{{ authStore.isLoading ? 'Deriving Keys...' : 'Continue to Recovery Key' }}</span>
            <ArrowRight class="w-4 h-4" />
          </button>
        </form>

        <!-- Step 2: Hard Gate Recovery Phrase -->
        <div v-else-if="step === 'recovery_phrase'" class="space-y-6">
          <div class="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200 space-y-1.5">
            <div class="flex items-center space-x-1.5 font-bold text-amber-400">
              <AlertTriangle class="w-4 h-4" />
              <span>Hard Gate — Write Down These 24 Words</span>
            </div>
            <p>
              If you ever forget your password, our server cannot reset it for you. This 24-word phrase is the master cryptographic recovery mechanism for your vault.
            </p>
          </div>

          <!-- 24-word grid -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-4 rounded-2xl bg-slate-900/90 border border-slate-800">
            <div
              v-for="(word, index) in recoveryWords"
              :key="index"
              class="px-2.5 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 flex items-center justify-between text-xs"
            >
              <span class="text-slate-500 font-mono text-[10px]">{{ index + 1 }}</span>
              <span class="font-mono font-bold text-brand-300">{{ word }}</span>
            </div>
          </div>

          <!-- Copy & Download buttons -->
          <div class="flex items-center space-x-3">
            <button
              type="button"
              @click="copyPhrase"
              class="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700 flex items-center justify-center space-x-2 transition-all"
            >
              <Copy class="w-4 h-4 text-brand-400" />
              <span>{{ copied ? 'Copied to Clipboard!' : 'Copy Phrase' }}</span>
            </button>
            <button
              type="button"
              @click="downloadPhraseFile"
              class="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700 flex items-center justify-center space-x-2 transition-all"
            >
              <Download class="w-4 h-4 text-brand-400" />
              <span>Download .txt File</span>
            </button>
          </div>

          <!-- Checkbox Hard Gate -->
          <label class="flex items-start space-x-3 cursor-pointer pt-2">
            <input
              type="checkbox"
              v-model="hasSavedPhrase"
              class="mt-1 w-4 h-4 rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-brand-500"
            />
            <span class="text-xs text-slate-300 leading-relaxed">
              I have safely backed up my 24-word recovery phrase. I understand that SpeedCloud cannot recover my account or files if I lose both my password and this phrase.
            </span>
          </label>

          <button
            type="button"
            @click="proceedToSubscription"
            :disabled="!hasSavedPhrase"
            class="w-full py-3.5 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-brand-600/30 transition-all flex items-center justify-center space-x-2"
          >
            <span>Proceed to Subscription Activation</span>
            <ArrowRight class="w-4 h-4" />
          </button>
        </div>

        <!-- Step 3: Subscription Checkout Gate -->
        <div v-else-if="step === 'subscription'" class="space-y-6">
          <div class="p-4 rounded-2xl bg-brand-950/60 border border-brand-800/80 text-xs text-slate-300 space-y-2">
            <div class="flex items-center justify-between text-white font-bold text-sm">
              <span>{{ selectedPlan === 'personal' ? 'Personal Plan (200 GB)' : 'Business Plan (2 TB)' }}</span>
              <span class="text-brand-400 font-mono font-black">
                ₹{{ billingInterval === 'yearly' ? (selectedPlan === 'personal' ? '1,999' : '4,999') : (selectedPlan === 'personal' ? '199' : '499') }}
              </span>
            </div>
            <p class="text-[11px] text-slate-400">
              Zero-knowledge vault initialized. Activate your plan with Razorpay (UPI, GooglePay, PhonePe, Cards, Netbanking) to start uploading.
            </p>
          </div>

          <button
            type="button"
            @click="initiateCheckout"
            :disabled="billingStore.isLoading"
            class="w-full py-4 rounded-xl font-bold text-white bg-gradient-to-r from-accent-orange to-amber-500 hover:from-orange-600 hover:to-amber-600 shadow-xl shadow-orange-500/25 transition-all flex items-center justify-center space-x-2"
          >
            <span>{{ billingStore.isLoading ? 'Opening Razorpay...' : 'Pay with Razorpay / UPI' }}</span>
            <ArrowRight class="w-4 h-4" />
          </button>
        </div>

        <!-- Bottom Link -->
        <div class="text-center pt-2">
          <router-link to="/login" class="text-xs text-slate-400 hover:text-brand-400">
            Already have an account? Log in
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

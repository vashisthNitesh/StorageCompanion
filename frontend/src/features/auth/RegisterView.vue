<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore } from "../../stores/billing";
import {
  Lock,
  AlertTriangle,
  ArrowRight,
  CreditCard,
  RefreshCw,
  Eye,
  EyeOff,
} from "lucide-vue-next";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const billingStore = useBillingStore();

const email = ref("");
const fullName = ref("");
const password = ref("");
const confirmPassword = ref("");
const showPassword = ref(false);
const showConfirmPassword = ref(false);
const selectedPlan = ref<string>((route.query.plan as string) || "value");
const billingInterval = ref<"monthly" | "yearly">((route.query.interval as "monthly" | "yearly") || "monthly");

const step = ref<"details" | "subscription">("details");
const errorMessage = ref("");
const isGoogleLoading = ref(false);
const googleBtnRef = ref<HTMLElement | null>(null);

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
        text: "signup_with",
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
    if (route.query.plan) {
      step.value = "subscription";
    } else {
      router.push("/app/files");
    }
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
    const devToken = prompt("Enter Google Test Token (or click OK for default demo user):", "mock_token_newuser");
    if (devToken) {
      handleGoogleCredentialResponse({ credential: devToken });
    }
  }
}

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
    await authStore.register(email.value, password.value, fullName.value);
    // Direct progression without any recovery words interruption
    if (route.query.plan) {
      step.value = "subscription";
    } else {
      router.push("/app/files");
    }
  } catch (err: any) {
    errorMessage.value = err.message || "Registration failed. Please verify your details.";
  }
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
  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden selection:bg-brand-600 selection:text-white">
    <!-- Ambient background soft glow -->
    <div class="absolute inset-0 pointer-events-none -z-10 flex items-center justify-center">
      <div class="w-[700px] h-[700px] bg-blue-500/5 rounded-full blur-3xl"></div>
    </div>

    <!-- Header Branding -->
    <div class="sm:mx-auto sm:w-full sm:max-w-lg text-center space-y-2 relative z-10">
      <router-link to="/" class="inline-flex items-center space-x-2.5 group">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-500 flex items-center justify-center shadow-md shadow-brand-500/25 group-hover:scale-105 transition-transform duration-200">
          <Lock class="w-5 h-5 text-white" />
        </div>
        <div class="flex flex-col text-left">
          <span class="text-xl font-bold tracking-tight text-slate-900 leading-none">SmartSpace</span>
          <span class="text-[10px] text-slate-400 font-mono mt-0.5">smartspacedata.com</span>
        </div>
      </router-link>

      <h1 class="text-2xl font-bold text-slate-900 tracking-tight mt-2">
        {{ step === 'details' ? 'Create your encrypted vault' : 'Activate your subscription' }}
      </h1>
      <p class="text-sm text-slate-500">
        {{ step === 'details' ? 'Zero-knowledge encryption with client-side key derivation.' : 'SmartSpace Data is an uncompressed, zero-egress cloud service.' }}
      </p>
    </div>

    <!-- Step Progress Indicator -->
    <div v-if="step === 'subscription'" class="mt-4 sm:mx-auto sm:w-full sm:max-w-xl flex items-center justify-center space-x-3 text-xs text-slate-500 font-mono relative z-10">
      <div class="flex items-center space-x-1.5 text-emerald-600 font-semibold">
        <span class="w-5 h-5 rounded-full bg-emerald-50 border border-emerald-500/30 flex items-center justify-center text-[10px]">✓</span>
        <span>Account Created</span>
      </div>
      <div class="h-px w-8 bg-slate-200"></div>
      <div class="flex items-center space-x-1.5 text-blue-600 font-bold">
        <span class="w-5 h-5 rounded-full bg-blue-50 border border-blue-500/30 flex items-center justify-center text-[10px]">2</span>
        <span>Plan Activation</span>
      </div>
    </div>

    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-xl relative z-10">
      <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xl shadow-slate-200/50 p-7 sm:p-9 space-y-6">
        <!-- Error Alert -->
        <div v-if="errorMessage" class="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start space-x-2.5 animate-fadeIn">
          <AlertTriangle class="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <span class="leading-relaxed">{{ errorMessage }}</span>
        </div>

        <!-- Google Sign-Up -->
        <div v-if="step === 'details'" class="space-y-3">
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
            <span>{{ isGoogleLoading ? 'Connecting to Google...' : 'Sign up with Google' }}</span>
          </button>

          <!-- Clean Divider (Fix for squished vertical text) -->
          <div class="relative flex items-center my-6">
            <div class="grow border-t border-slate-200"></div>
            <span class="shrink-0 px-3.5 text-xs font-semibold text-slate-400 uppercase tracking-wider select-none whitespace-nowrap">
              Or continue with email
            </span>
            <div class="grow border-t border-slate-200"></div>
          </div>
        </div>

        <!-- Normal Account Registration Form -->
        <form v-if="step === 'details'" @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1.5">Full Name</label>
            <input
              type="text"
              v-model="fullName"
              placeholder="e.g. Aman Sharma"
              class="w-full h-11 px-3.5 rounded-xl bg-slate-50/70 border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-500/10 transition-all"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1.5">Email Address</label>
            <input
              type="email"
              v-model="email"
              required
              placeholder="you@domain.com"
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
                minlength="10"
                placeholder="Minimum 10 characters"
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
            <p class="text-[11px] text-slate-500 mt-1.5">Derives your 256-bit zero-knowledge encryption key.</p>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wide">Confirm Password</label>
            </div>
            <div class="relative">
              <input
                :type="showConfirmPassword ? 'text' : 'password'"
                v-model="confirmPassword"
                required
                minlength="10"
                placeholder="Re-enter password"
                class="w-full h-11 px-3.5 pr-11 rounded-xl bg-slate-50/70 border border-slate-200 text-slate-900 text-sm placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-500/10 transition-all"
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                tabindex="-1"
                class="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 active:bg-slate-200 focus:outline-none transition-colors cursor-pointer"
                :title="showConfirmPassword ? 'Hide password' : 'Show password'"
                :aria-label="showConfirmPassword ? 'Hide password' : 'Show password'"
              >
                <EyeOff v-if="showConfirmPassword" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- 5 Plan Selector Picker (Optional selection during registration) -->
          <div class="pt-2 space-y-2">
            <div class="flex items-center justify-between">
              <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wide">Select Plan (Optional)</label>
              <span class="text-[10px] text-blue-700 font-mono font-bold bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">100% RAW • Zero Egress</span>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              <div
                v-for="(info, code) in planDetailsMap"
                :key="code"
                @click="selectedPlan = code"
                class="p-3 rounded-xl border cursor-pointer transition-all text-left flex flex-col justify-between"
                :class="selectedPlan === code ? 'border-blue-600 bg-blue-50/70 ring-2 ring-blue-500/20 shadow-xs' : 'border-slate-200 bg-slate-50/60 hover:bg-white hover:border-slate-300'"
              >
                <div>
                  <div class="flex items-center justify-between">
                    <span class="font-bold text-slate-900 text-xs">{{ info.name }}</span>
                    <span v-if="code === 'value'" class="text-[8px] px-1.5 py-0.5 rounded bg-blue-600 text-white font-bold tracking-wider">HERO</span>
                  </div>
                  <div class="text-[11px] text-slate-500 font-medium mt-0.5">{{ info.storage }}</div>
                </div>
                <div class="text-blue-600 font-mono font-bold text-xs mt-2">
                  {{ info.monthly }} <span class="text-[10px] text-slate-500 font-normal">/mo</span>
                </div>
              </div>
            </div>
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading || isGoogleLoading"
            class="w-full h-11 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-semibold flex items-center justify-center space-x-2 shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.99] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed group mt-2"
          >
            <RefreshCw v-if="authStore.isLoading" class="w-4 h-4 animate-spin" />
            <span>{{ authStore.isLoading ? 'Creating Encrypted Vault...' : 'Create Account & Continue' }}</span>
            <ArrowRight v-if="!authStore.isLoading" class="w-4 h-4 ml-0.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        </form>

        <!-- Subscription & Razorpay Activation Gate (If plan selected) -->
        <div v-else-if="step === 'subscription'" class="space-y-5">
          <div class="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-slate-900">
                {{ currentPlanInfo.name }} ({{ currentPlanInfo.storage }})
              </span>
              <span class="text-base font-mono font-bold text-blue-600">
                {{ billingInterval === 'yearly' ? currentPlanInfo.yearly + ' / yr' : currentPlanInfo.monthly + ' / mo' }}
              </span>
            </div>
            <p class="text-xs text-slate-600 leading-relaxed">
              {{ currentPlanInfo.desc }}. Zero egress fees. Complete 1-Click payment via Razorpay to allocate your cloud storage.
            </p>
          </div>

          <!-- Payment Methods Banner -->
          <div class="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-between text-xs text-emerald-800">
            <div class="flex items-center space-x-2">
              <CreditCard class="w-4 h-4 text-emerald-600 shrink-0" />
              <span class="font-medium">Razorpay 1-Click Native</span>
            </div>
            <span class="font-mono font-bold text-[11px]">UPI • Cards • Netbanking</span>
          </div>

          <button
            type="button"
            @click="initiateCheckout"
            :disabled="billingStore.isLoading"
            class="w-full h-11 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-semibold flex items-center justify-center space-x-2 shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 active:scale-[0.99] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <RefreshCw v-if="billingStore.isLoading" class="w-4 h-4 animate-spin" />
            <span>{{ billingStore.isLoading ? 'Launching Razorpay Checkout...' : `Pay ${billingInterval === 'yearly' ? currentPlanInfo.yearly : currentPlanInfo.monthly} via UPI / Cards` }}</span>
            <ArrowRight v-if="!billingStore.isLoading" class="w-4 h-4 ml-0.5 group-hover:translate-x-0.5 transition-transform" />
          </button>

          <div class="flex items-center justify-center pt-1">
            <router-link to="/app/files" class="text-xs text-slate-500 hover:text-slate-800 font-medium transition-colors">
              Skip for now and enter vault →
            </router-link>
          </div>

          <div class="text-[11px] text-center text-slate-500 space-y-1 pt-1">
            <p>₹149 means ₹149. All-inclusive (18% GST & Gateway charges included).</p>
            <p class="text-slate-400">Note: 15-day inactivity clean-up protocol applies to unrenewed accounts.</p>
          </div>
        </div>

        <div class="text-center pt-2 border-t border-slate-100">
          <p class="text-sm text-slate-500">
            Already have an active account?
            <router-link to="/login" class="font-semibold text-blue-600 hover:text-blue-700 hover:underline transition-colors ml-1">
              Log In
            </router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>


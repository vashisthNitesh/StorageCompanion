<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { Lock, CheckCircle2, ArrowLeft, ArrowRight, ShieldCheck, Zap } from "lucide-vue-next";

const router = useRouter();
const interval = ref<"monthly" | "yearly">("monthly");
const storageNeededGB = ref<number>(200);

const plans = [
  {
    code: "entry",
    name: "Entry Pack",
    storageGB: 25,
    storageLabel: "25 GB",
    monthlyPrice: "₹39",
    yearlyPrice: "₹390",
    description: "Essential cloud vault for documents, receipts, and personal archives.",
    features: [
      "25 GB Encrypted Storage",
      "100% Original RAW Quality",
      "Zero Egress Bandwidth Fees",
      "End-to-End Encryption",
      "1-Click UPI via Razorpay",
    ],
    badge: "Budget Friendly",
    isHero: false,
  },
  {
    code: "smart",
    name: "Smart Pack",
    storageGB: 100,
    storageLabel: "100 GB",
    monthlyPrice: "₹89",
    yearlyPrice: "₹890",
    description: "Great for students, personal photo archives, and regular creators.",
    features: [
      "100 GB Encrypted Storage",
      "100% Original RAW Quality",
      "Zero Egress Bandwidth Fees",
      "Client Decrypted Search",
      "Password-Protected Share Links",
    ],
    badge: "Student Value",
    isHero: false,
  },
  {
    code: "value",
    name: "Value Pack",
    storageGB: 200,
    storageLabel: "200 GB",
    monthlyPrice: "₹149",
    yearlyPrice: "₹1,490",
    description: "India's #1 'Paisa Vasool' pack. Tailored for wedding photographers, video editors, and indie filmmakers.",
    features: [
      "200 GB Uncompressed Storage",
      "100% Original RAW & 4K Video",
      "Zero Egress Bandwidth Fees",
      "Direct Presigned S3/R2 Uploads",
      "30-Day Version Retention",
      "Instant 1-Click UPI (Paytm/GPay)",
    ],
    badge: "🔥 PAISA VASOOL (HERO)",
    isHero: true,
  },
  {
    code: "super",
    name: "Super Pack",
    storageGB: 400,
    storageLabel: "400 GB",
    monthlyPrice: "₹249",
    yearlyPrice: "₹2,490",
    description: "Heavy-duty capacity for active content creators and boutique video production houses.",
    features: [
      "400 GB Uncompressed Storage",
      "Unthrottled 4K Video Streaming",
      "Zero Egress Bandwidth Fees",
      "X25519 End-to-End Sharing",
      "60-Day Version Retention",
      "Priority Direct Storage Bandwidth",
    ],
    badge: "For Studios",
    isHero: false,
  },
  {
    code: "mega",
    name: "Mega Pack",
    storageGB: 1000,
    storageLabel: "1 TB (1,000 GB)",
    monthlyPrice: "₹449",
    yearlyPrice: "₹4,490",
    description: "Maximum 1 TB enterprise volume for commercial agencies, heavy RAW shoots, and data archives.",
    features: [
      "1,000 GB (1 TB) RAW Storage",
      "100% Uncompressed Multi-Part Archives",
      "Zero Egress Bandwidth Fees",
      "Tamper-Proof Audit Logging",
      "90-Day Version Retention",
      "Priority 24/7 Dedicated Support",
    ],
    badge: "Maximum Capacity",
    isHero: false,
  },
];

const recommendedPlan = computed(() => {
  if (storageNeededGB.value <= 25) return "entry";
  if (storageNeededGB.value <= 100) return "smart";
  if (storageNeededGB.value <= 200) return "value";
  if (storageNeededGB.value <= 400) return "super";
  return "mega";
});

function selectPlan(planCode: string) {
  router.push({ path: "/register", query: { plan: planCode, interval: interval.value } });
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 flex flex-col selection:bg-brand-600 selection:text-white">
    <!-- Top Nav -->
    <header class="border-b border-slate-200 bg-white/80 sticky top-0 z-30 backdrop-blur-md shadow-2xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-2 text-slate-600 hover:text-slate-900 text-xs font-semibold transition-colors">
          <ArrowLeft class="w-4 h-4" />
          <span>Back to smartspacedata.com</span>
        </router-link>

        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
            <Lock class="w-4 h-4" />
          </div>
          <span class="font-bold text-slate-900 text-sm tracking-tight">SmartSpace Cloud Storage</span>
        </div>

        <router-link to="/login" class="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors">
          Log In
        </router-link>
      </div>
    </header>

    <main class="flex-1 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-14 w-full space-y-12">
      <div class="text-center space-y-4 max-w-2xl mx-auto">
        <div class="inline-flex items-center space-x-1.5 px-3.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-700">
          <Zap class="w-3.5 h-3.5 text-blue-600" />
          <span>ALL-INCLUSIVE INR PRICING • ZERO HIDDEN FEES</span>
        </div>
        <h1 class="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          Flexible Plans with SpaceByte Storage
        </h1>
        <p class="text-slate-600 text-xs sm:text-sm leading-relaxed">
          Zero egress download fees, uncompressed original quality, and instant 1-click Razorpay UPI. Configured up to 1 TB for seamless high-capacity storage.
        </p>

        <!-- Interval Switcher -->
        <div class="inline-flex p-1.5 rounded-2xl bg-slate-200/70 border border-slate-300/60 text-xs shadow-2xs">
          <button
            @click="interval = 'monthly'"
            class="px-5 py-2 rounded-xl font-semibold transition-all"
            :class="interval === 'monthly' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            Monthly Billing
          </button>
          <button
            @click="interval = 'yearly'"
            class="px-5 py-2 rounded-xl font-semibold transition-all flex items-center space-x-2"
            :class="interval === 'yearly' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            <span>Annual (Save 17%)</span>
            <span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">2 Mos Free</span>
          </button>
        </div>
      </div>

      <!-- Storage Calculator Slider -->
      <div class="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-base font-bold text-slate-900 tracking-tight">Storage Estimator</h2>
            <p class="text-xs text-slate-500">Slide to find the exact plan matching your archive and volume requirements.</p>
          </div>
          <div class="text-right">
            <span class="text-3xl font-extrabold text-blue-600 font-mono">{{ storageNeededGB }} GB</span>
            <div class="text-xs text-slate-500 mt-0.5">
              Recommended: <span class="text-slate-900 font-bold uppercase">{{ recommendedPlan }} Pack</span>
            </div>
          </div>
        </div>

        <input
          type="range"
          v-model.number="storageNeededGB"
          min="25"
          max="1000"
          step="25"
          class="w-full accent-blue-600 h-2.5 bg-slate-100 rounded-lg cursor-pointer"
        />
        <div class="flex justify-between text-[11px] text-slate-500 font-medium font-mono">
          <span>25 GB (₹39)</span>
          <span>100 GB (₹89)</span>
          <span>200 GB (₹149)</span>
          <span>400 GB (₹249)</span>
          <span>1 TB (₹449)</span>
        </div>
      </div>

      <!-- 5 Plans Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div
          v-for="plan in plans"
          :key="plan.code"
          class="bg-white rounded-2xl p-5 border flex flex-col justify-between space-y-4 transition-all"
          :class="plan.isHero ? 'border-2 border-blue-600 shadow-md ring-4 ring-blue-50' : 'border-slate-200 hover:border-slate-300 shadow-sm hover:shadow'"
        >
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-bold uppercase tracking-wider text-blue-600 font-mono">
                {{ plan.name }}
              </span>
              <span
                v-if="plan.isHero"
                class="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-xs"
              >
                POPULAR
              </span>
            </div>

            <div>
              <div class="text-3xl font-extrabold text-slate-900 tracking-tight">
                {{ interval === 'yearly' ? plan.yearlyPrice : plan.monthlyPrice }}
              </div>
              <div class="text-xs text-slate-500 font-medium">
                / {{ interval === 'yearly' ? 'year' : 'month' }}
              </div>
            </div>

            <div class="px-2.5 py-1 rounded-xl bg-slate-100 text-xs font-bold text-slate-800 font-mono text-center">
              {{ plan.storageLabel }} Storage
            </div>

            <p class="text-xs text-slate-500 leading-snug">
              {{ plan.description }}
            </p>

            <div class="pt-3 border-t border-slate-100 space-y-2 text-xs text-slate-600">
              <div v-for="(feat, idx) in plan.features" :key="idx" class="flex items-start space-x-2">
                <CheckCircle2 class="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span class="leading-tight">{{ feat }}</span>
              </div>
            </div>
          </div>

          <button
            @click="selectPlan(plan.code)"
            class="w-full py-2.5 rounded-xl text-xs font-semibold transition-all flex items-center justify-center space-x-1.5 shadow-xs"
            :class="plan.isHero ? 'btn-primary' : 'btn-secondary'"
          >
            <span>Select {{ plan.name }}</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <!-- Value Guarantee Banner -->
      <div class="p-6 sm:p-8 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-3">
        <div class="flex items-center space-x-2.5 text-base font-bold text-slate-900">
          <ShieldCheck class="w-5 h-5 text-blue-600" />
          <span>The SmartSpace Data '₹149 Means ₹149' Commitment</span>
        </div>
        <p class="text-xs sm:text-sm text-slate-600 leading-relaxed">
          Every plan on smartspacedata.com is all-inclusive. There are no surprise 18% GST add-ons at checkout, no payment gateway convenience markups, and no download egress bandwidth bills for you or your clients. Uninterrupted 100% original RAW quality powered by local SpaceByte storage infrastructure.
        </p>
      </div>
    </main>
  </div>
</template>

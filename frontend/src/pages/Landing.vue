<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import {
  ShieldCheck,
  Lock,
  Zap,
  Key,
  HardDrive,
  Search,
  CheckCircle2,
  ArrowRight,
  HelpCircle,
  CreditCard,
  Layers,
  ChevronDown,
  Terminal,
  Camera,
  Film,
  Sparkles,
  Download,
} from "lucide-vue-next";

const router = useRouter();
const billingInterval = ref<"monthly" | "yearly">("monthly");
const openFaqIndex = ref<number | null>(null);

function toggleFaq(index: number) {
  openFaqIndex.value = openFaqIndex.value === index ? null : index;
}

function selectPlan(planCode: string = "value") {
  router.push({
    path: "/register",
    query: { plan: planCode, interval: billingInterval.value },
  });
}

const plans = [
  {
    code: "entry",
    name: "Entry Pack",
    storage: "25 GB",
    monthlyPrice: "₹39",
    yearlyPrice: "₹390",
    description: "Essential cloud vault for documents, receipts, and personal backups.",
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
    storage: "100 GB",
    monthlyPrice: "₹89",
    yearlyPrice: "₹890",
    description: "Great for students, personal photo archives, and regular creators.",
    features: [
      "100 GB Encrypted Storage",
      "100% Original RAW Quality",
      "Zero Egress Bandwidth Fees",
      "Client Decrypted Search",
      "Password-Protected Links",
    ],
    badge: "Popular for Students",
    isHero: false,
  },
  {
    code: "value",
    name: "Value Pack",
    storage: "200 GB",
    monthlyPrice: "₹149",
    yearlyPrice: "₹1,490",
    description: "India's #1 'Paisa Vasool' pack. Tailored for wedding photographers, video editors, and indie filmmakers.",
    features: [
      "200 GB Uncompressed Storage",
      "100% Original RAW & 4K Video",
      "Zero Egress Bandwidth Fees",
      "Direct Presigned Uploads",
      "30-Day Version Retention",
      "Instant 1-Click UPI (Paytm/GPay)",
    ],
    badge: "🔥 PAISA VASOOL (MOST POPULAR)",
    isHero: true,
  },
  {
    code: "super",
    name: "Super Pack",
    storage: "400 GB",
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
    storage: "1 TB (1,000 GB)",
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

const faqs = [
  {
    q: "What does 'Zero Egress Fees' mean for me and my clients?",
    a: "Unlike Google Cloud or AWS where you are penalized every time someone downloads your files, SmartSpace Data charges exactly ₹0 in download egress fees. You and your clients can download multi-gigabyte 4K wedding shoots or project ZIPs infinitely at full broadband speed.",
  },
  {
    q: "What does '100% Original RAW Quality' mean?",
    a: "Services like Google Photos silently re-compress your high-resolution photos and video frames to save on their disk space. SmartSpace Data guarantees bit-for-bit byte preservation. Your Sony ARW, Canon CR3, Nikon NEF, ProRes 4K footage, and ZIP files stay 100% pristine and unaltered.",
  },
  {
    q: "Why is there a 15-day renewal purge policy?",
    a: "To keep our operational infrastructure lean and pass the maximum 'Paisa Vasool' savings directly to Indian creators (starting at just ₹39/mo), if an expired subscription is not renewed within 15 days, inactive data is safely purged from the cloud layer.",
  },
  {
    q: "How does 1-Click UPI payment work?",
    a: "We process payments via Razorpay natively in Indian Rupees (INR). You can pay via any UPI app (Paytm, PhonePe, Google Pay, BHIM, CRED) or Indian RuPay/Visa/Mastercard. All plans are 100% all-inclusive with zero hidden GST or surprise recurring charges.",
  },
  {
    q: "Is SmartSpace Data compliant with India's DPDP Privacy Act?",
    a: "Yes. SmartSpace Data adheres to India's Digital Personal Data Protection (DPDP) Act with zero-knowledge client-side encryption. Your master decryption key never leaves your browser, meaning even our server operators cannot see your filenames or view your files.",
  },
];
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#F8FAFC] text-slate-800 selection:bg-brand-600 selection:text-white">
    <!-- Navbar -->
    <header class="sticky top-0 z-40 bg-white/85 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-2.5 group">
          <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-500 flex items-center justify-center shadow-sm shadow-brand-500/20">
            <Lock class="w-4 h-4 text-white" />
          </div>
          <div class="flex flex-col">
            <span class="text-base font-bold tracking-tight text-slate-900 leading-none">
              Smart<span class="text-brand-600">Space</span>
            </span>
            <span class="text-[9px] text-slate-500 font-mono tracking-wider">DATA.COM</span>
          </div>
          <span class="hidden sm:inline-block text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-semibold ml-2">
            PAISA VASOOL CLOUD
          </span>
        </router-link>

        <!-- Nav links -->
        <nav class="hidden md:flex items-center space-x-7 text-xs font-semibold text-slate-600">
          <a href="#features" class="hover:text-brand-600 transition-colors">Core Pillars</a>
          <a href="#creators" class="hover:text-brand-600 transition-colors">For Creators</a>
          <router-link to="/pricing" class="hover:text-brand-600 transition-colors">Plans (from ₹39)</router-link>
          <router-link to="/security" class="hover:text-brand-600 transition-colors">DPDP & Encryption</router-link>
          <a href="#faq" class="hover:text-brand-600 transition-colors">FAQ</a>
        </nav>

        <!-- Actions -->
        <div class="flex items-center space-x-3">
          <router-link
            to="/login"
            class="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
          >
            Log In
          </router-link>
          <button
            @click="selectPlan('value')"
            class="btn-primary px-4 py-2 rounded-xl text-xs font-semibold text-white flex items-center space-x-1.5 shadow-sm hover:shadow-md transition-all"
          >
            <span>Get Started</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="pt-16 pb-20 border-b border-slate-200/80 bg-gradient-to-b from-white via-[#F8FAFC] to-[#F1F5F9] relative overflow-hidden">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
        <!-- Value Badge -->
        <div class="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-white border border-slate-200 shadow-xs text-xs font-medium text-slate-700">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>India's Asset-Light Cloud Storage Startup</span>
          <span class="text-slate-300">•</span>
          <span class="text-brand-600 font-bold">₹149 Means ₹149</span>
        </div>

        <!-- Main Headline -->
        <h1 class="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-tight">
          India’s 'Paisa Vasool' <br class="hidden sm:block" />
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 via-indigo-600 to-blue-700">
            Cloud Storage for Creators.
          </span>
        </h1>

        <!-- Subtitle -->
        <p class="text-base sm:text-lg text-slate-600 max-w-2xl mx-auto font-normal leading-relaxed">
          Zero egress fees. 100% uncompressed RAW & 4K quality for freelance wedding photographers, video editors, and indie filmmakers. 1-Click native Razorpay UPI.
        </p>

        <!-- CTAs -->
        <div class="flex flex-col sm:flex-row items-center justify-center space-y-3 sm:space-y-0 sm:space-x-4 pt-2">
          <button
            @click="selectPlan('value')"
            class="w-full sm:w-auto btn-primary px-6 py-3.5 rounded-xl text-sm font-semibold text-white flex items-center justify-center space-x-2 shadow-md hover:shadow-lg transition-all"
          >
            <span>Get Value Pack (200 GB @ ₹149/mo)</span>
            <ArrowRight class="w-4 h-4" />
          </button>
          <router-link
            to="/pricing"
            class="w-full sm:w-auto px-6 py-3.5 rounded-xl text-sm font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 shadow-xs flex items-center justify-center space-x-2 transition-all"
          >
            <span>View All 5 Packs (from ₹39/mo)</span>
          </router-link>
        </div>

        <!-- 3 Core Blueprint Pillars Banner -->
        <div id="features" class="pt-10 grid grid-cols-1 md:grid-cols-3 gap-5 text-left max-w-4xl mx-auto">
          <!-- Pillar 1 -->
          <div class="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md hover:border-brand-300 transition-all space-y-3">
            <div class="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center">
              <Zap class="w-5 h-5" />
            </div>
            <div class="text-base font-bold text-slate-900">🚀 Zero Egress Fees</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              No download bandwidth charges. You and your link recipients can download files infinitely at max broadband speeds.
            </p>
          </div>

          <!-- Pillar 2 -->
          <div class="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md hover:border-emerald-300 transition-all space-y-3">
            <div class="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Camera class="w-5 h-5" />
            </div>
            <div class="text-base font-bold text-slate-900">🔒 100% Original RAW Quality</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              Zero hidden compression on Canon/Sony RAW images, 4K ProRes videos, or multi-part project ZIP extractions.
            </p>
          </div>

          <!-- Pillar 3 -->
          <div class="p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm hover:shadow-md hover:border-amber-300 transition-all space-y-3">
            <div class="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <CreditCard class="w-5 h-5" />
            </div>
            <div class="text-base font-bold text-slate-900">🇮🇳 1-Click UPI Native</div>
            <p class="text-xs text-slate-600 leading-relaxed">
              Direct checkout via Paytm, PhonePe, Google Pay, and RuPay with zero auto-debit traps. All-inclusive pricing.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Creator Spotlight Section (Delhi-NCR & Pan India) -->
    <section id="creators" class="py-20 border-b border-slate-200/80 bg-white">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-2xl mx-auto space-y-3 mb-14">
          <div class="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-brand-50 text-xs font-mono font-semibold text-brand-700">
            <Film class="w-3.5 h-3.5" />
            <span>BUILT FOR PRODUCTION WORKFLOWS</span>
          </div>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900">
            Engineered for wedding photographers, editors, and filmmakers.
          </h2>
          <p class="text-xs sm:text-sm text-slate-600">
            Tired of Google Drive link throttles, WeTransfer file expiration limits, or Dropbox currency conversion markups?
          </p>
        </div>

        <div class="grid md:grid-cols-3 gap-6">
          <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-xs hover:shadow-sm transition-all space-y-3">
            <h3 class="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <span>Wedding Photographers</span>
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Deliver complete uncompressed shoot albums (CR3, ARW, NEF) directly to families and couples. Clients download full-resolution RAW galleries with one click without creating an account.
            </p>
          </div>

          <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-xs hover:shadow-sm transition-all space-y-3">
            <h3 class="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <span>Video Editors & Colorists</span>
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Upload 4K 10-bit H.264/ProRes timelines directly to high-speed storage. Your directors and YouTube creators preview or download raw footage with zero bandwidth caps.
            </p>
          </div>

          <div class="p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-xs hover:shadow-sm transition-all space-y-3">
            <h3 class="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <span>Freelancers & Indie Creators</span>
            </h3>
            <p class="text-xs text-slate-600 leading-relaxed">
              Full client-side zero-knowledge security backed by a 24-word offline recovery phrase. Your project assets, NDA files, and client deliverables remain completely confidential.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- 5-Tier Paisa Vasool Pricing Section -->
    <section id="pricing" class="py-20 border-b border-slate-200/80 bg-[#F8FAFC]">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-2xl mx-auto space-y-4 mb-12">
          <h2 class="text-2xl sm:text-3xl font-extrabold text-slate-900">
            Final 'Value For Money' Plans
          </h2>
          <p class="text-xs sm:text-sm text-slate-600">
            All prices are completely all-inclusive (inclusive of all transaction gateway costs, 18% GST, and zero egress fees).
          </p>

          <!-- Monthly / Yearly Switch -->
          <div class="inline-flex items-center p-1 rounded-xl bg-white border border-slate-200 shadow-xs text-xs">
            <button
              @click="billingInterval = 'monthly'"
              class="px-4 py-1.5 rounded-lg font-semibold transition-all"
              :class="billingInterval === 'monthly' ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'"
            >
              Monthly Billing
            </button>
            <button
              @click="billingInterval = 'yearly'"
              class="px-4 py-1.5 rounded-lg font-semibold transition-all flex items-center space-x-1.5"
              :class="billingInterval === 'yearly' ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'"
            >
              <span>Yearly (Save 17%)</span>
              <span class="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-bold" :class="billingInterval === 'yearly' ? 'bg-white/20 text-white' : ''">2 Mos Free</span>
            </button>
          </div>
        </div>

        <!-- 5 Plans Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div
            v-for="plan in plans"
            :key="plan.code"
            class="rounded-2xl p-5 border flex flex-col justify-between space-y-4 transition-all"
            :class="plan.isHero ? 'border-brand-500 bg-white ring-2 ring-brand-500/20 shadow-md' : 'border-slate-200 bg-white shadow-xs hover:shadow-sm'"
          >
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono font-bold uppercase tracking-wider text-brand-600">
                  {{ plan.name }}
                </span>
                <span
                  v-if="plan.isHero"
                  class="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-brand-600 text-white"
                >
                  Hero
                </span>
              </div>

              <div>
                <div class="text-2xl font-extrabold text-slate-900">
                  {{ billingInterval === 'yearly' ? plan.yearlyPrice : plan.monthlyPrice }}
                </div>
                <div class="text-[11px] text-slate-500">
                  / {{ billingInterval === 'yearly' ? 'year' : 'month' }}
                </div>
              </div>

              <div class="px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-mono font-bold text-emerald-700 text-center">
                {{ plan.storage }} Storage
              </div>

              <p class="text-[11px] text-slate-600 leading-snug">
                {{ plan.description }}
              </p>

              <div class="pt-3 border-t border-slate-100 space-y-2 text-[11px] text-slate-700">
                <div v-for="(feat, idx) in plan.features" :key="idx" class="flex items-start space-x-1.5">
                  <CheckCircle2 class="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                  <span class="leading-tight">{{ feat }}</span>
                </div>
              </div>
            </div>

            <button
              @click="selectPlan(plan.code)"
              class="w-full py-2.5 rounded-xl text-xs font-semibold transition-all shadow-xs"
              :class="plan.isHero ? 'btn-primary text-white' : 'bg-slate-100 hover:bg-slate-200 text-slate-800'"
            >
              <span>Choose {{ plan.name }}</span>
            </button>
          </div>
        </div>

        <!-- 15-Day Data Clean-up Guideline Note -->
        <div class="mt-8 p-4 rounded-2xl bg-blue-50/60 border border-blue-200/80 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-700 gap-3">
          <div class="flex items-center space-x-2">
            <ShieldCheck class="w-4 h-4 text-brand-600 shrink-0" />
            <span>
              <strong>15-Day Inactivity Protocol:</strong> If an expired plan is not renewed within 15 days, inactive data is purged from the cloud layer to maintain our asset-light cost structure.
            </span>
          </div>
          <span class="font-mono text-[11px] text-emerald-700 font-bold shrink-0">
            ✓ 100% Tax Invoice & GST Compliant
          </span>
        </div>
      </div>
    </section>

    <!-- Comparison Table: SmartSpace Data vs Giants -->
    <section class="py-20 border-b border-slate-200/80 bg-white">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center max-w-xl mx-auto space-y-3 mb-12">
          <h2 class="text-2xl font-extrabold text-slate-900">Why Creators Switch to SmartSpace</h2>
          <p class="text-xs text-slate-600">Honest comparison against traditional corporate providers.</p>
        </div>

        <div class="overflow-x-auto rounded-2xl border border-slate-200 shadow-xs">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-600 font-mono text-[11px]">
                <th class="py-3.5 px-4">Feature</th>
                <th class="py-3.5 px-4 text-brand-700 font-bold bg-blue-50/60">SmartSpace Data</th>
                <th class="py-3.5 px-4">Google One</th>
                <th class="py-3.5 px-4">OneDrive / Dropbox</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-slate-700 bg-white">
              <tr>
                <td class="py-3.5 px-4 font-semibold text-slate-900">200 GB Pricing (INR)</td>
                <td class="py-3.5 px-4 bg-blue-50/30 font-bold text-brand-700">₹149 / mo (All-Inclusive)</td>
                <td class="py-3.5 px-4 text-slate-500">₹210 + Taxes</td>
                <td class="py-3.5 px-4 text-slate-500">~₹800 / mo ($9.99)</td>
              </tr>
              <tr>
                <td class="py-3.5 px-4 font-semibold text-slate-900">Media Compression</td>
                <td class="py-3.5 px-4 bg-blue-50/30 font-bold text-emerald-600">100% RAW Uncompressed</td>
                <td class="py-3.5 px-4 text-rose-500">Silent re-compression</td>
                <td class="py-3.5 px-4 text-slate-500">Limited preview resolution</td>
              </tr>
              <tr>
                <td class="py-3.5 px-4 font-semibold text-slate-900">Download Egress Fees</td>
                <td class="py-3.5 px-4 bg-blue-50/30 font-bold text-emerald-600">Zero Egress Fees</td>
                <td class="py-3.5 px-4 text-slate-500">Rate-limited quotas</td>
                <td class="py-3.5 px-4 text-rose-500">Daily bandwidth limits</td>
              </tr>
              <tr>
                <td class="py-3.5 px-4 font-semibold text-slate-900">1-Click Local UPI</td>
                <td class="py-3.5 px-4 bg-blue-50/30 font-bold text-emerald-600">Paytm, PhonePe, GPay</td>
                <td class="py-3.5 px-4 text-slate-500">Auto-debit mandate required</td>
                <td class="py-3.5 px-4 text-slate-500">Foreign credit cards only</td>
              </tr>
              <tr>
                <td class="py-3.5 px-4 font-semibold text-slate-900">Privacy Architecture</td>
                <td class="py-3.5 px-4 bg-blue-50/30 font-bold text-emerald-600">Argon2id Zero-Knowledge</td>
                <td class="py-3.5 px-4 text-slate-500">Scanned for AI training</td>
                <td class="py-3.5 px-4 text-slate-500">Server decryptable</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- FAQ Accordion -->
    <section id="faq" class="py-20 border-b border-slate-200/80 bg-[#F8FAFC]">
      <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div class="text-center space-y-2 mb-10">
          <h2 class="text-2xl font-extrabold text-slate-900">Frequently Asked Questions</h2>
          <p class="text-xs text-slate-600">Everything you need to know about our 'Paisa Vasool' cloud storage.</p>
        </div>

        <div class="space-y-3">
          <div
            v-for="(faq, idx) in faqs"
            :key="idx"
            class="rounded-2xl overflow-hidden border border-slate-200 bg-white shadow-xs transition-all"
          >
            <button
              @click="toggleFaq(idx)"
              class="w-full px-5 py-4 text-left flex items-center justify-between text-xs font-semibold text-slate-900 hover:bg-slate-50 transition-colors"
            >
              <span>{{ faq.q }}</span>
              <ChevronDown
                class="w-4 h-4 text-slate-400 transition-transform duration-200 shrink-0 ml-3"
                :class="{ 'rotate-180 text-brand-600': openFaqIndex === idx }"
              />
            </button>
            <div
              v-if="openFaqIndex === idx"
              class="px-5 pb-4 text-xs text-slate-600 leading-relaxed border-t border-slate-100 pt-3"
            >
              {{ faq.a }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="py-10 bg-white border-t border-slate-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
        <div class="flex items-center space-x-2">
          <div class="w-6 h-6 rounded bg-brand-600 flex items-center justify-center text-white">
            <Lock class="w-3.5 h-3.5" />
          </div>
          <span class="font-bold text-slate-900">SmartSpace Data</span>
          <span>(smartspacedata.com) • India's 'Paisa Vasool' Cloud</span>
        </div>
        <div class="flex items-center space-x-6 text-slate-600 font-medium">
          <router-link to="/security" class="hover:text-brand-600 transition-colors">DPDP & Security</router-link>
          <router-link to="/legal" class="hover:text-brand-600 transition-colors">Privacy & Terms</router-link>
          <router-link to="/pricing" class="hover:text-brand-600 transition-colors">Plans (from ₹39)</router-link>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { Cloud, CheckCircle2, Zap, ArrowLeft } from "lucide-vue-next";

const router = useRouter();
const interval = ref<"monthly" | "yearly">("monthly");
const storageNeededGB = ref<number>(500);

const recommendedPlan = computed(() => {
  return storageNeededGB.value <= 200 ? "personal" : "business";
});

function selectPlan(planCode: string) {
  router.push({ path: "/register", query: { plan: planCode, interval: interval.value } });
}
</script>

<template>
  <div class="min-h-screen bg-[#070D1A] text-slate-100 flex flex-col">
    <!-- Top Nav -->
    <header class="border-b border-slate-800/80 bg-[#070D1A]/80 sticky top-0 z-30">
      <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-2 text-slate-300 hover:text-white text-sm font-medium">
          <ArrowLeft class="w-4 h-4" />
          <span>Back to Home</span>
        </router-link>
        <div class="flex items-center space-x-2">
          <div class="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Cloud class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-white tracking-tight">SpeedCloud Pricing</span>
        </div>
        <router-link to="/login" class="text-sm font-semibold text-brand-400 hover:text-brand-300">
          Login
        </router-link>
      </div>
    </header>

    <main class="flex-1 max-w-5xl mx-auto px-4 py-16 w-full space-y-16">
      <div class="text-center space-y-4 max-w-2xl mx-auto">
        <h1 class="text-4xl sm:text-5xl font-extrabold text-white tracking-tight">
          Simple, Transparent Pricing
        </h1>
        <p class="text-slate-300 text-base">
          No ad-tracking, no free tier compromises. Pure private cloud storage in INR.
        </p>

        <!-- Interval Switcher -->
        <div class="mt-6 inline-flex p-1.5 rounded-2xl bg-slate-900 border border-slate-800">
          <button
            @click="interval = 'monthly'"
            class="px-6 py-2.5 rounded-xl text-sm font-semibold transition-all"
            :class="interval === 'monthly' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-white'"
          >
            Monthly
          </button>
          <button
            @click="interval = 'yearly'"
            class="px-6 py-2.5 rounded-xl text-sm font-semibold transition-all flex items-center space-x-2"
            :class="interval === 'yearly' ? 'bg-brand-600 text-white shadow-md' : 'text-slate-400 hover:text-white'"
          >
            <span>Yearly (Save 17%)</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] bg-accent-orange text-white font-bold">2 Mos Free</span>
          </button>
        </div>
      </div>

      <!-- Storage Calculator -->
      <div class="glass-card rounded-3xl p-8 border border-slate-800 space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-xl font-bold text-white">Storage Need Calculator</h2>
            <p class="text-sm text-slate-400">Estimate how much zero-knowledge storage your archives require.</p>
          </div>
          <div class="text-right">
            <span class="text-3xl font-black text-brand-400 font-mono">{{ storageNeededGB }} GB</span>
            <div class="text-xs text-slate-400">Recommended: <span class="text-white font-bold uppercase">{{ recommendedPlan }}</span></div>
          </div>
        </div>

        <input
          type="range"
          v-model.number="storageNeededGB"
          min="50"
          max="2000"
          step="50"
          class="w-full accent-brand-500 h-2 bg-slate-800 rounded-lg cursor-pointer"
        />
        <div class="flex justify-between text-xs text-slate-500 font-mono">
          <span>50 GB</span>
          <span>200 GB (Personal)</span>
          <span>1 TB</span>
          <span>2 TB (Business)</span>
        </div>
      </div>

      <!-- Plans Grid -->
      <div class="grid md:grid-cols-2 gap-8">
        <!-- Personal Plan -->
        <div
          class="rounded-3xl p-8 glass-card border transition-all flex flex-col justify-between"
          :class="recommendedPlan === 'personal' ? 'border-brand-500 shadow-2xl shadow-brand-500/10' : 'border-slate-800'"
        >
          <div class="space-y-6">
            <span class="px-3 py-1 rounded-full text-xs font-bold uppercase bg-brand-500/10 text-brand-400 border border-brand-500/30">
              Personal Plan
            </span>
            <div class="flex items-baseline space-x-2">
              <span class="text-5xl font-black text-white">
                ₹{{ interval === 'yearly' ? '1,999' : '199' }}
              </span>
              <span class="text-slate-400 font-medium">/ {{ interval === 'yearly' ? 'year' : 'month' }}</span>
            </div>
            <p class="text-xs text-slate-400">For students, creators, and individuals wanting complete file sovereignty.</p>

            <div class="space-y-3 pt-4 border-t border-slate-800/80 text-sm">
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span><strong>200 GB</strong> Encrypted Storage</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>10 GB Single Max File Size</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>30 Days File Version History</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>Password Protected Public Links</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>Up to 5 Devices</span>
              </div>
            </div>
          </div>

          <div class="pt-8">
            <button
              @click="selectPlan('personal')"
              class="w-full py-4 rounded-xl font-bold text-white bg-gradient-to-r from-accent-orange to-amber-500 hover:from-orange-600 hover:to-amber-600 shadow-xl shadow-orange-500/20 transition-all"
            >
              Get Started with Personal
            </button>
          </div>
        </div>

        <!-- Business Plan -->
        <div
          class="rounded-3xl p-8 glass-card border transition-all flex flex-col justify-between"
          :class="recommendedPlan === 'business' ? 'border-brand-500 shadow-2xl shadow-brand-500/10' : 'border-slate-800'"
        >
          <div class="space-y-6">
            <span class="px-3 py-1 rounded-full text-xs font-bold uppercase bg-brand-500/20 text-brand-300 border border-brand-500/40">
              Business Plan
            </span>
            <div class="flex items-baseline space-x-2">
              <span class="text-5xl font-black text-white">
                ₹{{ interval === 'yearly' ? '4,999' : '499' }}
              </span>
              <span class="text-slate-400 font-medium">/ {{ interval === 'yearly' ? 'year' : 'month' }}</span>
            </div>
            <p class="text-xs text-slate-400">For companies, developers, and compliance-heavy production workflows.</p>

            <div class="space-y-3 pt-4 border-t border-slate-800/80 text-sm">
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span><strong>2 TB</strong> High-Speed Storage</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>50 GB Single Max File Size</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>365 Days Extended Version Retention</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>Team Access & X25519 Secure Sharing</span>
              </div>
              <div class="flex items-center space-x-3 text-slate-200">
                <CheckCircle2 class="w-5 h-5 text-brand-400" />
                <span>Unlimited Devices & Priority Support</span>
              </div>
            </div>
          </div>

          <div class="pt-8">
            <button
              @click="selectPlan('business')"
              class="w-full py-4 rounded-xl font-bold text-white bg-brand-600 hover:bg-brand-500 shadow-xl shadow-brand-600/30 transition-all"
            >
              Choose Business Plan
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

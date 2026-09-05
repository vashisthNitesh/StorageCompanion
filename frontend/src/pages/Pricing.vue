<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { Lock, CheckCircle2, ArrowLeft, ArrowRight, ShieldCheck } from "lucide-vue-next";

const router = useRouter();
const interval = ref<"monthly" | "yearly">("monthly");
const storageNeededGB = ref<number>(200);

const recommendedPlan = computed(() => {
  return storageNeededGB.value <= 200 ? "personal" : "business";
});

function selectPlan(planCode: string) {
  router.push({ path: "/register", query: { plan: planCode, interval: interval.value } });
}
</script>

<template>
  <div class="min-h-screen bg-surface-ground text-slate-100 flex flex-col selection:bg-brand-600 selection:text-white">
    <!-- Top Nav -->
    <header class="border-b border-surface-border bg-surface-ground/90 sticky top-0 z-30 backdrop-blur-md">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center space-x-2 text-slate-400 hover:text-white text-xs font-medium transition-colors">
          <ArrowLeft class="w-4 h-4" />
          <span>Back to SpeedCloud</span>
        </router-link>

        <div class="flex items-center space-x-2">
          <div class="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center text-white">
            <Lock class="w-3.5 h-3.5" />
          </div>
          <span class="font-bold text-white text-sm tracking-tight">SpeedCloud Pricing</span>
        </div>

        <router-link to="/login" class="text-xs font-semibold text-slate-300 hover:text-white transition-colors">
          Log In
        </router-link>
      </div>
    </header>

    <main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full space-y-12">
      <div class="text-center space-y-4 max-w-2xl mx-auto">
        <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Simple, transparent vault subscriptions.
        </h1>
        <p class="text-slate-400 text-xs sm:text-sm leading-relaxed">
          Zero-knowledge encryption, zero ads, and zero egress fees. Billed in INR with instant Razorpay activation.
        </p>

        <!-- Interval Switcher -->
        <div class="inline-flex p-1 rounded-xl bg-surface-card border border-surface-border text-xs">
          <button
            @click="interval = 'monthly'"
            class="px-5 py-1.5 rounded-lg font-semibold transition-all"
            :class="interval === 'monthly' ? 'bg-surface-elevated text-white shadow-sm' : 'text-slate-400 hover:text-white'"
          >
            Monthly
          </button>
          <button
            @click="interval = 'yearly'"
            class="px-5 py-1.5 rounded-lg font-semibold transition-all flex items-center space-x-2"
            :class="interval === 'yearly' ? 'bg-surface-elevated text-white shadow-sm' : 'text-slate-400 hover:text-white'"
          >
            <span>Annual (Save 16%)</span>
            <span class="px-1.5 py-0.2 rounded bg-brand-600/20 text-brand-400 text-[10px] font-bold">BEST VALUE</span>
          </button>
        </div>
      </div>

      <!-- Storage Calculator Slider -->
      <div class="vault-panel rounded-2xl p-6 sm:p-8 border border-surface-border space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-sm font-bold text-white tracking-tight">Storage Estimator</h2>
            <p class="text-xs text-slate-400">Slide to see how much encrypted capacity fits your archive requirements.</p>
          </div>
          <div class="text-right">
            <span class="text-2xl font-bold text-brand-400 font-mono">{{ storageNeededGB }} GB</span>
            <div class="text-[11px] text-slate-400">Recommended Plan: <span class="text-white font-bold uppercase">{{ recommendedPlan }}</span></div>
          </div>
        </div>

        <input
          type="range"
          v-model.number="storageNeededGB"
          min="50"
          max="2000"
          step="50"
          class="w-full accent-brand-500 h-2 bg-surface-subtle rounded-lg cursor-pointer"
        />
        <div class="flex justify-between text-[11px] text-slate-500 font-mono">
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
          class="vault-panel rounded-2xl p-7 border transition-all flex flex-col justify-between space-y-6"
          :class="recommendedPlan === 'personal' ? 'border-brand-500/50 shadow-xl' : 'border-surface-border'"
        >
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono uppercase font-bold text-brand-400">Personal Vault</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-surface-elevated text-slate-400">200 GB</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span class="text-3xl font-extrabold text-white">
                ₹{{ interval === 'yearly' ? '1,999' : '199' }}
              </span>
              <span class="text-xs text-slate-400">/ {{ interval === 'yearly' ? 'year' : 'month' }}</span>
            </div>
            <p class="text-xs text-slate-400">For personal documents, photo archives, and sensitive zero-knowledge backups.</p>

            <div class="space-y-2.5 pt-4 border-t border-surface-border text-xs text-slate-300">
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span><strong>200 GB</strong> Encrypted Storage</span>
              </div>
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span>10 GB Single Max File Size</span>
              </div>
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span>30 Days File Version History</span>
              </div>
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span>X25519 End-to-End Link Sharing</span>
              </div>
            </div>
          </div>

          <button
            @click="selectPlan('personal')"
            class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2"
          >
            <span>Activate Personal Plan</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Business Plan -->
        <div
          class="vault-panel rounded-2xl p-7 border transition-all flex flex-col justify-between space-y-6"
          :class="recommendedPlan === 'business' ? 'border-brand-500/50 shadow-xl' : 'border-surface-border'"
        >
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono uppercase font-bold text-brand-400">Business Vault</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-brand-600/20 text-brand-400 font-bold uppercase">2 TB (2,048 GB)</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span class="text-3xl font-extrabold text-white">
                ₹{{ interval === 'yearly' ? '4,999' : '499' }}
              </span>
              <span class="text-xs text-slate-400">/ {{ interval === 'yearly' ? 'year' : 'month' }}</span>
            </div>
            <p class="text-xs text-slate-400">For teams, developers, and data-heavy workflows requiring extended retention.</p>

            <div class="space-y-2.5 pt-4 border-t border-surface-border text-xs text-slate-300">
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span><strong>2 TB</strong> Encrypted Storage</span>
              </div>
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span>50 GB Single Max File Size</span>
              </div>
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span>90 Days Version Retention & Audit Logs</span>
              </div>
              <div class="flex items-center space-x-2.5">
                <CheckCircle2 class="w-4 h-4 text-accent-emerald shrink-0" />
                <span>Priority 24/7 Dedicated Support</span>
              </div>
            </div>
          </div>

          <button
            @click="selectPlan('business')"
            class="w-full btn-primary py-3 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2"
          >
            <span>Activate Business Plan</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

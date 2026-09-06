<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore } from "../../stores/billing";
import {
  CreditCard,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Lock,
  ArrowRight,
  RefreshCw,
  Zap,
  ShieldCheck,
} from "lucide-vue-next";

const route = useRoute();
const authStore = useAuthStore();
const billingStore = useBillingStore();

const isGateRequired = ref(route.query.gate === "required");
const checkoutError = ref("");

const plansList = [
  {
    code: "entry",
    name: "Entry Pack",
    storage: "25 GB",
    monthlyPrice: "₹39",
    yearlyPrice: "₹390",
    desc: "Personal receipts & basic docs",
  },
  {
    code: "smart",
    name: "Smart Pack",
    storage: "100 GB",
    monthlyPrice: "₹89",
    yearlyPrice: "₹890",
    desc: "Student & creator archives",
  },
  {
    code: "value",
    name: "Value Pack",
    storage: "200 GB",
    monthlyPrice: "₹149",
    yearlyPrice: "₹1,490",
    desc: "Flagship: Wedding & 4K video",
    isHero: true,
  },
  {
    code: "super",
    name: "Super Pack",
    storage: "400 GB",
    monthlyPrice: "₹249",
    yearlyPrice: "₹2,490",
    desc: "Studio production workflows",
  },
  {
    code: "mega",
    name: "Mega Pack",
    storage: "1 TB (1,000 GB)",
    monthlyPrice: "₹449",
    yearlyPrice: "₹4,490",
    desc: "Agency multi-part archives",
  },
];

onMounted(async () => {
  await Promise.all([
    billingStore.fetchPlans(),
    billingStore.fetchSubscription(),
    billingStore.fetchInvoices(),
  ]);
});

async function handleUpgrade(planCode: string) {
  checkoutError.value = "";
  try {
    await billingStore.checkout(planCode, billingStore.selectedInterval);
    isGateRequired.value = false;
  } catch (err: any) {
    checkoutError.value = err.message || "Payment could not be completed.";
  }
}
</script>

<template>
  <div class="space-y-6 max-w-6xl">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-white tracking-tight">Subscription & Quota Management</h1>
        <p class="text-xs text-slate-400">smartspacedata.com • All-inclusive INR pricing with zero egress fees.</p>
      </div>

      <!-- Interval Toggle -->
      <div class="inline-flex items-center p-1 rounded-xl bg-surface-card border border-surface-border text-xs self-start sm:self-auto">
        <button
          @click="billingStore.selectedInterval = 'monthly'"
          class="px-3.5 py-1 rounded-lg font-medium transition-colors"
          :class="billingStore.selectedInterval === 'monthly' ? 'bg-surface-elevated text-white' : 'text-slate-400 hover:text-white'"
        >
          Monthly
        </button>
        <button
          @click="billingStore.selectedInterval = 'yearly'"
          class="px-3.5 py-1 rounded-lg font-medium transition-colors"
          :class="billingStore.selectedInterval === 'yearly' ? 'bg-surface-elevated text-white' : 'text-slate-400 hover:text-white'"
        >
          Annual (Save 17%)
        </button>
      </div>
    </div>

    <!-- Gate Required Alert -->
    <div v-if="isGateRequired || !authStore.hasActiveSubscription" class="p-4 rounded-xl bg-amber-950/30 border border-amber-800/50 flex items-start space-x-3 text-xs text-amber-200">
      <Lock class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
      <div class="space-y-1 leading-relaxed">
        <div class="font-bold text-amber-400">Active Subscription Required</div>
        <p>
          Your zero-knowledge vault is staged, but encrypted uploads require an active 'Paisa Vasool' plan. Choose any pack below to activate your storage via Razorpay 1-Click UPI.
        </p>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="checkoutError" class="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex items-center space-x-2.5">
      <AlertTriangle class="w-4 h-4 text-rose-400" />
      <span>{{ checkoutError }}</span>
    </div>

    <!-- Current Subscription Panel -->
    <div class="vault-panel p-6 rounded-2xl border border-surface-border space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-1.5">
          <div class="flex items-center space-x-2">
            <span class="text-xs font-mono uppercase tracking-wider text-slate-400">Subscription Status</span>
            <span
              class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
              :class="authStore.hasActiveSubscription ? 'bg-emerald-950/60 text-accent-emerald border border-emerald-800/60' : 'bg-rose-950/60 text-rose-400 border border-rose-800/60'"
            >
              {{ authStore.hasActiveSubscription ? (billingStore.currentSubscription?.status || 'Active') : 'Inactive / Payment Required' }}
            </span>
          </div>
          <div class="text-2xl font-bold text-white tracking-tight">
            {{ billingStore.currentSubscription?.plan_details?.name || (authStore.hasActiveSubscription ? 'Value Pack (200 GB)' : 'No Active Plan') }}
          </div>
          <div class="text-xs text-slate-400">
            <span v-if="billingStore.currentSubscription?.current_period_end">
              Renewal date: {{ new Date(billingStore.currentSubscription.current_period_end).toLocaleDateString() }} via Razorpay UPI / Cards
            </span>
            <span v-else>
              Select an uncompressed pack below to unlock your encrypted cloud vault.
            </span>
          </div>
        </div>

        <div class="p-3.5 rounded-xl bg-surface-card border border-surface-border text-right min-w-[150px]">
          <div class="text-[11px] text-slate-400 font-medium">Allocated Quota</div>
          <div class="text-2xl font-bold text-white font-mono">
            {{ ((authStore.user?.quota?.bytes_limit || 0) / (1024 * 1024 * 1024)).toFixed(0) }} GB
          </div>
        </div>
      </div>

      <!-- Quota Meter -->
      <div class="space-y-2 pt-3 border-t border-surface-border">
        <div class="flex justify-between text-xs text-slate-400">
          <span>RAW Storage Consumed</span>
          <span class="font-mono text-white">{{ authStore.user?.quota?.percent_used || 0 }}% used</span>
        </div>
        <div class="w-full bg-surface-subtle h-2 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="(authStore.user?.quota?.percent_used || 0) > 85 ? 'bg-rose-500' : 'bg-brand-600'"
            :style="{ width: `${authStore.user?.quota?.percent_used || 0}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- 15-Day Inactivity Clean-Up Protocol Notice -->
    <div class="p-4 rounded-xl bg-surface-card border border-surface-border flex items-start space-x-3 text-xs text-slate-400">
      <ShieldCheck class="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
      <div class="space-y-1">
        <span class="font-bold text-slate-200">15-Day Inactivity & Data Retention Protocol</span>
        <p class="leading-relaxed">
          To sustain our asset-light cost model and pass the maximum savings to Indian creators, our terms enforce that if an expired subscription is not renewed within 15 days of expiration, user data will be automatically purged from the secure cloud layer.
        </p>
      </div>
    </div>

    <!-- Available Plans Grid (5 Packs) -->
    <div class="space-y-4">
      <h2 class="text-sm font-bold text-white tracking-tight">Available 'Paisa Vasool' Packs</h2>

      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <div
          v-for="plan in plansList"
          :key="plan.code"
          class="vault-panel p-4 rounded-xl border flex flex-col justify-between space-y-4"
          :class="plan.isHero ? 'border-brand-500/60 bg-surface-card ring-1 ring-brand-500/30' : 'border-surface-border'"
        >
          <div class="space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-mono font-bold uppercase text-brand-400">{{ plan.name }}</span>
              <span v-if="plan.isHero" class="text-[9px] px-1.5 py-0.2 rounded bg-brand-600 text-white font-bold">HERO</span>
            </div>

            <div>
              <div class="text-xl font-extrabold text-white">
                {{ billingStore.selectedInterval === 'yearly' ? plan.yearlyPrice : plan.monthlyPrice }}
              </div>
              <div class="text-[10px] text-slate-400">/ {{ billingStore.selectedInterval === 'yearly' ? 'yr' : 'mo' }}</div>
            </div>

            <div class="px-2 py-0.5 rounded bg-surface-elevated text-xs font-mono font-bold text-accent-emerald text-center">
              {{ plan.storage }}
            </div>

            <p class="text-[10px] text-slate-400 leading-tight">
              {{ plan.desc }}
            </p>
          </div>

          <button
            @click="handleUpgrade(plan.code)"
            :disabled="billingStore.isLoading || (billingStore.currentSubscription?.plan_details?.code === plan.code && authStore.hasActiveSubscription)"
            class="w-full py-2 rounded-lg text-xs font-semibold text-white transition-colors disabled:opacity-40"
            :class="plan.isHero ? 'btn-primary' : 'btn-secondary'"
          >
            <span>
              {{ billingStore.currentSubscription?.plan_details?.code === plan.code && authStore.hasActiveSubscription ? 'Current Plan' : 'Select ' + plan.name }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Invoice History -->
    <div class="space-y-4 pt-2">
      <h2 class="text-sm font-bold text-white tracking-tight">Tax Invoices & Receipts</h2>

      <div v-if="billingStore.invoices.length === 0" class="p-6 rounded-xl bg-surface-card border border-surface-border text-center text-xs text-slate-400">
        No past invoices recorded.
      </div>
      <div v-else class="rounded-xl border border-surface-border bg-surface-card overflow-hidden divide-y divide-surface-border">
        <div
          v-for="inv in billingStore.invoices"
          :key="inv.id"
          class="p-4 flex items-center justify-between text-xs"
        >
          <div class="flex items-center space-x-3">
            <FileText class="w-4 h-4 text-slate-400" />
            <div>
              <div class="font-bold text-white font-mono">{{ inv.provider_invoice_id || inv.id.slice(0, 12) }}</div>
              <div class="text-[10px] text-slate-400">{{ new Date(inv.issued_at).toLocaleDateString() }} • SAC 998315</div>
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <span class="font-bold font-mono text-white">₹{{ inv.amount }}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-950/60 text-accent-emerald border border-emerald-800/60">
              {{ inv.status }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

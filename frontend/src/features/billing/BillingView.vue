<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore } from "../../stores/billing";
import { apiRequest } from "../../lib/api";
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
  Server,
} from "lucide-vue-next";

const route = useRoute();
const authStore = useAuthStore();
const billingStore = useBillingStore();

const isGateRequired = ref(route.query.gate === "required");
const checkoutError = ref("");
const poolStats = ref<{
  total_pool_gb: number;
  used_gb: number;
  remaining_gb: number;
  percent_used: number;
  is_connected: boolean;
  provider: string;
} | null>(null);

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
    desc: "Agency multi-part archives (Max Testing Tier)",
  },
];

async function fetchPoolStatus() {
  try {
    const data = await apiRequest<any>("/api/v1/pool-status");
    poolStats.value = data;
  } catch {
    poolStats.value = {
      total_pool_gb: 1000,
      used_gb: 0,
      remaining_gb: 1000,
      percent_used: 0,
      is_connected: false,
      provider: "spacebyte",
    };
  }
}

onMounted(async () => {
  await Promise.all([
    billingStore.fetchPlans(),
    billingStore.fetchSubscription(),
    billingStore.fetchInvoices(),
    fetchPoolStatus(),
  ]);
});

async function handleUpgrade(planCode: string) {
  checkoutError.value = "";
  try {
    await billingStore.checkout(planCode, billingStore.selectedInterval);
    isGateRequired.value = false;
    await fetchPoolStatus();
  } catch (err: any) {
    checkoutError.value = err.message || "Payment could not be completed.";
  }
}
</script>

<template>
  <div class="space-y-6 max-w-6xl text-slate-900">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Subscription & Quota Management</h1>
        <p class="text-xs text-slate-500 mt-0.5">smartspacedata.com • All-inclusive INR pricing with zero egress fees powered by SpaceByte.</p>
      </div>

      <!-- Interval Toggle -->
      <div class="inline-flex items-center p-1 rounded-2xl bg-slate-200/70 border border-slate-300/60 text-xs self-start sm:self-auto shadow-2xs">
        <button
          @click="billingStore.selectedInterval = 'monthly'"
          class="px-4 py-1.5 rounded-xl font-semibold transition-all"
          :class="billingStore.selectedInterval === 'monthly' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
        >
          Monthly
        </button>
        <button
          @click="billingStore.selectedInterval = 'yearly'"
          class="px-4 py-1.5 rounded-xl font-semibold transition-all flex items-center space-x-1.5"
          :class="billingStore.selectedInterval === 'yearly' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
        >
          <span>Annual (Save 17%)</span>
        </button>
      </div>
    </div>

    <!-- Gate Required Alert -->
    <div v-if="isGateRequired || !authStore.hasActiveSubscription" class="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start space-x-3 text-xs text-amber-900 shadow-xs">
      <Lock class="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
      <div class="space-y-1 leading-relaxed">
        <div class="font-bold text-amber-900">Active Subscription Required</div>
        <p>
          Your zero-knowledge encrypted vault is staged. To upload files, choose an uncompressed plan below to activate your storage via Razorpay 1-Click UPI.
        </p>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="checkoutError" class="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2.5">
      <AlertTriangle class="w-4 h-4 text-rose-600" />
      <span>{{ checkoutError }}</span>
    </div>

    <!-- Top Status Cards Grid: User Subscription + SpaceByte Upstream Pool -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <!-- Current Subscription Panel (Span 2) -->
      <div class="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="space-y-1.5">
            <div class="flex items-center space-x-2">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">Subscription Status</span>
              <span
                class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider"
                :class="authStore.hasActiveSubscription ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'"
              >
                {{ authStore.hasActiveSubscription ? (billingStore.currentSubscription?.status || 'Active') : 'Inactive / Plan Required' }}
              </span>
            </div>
            <div class="text-2xl font-extrabold text-slate-900 tracking-tight">
              {{ billingStore.currentSubscription?.plan_details?.name || (authStore.hasActiveSubscription ? 'Value Pack (200 GB)' : 'No Active Plan') }}
            </div>
            <div class="text-xs text-slate-500">
              <span v-if="billingStore.currentSubscription?.current_period_end">
                Renewal date: {{ new Date(billingStore.currentSubscription.current_period_end).toLocaleDateString() }} via Razorpay UPI / Cards ({{ billingStore.selectedInterval }})
              </span>
              <span v-else>
                Select an uncompressed pack below to unlock your encrypted cloud vault.
              </span>
            </div>
          </div>

          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-right min-w-[140px]">
            <div class="text-[11px] text-slate-500 font-medium">Allocated Quota</div>
            <div class="text-2xl font-bold text-slate-900 font-mono">
              {{ ((authStore.user?.quota?.bytes_limit || 0) / (1024 * 1024 * 1024)).toFixed(0) }} GB
            </div>
          </div>
        </div>

        <!-- Quota Meter -->
        <div class="space-y-2 pt-3 border-t border-slate-100">
          <div class="flex justify-between text-xs text-slate-600">
            <span>Storage Consumed</span>
            <span class="font-mono text-slate-900 font-semibold">{{ authStore.user?.quota?.percent_used || 0 }}% used</span>
          </div>
          <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="(authStore.user?.quota?.percent_used || 0) > 85 ? 'bg-rose-500' : 'bg-blue-600'"
              :style="{ width: `${authStore.user?.quota?.percent_used || 0}%` }"
            ></div>
          </div>
        </div>
      </div>

      <!-- SpaceByte 1 TB Testing Pool Card (Span 1) -->
      <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2 text-xs font-bold text-slate-700">
              <Server class="w-4 h-4 text-blue-600" />
              <span>SpaceByte.in Storage Pool</span>
            </div>
            <span
              class="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase"
              :class="poolStats?.is_connected ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-blue-50 text-blue-700 border border-blue-200'"
            >
              {{ poolStats?.is_connected ? 'Live Upstream' : 'Testing Pool' }}
            </span>
          </div>

          <div class="space-y-1">
            <div class="text-2xl font-bold text-slate-900 font-mono">
              {{ poolStats?.total_pool_gb || 1000 }} GB (1 TB)
            </div>
            <p class="text-[11px] text-slate-500 leading-snug">
              System testing capacity limit allocated on SpaceByte.in upstream storage.
            </p>
          </div>

          <div class="space-y-1.5 pt-2 border-t border-slate-100 text-xs text-slate-600">
            <div class="flex justify-between">
              <span>Pool Available:</span>
              <span class="font-mono font-semibold text-slate-900">{{ poolStats?.remaining_gb || 1000 }} GB</span>
            </div>
            <div class="flex justify-between">
              <span>Billing Supported:</span>
              <span class="font-medium text-slate-700">Monthly & Yearly</span>
            </div>
          </div>
        </div>

        <div class="text-[10px] text-slate-400 bg-slate-50 p-2.5 rounded-xl border border-slate-200/80">
          Token: <code class="font-mono text-slate-600">SPACEBYTE_ACCESS_TOKEN</code> configured in server environment.
        </div>
      </div>
    </div>

    <!-- Available Plans Grid (5 Packs) -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-bold text-slate-900 tracking-tight">Available Subscription Packs</h2>
        <span class="text-xs text-slate-500">Max plan fits within testing 1 TB availability</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div
          v-for="plan in plansList"
          :key="plan.code"
          class="bg-white p-5 rounded-2xl border flex flex-col justify-between space-y-4 transition-all"
          :class="plan.isHero ? 'border-2 border-blue-600 shadow-md ring-4 ring-blue-50' : 'border-slate-200 hover:border-slate-300 shadow-sm hover:shadow'"
        >
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-mono font-bold uppercase text-blue-600">{{ plan.name }}</span>
              <span v-if="plan.isHero" class="text-[9px] px-2 py-0.5 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold">POPULAR</span>
            </div>

            <div>
              <div class="text-2xl font-extrabold text-slate-900">
                {{ billingStore.selectedInterval === 'yearly' ? plan.yearlyPrice : plan.monthlyPrice }}
              </div>
              <div class="text-[10px] text-slate-500">/ {{ billingStore.selectedInterval === 'yearly' ? 'year' : 'month' }}</div>
            </div>

            <div class="px-2.5 py-1 rounded-xl bg-slate-100 text-xs font-mono font-bold text-slate-800 text-center">
              {{ plan.storage }}
            </div>

            <p class="text-xs text-slate-500 leading-snug">
              {{ plan.desc }}
            </p>
          </div>

          <button
            @click="handleUpgrade(plan.code)"
            :disabled="billingStore.isLoading || (billingStore.currentSubscription?.plan_details?.code === plan.code && authStore.hasActiveSubscription)"
            class="w-full py-2.5 rounded-xl text-xs font-semibold transition-all disabled:opacity-50 shadow-xs"
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
      <h2 class="text-base font-bold text-slate-900 tracking-tight">Tax Invoices & Payment Receipts</h2>

      <div v-if="billingStore.invoices.length === 0" class="p-8 rounded-2xl bg-white border border-slate-200 text-center text-xs text-slate-500 shadow-sm">
        No past invoices recorded. Invoices will appear here automatically upon Razorpay checkout.
      </div>
      <div v-else class="rounded-2xl border border-slate-200 bg-white overflow-hidden divide-y divide-slate-100 shadow-sm">
        <div
          v-for="inv in billingStore.invoices"
          :key="inv.id"
          class="p-4 flex items-center justify-between text-xs hover:bg-slate-50/70 transition-colors"
        >
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText class="w-4 h-4" />
            </div>
            <div>
              <div class="font-bold text-slate-900 font-mono">{{ inv.provider_invoice_id || inv.id.slice(0, 12) }}</div>
              <div class="text-[10px] text-slate-500">{{ new Date(inv.issued_at).toLocaleDateString() }} • SAC 998315 (SpaceByte Storage)</div>
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <span class="font-bold font-mono text-slate-900 text-sm">₹{{ inv.amount }}</span>
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
              {{ inv.status }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore } from "../../stores/billing";
import { CreditCard, HardDrive, CheckCircle2, Zap, AlertCircle, FileText } from "lucide-vue-next";

const authStore = useAuthStore();
const billingStore = useBillingStore();

onMounted(async () => {
  await Promise.all([
    billingStore.fetchPlans(),
    billingStore.fetchSubscription(),
    billingStore.fetchInvoices(),
  ]);
});

async function upgrade(planCode: string) {
  await billingStore.checkout(planCode, billingStore.selectedInterval);
}
</script>

<template>
  <div class="space-y-8 max-w-5xl">
    <div>
      <h1 class="text-xl font-bold text-white">Subscription & Storage Quota</h1>
      <p class="text-xs text-slate-400">Manage your active plan, upgrade storage, and view invoices in INR.</p>
    </div>

    <!-- Current Plan Banner -->
    <div class="glass-panel p-6 rounded-3xl border border-slate-800 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="text-xs font-bold uppercase tracking-wider text-brand-400">Current Subscription</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              {{ billingStore.currentSubscription?.status || 'Active' }}
            </span>
          </div>
          <h2 class="text-2xl font-extrabold text-white">
            {{ billingStore.currentSubscription?.plan_details?.name || 'Personal Plan' }}
          </h2>
          <div class="text-xs text-slate-400 font-mono">
            Next renewal: {{ billingStore.currentSubscription?.current_period_end ? new Date(billingStore.currentSubscription.current_period_end).toLocaleDateString() : 'Active' }}
          </div>
        </div>

        <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-right">
          <div class="text-xs text-slate-400">Storage Limit</div>
          <div class="text-2xl font-black text-white font-mono">
            {{ ((authStore.user?.quota?.bytes_limit || 200 * 1024 * 1024 * 1024) / (1024 * 1024 * 1024)).toFixed(0) }} GB
          </div>
        </div>
      </div>

      <!-- Quota Meter -->
      <div class="space-y-2 pt-2 border-t border-slate-800/80">
        <div class="flex justify-between text-xs text-slate-300">
          <span>Storage Consumed</span>
          <span class="font-mono">{{ authStore.user?.quota?.percent_used || 0 }}% used</span>
        </div>
        <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
          <div
            class="bg-brand-500 h-full rounded-full transition-all"
            :style="{ width: `${authStore.user?.quota?.percent_used || 0}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Change or Upgrade Plan -->
    <div class="space-y-4">
      <h2 class="text-base font-bold text-white">Available Plans</h2>

      <div class="grid md:grid-cols-2 gap-6">
        <!-- Personal -->
        <div class="p-6 rounded-3xl glass-card border border-slate-800 space-y-4 flex flex-col justify-between">
          <div class="space-y-3">
            <h3 class="text-base font-bold text-white">Personal Plan</h3>
            <div class="text-3xl font-black text-white">₹199 <span class="text-xs text-slate-400 font-normal">/ month</span></div>
            <p class="text-xs text-slate-400">200 GB high-speed encrypted vault.</p>
            <div class="text-xs space-y-1.5 text-slate-300 pt-2 border-t border-slate-800">
              <div>✓ 200 GB Storage</div>
              <div>✓ 10 GB max file size</div>
              <div>✓ 30 days version history</div>
            </div>
          </div>
          <button
            @click="upgrade('personal')"
            class="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-white border border-slate-700 transition-colors"
          >
            {{ billingStore.currentSubscription?.plan_details?.code === 'personal' ? 'Current Plan' : 'Select Personal' }}
          </button>
        </div>

        <!-- Business -->
        <div class="p-6 rounded-3xl glass-card border border-brand-500/40 space-y-4 flex flex-col justify-between relative shadow-lg shadow-brand-500/5">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-base font-bold text-white">Business Plan</h3>
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-brand-500 text-white">Recommended</span>
            </div>
            <div class="text-3xl font-black text-white">₹499 <span class="text-xs text-slate-400 font-normal">/ month</span></div>
            <p class="text-xs text-slate-400">2 TB multi-user team storage with priority R2 bandwidth.</p>
            <div class="text-xs space-y-1.5 text-slate-300 pt-2 border-t border-slate-800">
              <div>✓ 2 TB Storage</div>
              <div>✓ Team Access & X25519 Sharing</div>
              <div>✓ 365 days version history</div>
              <div>✓ Priority 24/7 Support</div>
            </div>
          </div>
          <button
            @click="upgrade('business')"
            class="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-xs font-bold text-white shadow-md transition-colors"
          >
            {{ billingStore.currentSubscription?.plan_details?.code === 'business' ? 'Current Plan' : 'Upgrade with Razorpay' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Invoices Table -->
    <div class="space-y-4 pt-4">
      <h2 class="text-base font-bold text-white">Invoice History</h2>
      <div v-if="billingStore.invoices.length === 0" class="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-400">
        No past invoices recorded.
      </div>
      <div v-else class="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden divide-y divide-slate-800/60">
        <div
          v-for="inv in billingStore.invoices"
          :key="inv.id"
          class="p-4 flex items-center justify-between text-xs"
        >
          <div class="flex items-center space-x-3">
            <FileText class="w-4 h-4 text-slate-400" />
            <div>
              <div class="font-bold text-white font-mono">{{ inv.provider_invoice_id || inv.id.slice(0, 8) }}</div>
              <div class="text-[10px] text-slate-400">{{ new Date(inv.issued_at).toLocaleDateString() }}</div>
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <span class="font-bold font-mono text-white">₹{{ inv.amount }}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              {{ inv.status }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

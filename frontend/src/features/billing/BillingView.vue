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
} from "lucide-vue-next";

const route = useRoute();
const authStore = useAuthStore();
const billingStore = useBillingStore();

const isGateRequired = ref(route.query.gate === "required");
const checkoutError = ref("");

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
  <div class="space-y-6 max-w-5xl">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-white tracking-tight">Subscription & Invoices</h1>
        <p class="text-xs text-slate-400">Zero-knowledge storage allocation and Razorpay payment history.</p>
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
          Annual (Save 16%)
        </button>
      </div>
    </div>

    <!-- Gate Required Alert -->
    <div v-if="isGateRequired || !authStore.hasActiveSubscription" class="p-4 rounded-xl bg-amber-950/30 border border-amber-800/50 flex items-start space-x-3 text-xs text-amber-200">
      <Lock class="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
      <div class="space-y-1 leading-relaxed">
        <div class="font-bold text-amber-400">Active Subscription Required</div>
        <p>
          Your vault is encrypted and staged, but file storage requires an active subscription. Please select either the Personal or Business plan below to complete setup via Razorpay.
        </p>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="checkoutError" class="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-xs flex items-center space-x-2.5">
      <AlertTriangle class="w-4 h-4 text-rose-400 shrink-0" />
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
            {{ billingStore.currentSubscription?.plan_details?.name || (authStore.hasActiveSubscription ? 'Personal Plan' : 'No Active Plan') }}
          </div>
          <div class="text-xs text-slate-400">
            <span v-if="billingStore.currentSubscription?.current_period_end">
              Renews on {{ new Date(billingStore.currentSubscription.current_period_end).toLocaleDateString() }} via Razorpay
            </span>
            <span v-else>
              Select a plan below to activate your storage quota.
            </span>
          </div>
        </div>

        <div class="p-3.5 rounded-xl bg-surface-card border border-surface-border text-right min-w-[140px]">
          <div class="text-[11px] text-slate-400 font-medium">Allocated Quota</div>
          <div class="text-2xl font-bold text-white font-mono">
            {{ ((authStore.user?.quota?.bytes_limit || 0) / (1024 * 1024 * 1024)).toFixed(0) }} GB
          </div>
        </div>
      </div>

      <!-- Quota meter -->
      <div class="space-y-2 pt-3 border-t border-surface-border">
        <div class="flex justify-between text-xs text-slate-400">
          <span>Encrypted Storage Used</span>
          <span class="font-mono text-white">{{ authStore.user?.quota?.percent_used || 0 }}%</span>
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

    <!-- Available Plans Grid -->
    <div class="space-y-4">
      <h2 class="text-sm font-bold text-white tracking-tight">Choose Your Plan</h2>

      <div class="grid md:grid-cols-2 gap-6">
        <!-- Personal Plan Card -->
        <div class="vault-panel p-6 rounded-2xl border border-surface-border flex flex-col justify-between space-y-6">
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono uppercase font-bold text-brand-400">Personal Vault</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-surface-elevated text-slate-400">200 GB</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span class="text-3xl font-extrabold text-white">
                ₹{{ billingStore.selectedInterval === 'yearly' ? '1,999' : '199' }}
              </span>
              <span class="text-xs text-slate-400">/ {{ billingStore.selectedInterval === 'yearly' ? 'year' : 'month' }}</span>
            </div>
            <p class="text-xs text-slate-400">Individual zero-knowledge cloud vault for documents, photos, and backups.</p>

            <div class="pt-3 border-t border-surface-border space-y-2 text-xs text-slate-300">
              <div class="flex items-center space-x-2">
                <CheckCircle2 class="w-3.5 h-3.5 text-accent-emerald shrink-0" />
                <span>200 GB Encrypted Storage</span>
              </div>
              <div class="flex items-center space-x-2">
                <CheckCircle2 class="w-3.5 h-3.5 text-accent-emerald shrink-0" />
                <span>10 GB Single File Upload Limit</span>
              </div>
              <div class="flex items-center space-x-2">
                <CheckCircle2 class="w-3.5 h-3.5 text-accent-emerald shrink-0" />
                <span>30-day Automatic Version History</span>
              </div>
            </div>
          </div>

          <button
            @click="handleUpgrade('personal')"
            :disabled="billingStore.isLoading || (billingStore.currentSubscription?.plan_details?.code === 'personal' && authStore.hasActiveSubscription)"
            class="w-full btn-secondary py-2.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-40"
          >
            <span>
              {{ billingStore.currentSubscription?.plan_details?.code === 'personal' && authStore.hasActiveSubscription ? 'Current Active Plan' : 'Select Personal (₹199)' }}
            </span>
          </button>
        </div>

        <!-- Business Plan Card -->
        <div class="vault-panel p-6 rounded-2xl border border-brand-500/40 bg-surface-card flex flex-col justify-between space-y-6 relative">
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono uppercase font-bold text-brand-400">Business Vault</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-brand-600/20 text-brand-400 font-bold uppercase">2 TB Storage</span>
            </div>
            <div class="flex items-baseline space-x-1">
              <span class="text-3xl font-extrabold text-white">
                ₹{{ billingStore.selectedInterval === 'yearly' ? '4,999' : '499' }}
              </span>
              <span class="text-xs text-slate-400">/ {{ billingStore.selectedInterval === 'yearly' ? 'year' : 'month' }}</span>
            </div>
            <p class="text-xs text-slate-400">High-capacity encrypted workspace for teams and professionals.</p>

            <div class="pt-3 border-t border-surface-border space-y-2 text-xs text-slate-300">
              <div class="flex items-center space-x-2">
                <CheckCircle2 class="w-3.5 h-3.5 text-accent-emerald shrink-0" />
                <span>2 TB (2,048 GB) Encrypted Storage</span>
              </div>
              <div class="flex items-center space-x-2">
                <CheckCircle2 class="w-3.5 h-3.5 text-accent-emerald shrink-0" />
                <span>50 GB Single File Upload Limit</span>
              </div>
              <div class="flex items-center space-x-2">
                <CheckCircle2 class="w-3.5 h-3.5 text-accent-emerald shrink-0" />
                <span>90-day Version Retention & Audit Logs</span>
              </div>
            </div>
          </div>

          <button
            @click="handleUpgrade('business')"
            :disabled="billingStore.isLoading || (billingStore.currentSubscription?.plan_details?.code === 'business' && authStore.hasActiveSubscription)"
            class="w-full btn-primary py-2.5 rounded-xl text-xs font-semibold text-white flex items-center justify-center space-x-2 disabled:opacity-40"
          >
            <span>
              {{ billingStore.currentSubscription?.plan_details?.code === 'business' && authStore.hasActiveSubscription ? 'Current Active Plan' : 'Upgrade to Business with Razorpay' }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Invoice History -->
    <div class="space-y-4 pt-2">
      <h2 class="text-sm font-bold text-white tracking-tight">Invoice & Payment History</h2>

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
              <div class="text-[10px] text-slate-400">{{ new Date(inv.issued_at).toLocaleDateString() }}</div>
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

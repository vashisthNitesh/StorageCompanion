<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { Check, Download, Loader2, AlertCircle, Receipt, HardDrive, CalendarClock } from "lucide-vue-next";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore, type Plan, type Invoice } from "../../stores/billing";
import { useToastStore } from "../../stores/toast";
import { formatBytes, formatDate, formatMoney } from "../../lib/format";
import { GST_STATES } from "../../lib/gstStates";
import ConfirmDialog from "../../components/ConfirmDialog.vue";

const route = useRoute();
const authStore = useAuthStore();
const billing = useBillingStore();
const toast = useToastStore();

const interval = ref<"monthly" | "yearly">("yearly");
const billingState = ref<string>(safeGet("sc_billing_state"));
const loading = ref(true);
const payingPlan = ref<string | null>(null);
const checkoutError = ref("");
const confirmCancel = ref(false);
const downloading = ref<string | null>(null);

const highlighted = computed(() => (typeof route.query.plan === "string" ? route.query.plan : "value"));
const sub = computed(() => billing.currentSubscription);
const profileSub = computed(() => authStore.user?.subscription);
const isActive = computed(() => !!profileSub.value?.can_upload);

function safeGet(key: string) {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function price(plan: Plan) {
  return interval.value === "yearly" ? parseFloat(plan.price_yearly) : parseFloat(plan.price_monthly);
}
function savings(plan: Plan) {
  const monthly = parseFloat(plan.price_monthly) * 12;
  const yearly = parseFloat(plan.price_yearly);
  return monthly > yearly ? Math.round(((monthly - yearly) / monthly) * 100) : 0;
}
function storageLabel(bytes: number) {
  const gb = bytes / 1024 ** 3;
  return gb >= 1000 ? `${(gb / 1000).toFixed(gb % 1000 ? 1 : 0)} TB` : `${Math.round(gb)} GB`;
}

async function choose(plan: Plan) {
  checkoutError.value = "";
  if (!billingState.value) {
    checkoutError.value = "Select your state so we can issue a correct GST invoice.";
    document.getElementById("billing-state")?.focus();
    return;
  }
  try {
    localStorage.setItem("sc_billing_state", billingState.value);
  } catch {
    // ignore
  }
  payingPlan.value = plan.code;
  try {
    await billing.checkout(plan.code, interval.value, billingState.value);
    toast.success(`You're on ${plan.name}. Happy uploading!`);
  } catch (err: any) {
    checkoutError.value = err.message || "Payment failed. You haven't been charged.";
  } finally {
    payingPlan.value = null;
  }
}

async function cancelPlan() {
  await billing.cancel();
  toast.info("Your plan won't renew. It stays active until the end of the period.");
}

async function downloadInvoice(inv: Invoice) {
  downloading.value = inv.id;
  try {
    await billing.downloadInvoice(inv);
  } catch (err: any) {
    toast.error(err.message || "Couldn't download the invoice.");
  } finally {
    downloading.value = null;
  }
}

function statusBadge(status: string) {
  if (["active", "extended", "trialing"].includes(status)) return { cls: "badge-green", text: "Active" };
  if (["grace_period", "expired", "past_due"].includes(status)) return { cls: "badge-amber", text: "Expired" };
  if (status === "canceled") return { cls: "badge-amber", text: "Cancelled" };
  return { cls: "badge-gray", text: status.replace("_", " ") };
}

onMounted(async () => {
  await Promise.all([billing.fetchPlans(), billing.fetchSubscription(), billing.fetchInvoices(), authStore.fetchAuthConfig()]);
  loading.value = false;
});
</script>

<template>
  <div>
    <h1 class="page-title">Plan & billing</h1>
    <p class="page-subtitle">Prices include GST. Plans don't renew automatically; we'll remind you in the app a week before yours ends.</p>

    <!-- Current plan -->
    <section class="mt-6 card card-body">
      <div v-if="loading" class="h-16 animate-pulse rounded-lg bg-slate-100"></div>
      <div v-else-if="sub" class="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div class="flex items-center gap-2">
            <h2 class="section-title">{{ sub.plan_details.name }}</h2>
            <span :class="statusBadge(sub.status).cls">{{ statusBadge(sub.status).text }}</span>
          </div>
          <div class="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
            <span class="inline-flex items-center gap-1.5"><HardDrive class="h-4 w-4 text-slate-400" />{{ storageLabel(sub.plan_details.storage_bytes) }} storage</span>
            <span class="inline-flex items-center gap-1.5">
              <CalendarClock class="h-4 w-4 text-slate-400" />
              {{ isActive ? (sub.cancel_at_period_end ? "Ends" : "Active until") : "Ended" }} {{ formatDate(sub.current_period_end) }}
            </span>
          </div>
          <p v-if="!isActive && profileSub?.grace_period_ends_at" class="mt-2 text-sm text-amber-800">
            Your files are kept until {{ formatDate(profileSub.grace_period_ends_at) }}. Renew before then to keep them.
          </p>
        </div>
        <div class="md:text-right">
          <p class="text-sm text-slate-500">Storage used</p>
          <p class="text-lg font-semibold text-slate-900">
            {{ formatBytes(authStore.user?.quota?.bytes_used) }}
            <span class="text-sm font-normal text-slate-500">of {{ storageLabel(sub.plan_details.storage_bytes) }}</span>
          </p>
          <button v-if="isActive && !sub.cancel_at_period_end && sub.status === 'active'" class="mt-1 text-sm text-slate-500 underline hover:text-slate-700" @click="confirmCancel = true">
            Don't renew this plan
          </button>
        </div>
      </div>
      <div v-else class="flex items-center gap-3">
        <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600"><HardDrive class="h-5 w-5" /></span>
        <div>
          <h2 class="section-title">No plan yet</h2>
          <p class="text-sm text-slate-500">Pick a plan below to start uploading.</p>
        </div>
      </div>
    </section>

    <!-- Plans -->
    <section class="mt-10">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 class="section-title">{{ sub ? "Change or renew your plan" : "Choose a plan" }}</h2>
          <p class="mt-1 text-sm text-slate-500">Buying the plan you already have adds time to it.</p>
        </div>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div>
            <label for="billing-state" class="label">Your state (for GST)</label>
            <select id="billing-state" v-model="billingState" class="input h-9 sm:w-60">
              <option value="" disabled>Select state…</option>
              <option v-for="s in GST_STATES" :key="s.code" :value="s.code">{{ s.name }}</option>
            </select>
          </div>
          <div class="inline-flex rounded-lg border border-slate-200 bg-white p-0.5" role="group" aria-label="Billing period">
            <button
              v-for="opt in (['monthly', 'yearly'] as const)"
              :key="opt"
              class="h-8 rounded-md px-3 text-sm font-medium"
              :class="interval === opt ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'"
              :aria-pressed="interval === opt"
              @click="interval = opt"
            >
              {{ opt === "monthly" ? "Monthly" : "Yearly" }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="!authStore.paymentsEnabled && !loading" class="alert-warning mt-5">
        <AlertCircle class="mt-0.5 h-4 w-4 shrink-0" />
        Online payments are temporarily unavailable. Please try again later.
      </div>
      <div v-if="checkoutError" class="alert-error mt-5" role="alert">
        <AlertCircle class="mt-0.5 h-4 w-4 shrink-0" />{{ checkoutError }}
      </div>
      <div v-if="billing.plansError" class="alert-error mt-5">
        {{ billing.plansError }} <button class="ml-1 underline" @click="billing.fetchPlans()">Retry</button>
      </div>

      <div class="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <template v-if="loading">
          <div v-for="i in 5" :key="i" class="h-72 animate-pulse rounded-xl bg-white ring-1 ring-slate-200"></div>
        </template>
        <article
          v-for="plan in billing.plans"
          v-else
          :key="plan.code"
          class="relative flex flex-col rounded-xl bg-white p-5 ring-1"
          :class="plan.code === highlighted ? 'ring-2 ring-brand-600 shadow-pop' : 'ring-slate-200 shadow-card'"
        >
          <span v-if="plan.code === highlighted" class="badge-blue absolute -top-2.5 left-5 bg-white">Recommended</span>
          <h3 class="font-semibold text-slate-900">{{ plan.name }}</h3>
          <p class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">{{ storageLabel(plan.storage_bytes) }}</p>
          <p class="mt-3">
            <span class="text-xl font-semibold text-slate-900">{{ formatMoney(price(plan), plan.currency) }}</span>
            <span class="text-sm text-slate-500">/{{ interval === "yearly" ? "year" : "month" }}</span>
          </p>
          <p v-if="interval === 'yearly' && savings(plan)" class="text-xs font-medium text-emerald-700">Save {{ savings(plan) }}% vs monthly</p>
          <p class="mt-3 text-sm text-slate-500">{{ plan.description }}</p>
          <ul class="mt-4 flex-1 space-y-2 text-sm text-slate-700">
            <li class="flex gap-2"><Check class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />Files up to {{ storageLabel(plan.max_file_size) }} each</li>
            <li v-for="f in plan.features.slice(1, 4)" :key="f" class="flex gap-2"><Check class="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />{{ f }}</li>
          </ul>
          <button
            class="mt-5 w-full"
            :class="plan.code === highlighted ? 'btn-primary' : 'btn-secondary'"
            :disabled="!!payingPlan || !authStore.paymentsEnabled"
            @click="choose(plan)"
          >
            <Loader2 v-if="payingPlan === plan.code" class="h-4 w-4 animate-spin" />
            {{ sub?.plan_details.code === plan.code ? "Renew" : sub ? "Switch to this plan" : "Choose plan" }}
          </button>
        </article>
      </div>
    </section>

    <!-- Invoices -->
    <section class="mt-10">
      <h2 class="section-title">Invoices</h2>
      <div class="mt-4 card overflow-hidden">
        <div v-if="!billing.invoices.length" class="flex items-center gap-3 px-5 py-6 text-sm text-slate-500">
          <Receipt class="h-5 w-5 text-slate-300" /> Your invoices will appear here after your first payment.
        </div>
        <table v-else class="w-full text-left text-sm">
          <thead class="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th class="px-5 py-2.5 font-medium">Date</th>
              <th class="hidden px-5 py-2.5 font-medium sm:table-cell">Plan</th>
              <th class="px-5 py-2.5 font-medium">Amount</th>
              <th class="px-5 py-2.5"><span class="sr-only">Download</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="inv in billing.invoices" :key="inv.id">
              <td class="px-5 py-3 text-slate-700">{{ formatDate(inv.issued_at) }}</td>
              <td class="hidden px-5 py-3 text-slate-700 sm:table-cell">{{ inv.plan_name || "Storage plan" }} <span class="text-slate-400">· {{ inv.billing_interval || "" }}</span></td>
              <td class="px-5 py-3 font-medium text-slate-900">{{ formatMoney(inv.amount, inv.currency) }}</td>
              <td class="px-5 py-3 text-right">
                <button class="btn-ghost btn-sm" :disabled="downloading === inv.id" @click="downloadInvoice(inv)">
                  <Loader2 v-if="downloading === inv.id" class="h-4 w-4 animate-spin" />
                  <Download v-else class="h-4 w-4" />
                  <span class="hidden sm:inline">Download</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <ConfirmDialog
      :open="confirmCancel"
      title="Stop renewing?"
      :message="`Your plan stays active until ${formatDate(sub?.current_period_end)}. After that, uploads pause and your files are kept for 90 days.`"
      confirm-label="Don't renew"
      :action="cancelPlan"
      @close="confirmCancel = false"
    />
  </div>
</template>

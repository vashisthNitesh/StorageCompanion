<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Download, Receipt, HardDrive, CloudOff, Check, ArrowRight, CalendarPlus } from "lucide-vue-next";
import UiPageHeader from "../../components/ui/UiPageHeader.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiProgress from "../../components/ui/UiProgress.vue";
import UiProgressCircle from "../../components/ui/UiProgressCircle.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiEmptyState from "../../components/ui/UiEmptyState.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore, type Invoice } from "../../stores/billing";
import { normalizeApiError } from "../../lib/errors";
import { reportError } from "../../lib/reportError";
import { formatBytes, formatDate, formatMoney } from "../../lib/format";
import { INCLUDED_IN_ALL, priceFor, storageLabel } from "./planCatalog";

// Plan & billing overview: what you have, how long it lasts, how much space is left, how to
// add time, and invoices. Choosing or changing a plan happens on the plans page.
const authStore = useAuthStore();
const billing = useBillingStore();

const loadingInvoices = ref(true);
const invoicesError = ref<unknown>(null);
const downloading = ref<string | null>(null);

const sub = computed(() => authStore.user?.subscription);
const details = computed(() => billing.currentSubscription);
const quota = computed(() => authStore.user?.quota);
const hasPlan = computed(() => !!sub.value?.plan_code);
const ended = computed(() => hasPlan.value && !sub.value?.can_upload);
const plan = computed(() => billing.plans.find((p) => p.code === sub.value?.plan_code) ?? null);
const interval = computed<"monthly" | "yearly">(() => (details.value?.billing_interval === "monthly" ? "monthly" : "yearly"));
const daysLeft = computed(() => sub.value?.days_until_expiration ?? null);

const usedPct = computed(() => (quota.value?.bytes_limit ? Math.min(100, (quota.value.bytes_used / quota.value.bytes_limit) * 100) : 0));
const freeBytes = computed(() => Math.max(0, (quota.value?.bytes_limit ?? 0) - (quota.value?.bytes_used ?? 0)));

/** How far through the current period we are (for the timeline bar). */
const elapsedPct = computed(() => {
  const start = details.value?.current_period_start ? new Date(details.value.current_period_start).getTime() : 0;
  const end = sub.value?.current_period_end ? new Date(sub.value.current_period_end).getTime() : 0;
  if (!start || !end || end <= start) return 0;
  return Math.min(100, Math.max(0, ((Date.now() - start) / (end - start)) * 100));
});

/** Adding time continues from the current end date while the plan is active, else from today. */
function newEndDate(days: number) {
  const end = sub.value?.current_period_end ? new Date(sub.value.current_period_end).getTime() : 0;
  const from = !ended.value && end > Date.now() ? end : Date.now();
  return new Date(from + days * 86_400_000).toISOString();
}
const addTimeOptions = computed(() =>
  plan.value
    ? [
        { interval: "yearly" as const, label: "1 year", price: priceFor(plan.value, "yearly"), until: newEndDate(365), badge: "2 months free" },
        { interval: "monthly" as const, label: "30 days", price: priceFor(plan.value, "monthly"), until: newEndDate(30), badge: "" },
      ]
    : []
);

const status = computed(() => {
  if (ended.value) return { tone: "warning" as const, text: "Ended" };
  if (daysLeft.value !== null && daysLeft.value <= 7) return { tone: "warning" as const, text: "Ends soon" };
  return { tone: "success" as const, text: "Active" };
});

async function loadInvoices() {
  loadingInvoices.value = true;
  invoicesError.value = null;
  try {
    await billing.fetchInvoices();
  } catch (err) {
    invoicesError.value = err;
  } finally {
    loadingInvoices.value = false;
  }
}

async function downloadInvoice(inv: Invoice) {
  downloading.value = inv.id;
  try {
    await billing.downloadInvoice(inv);
  } catch (err) {
    reportError(err, { retry: () => void downloadInvoice(inv) });
  } finally {
    downloading.value = null;
  }
}

const invoiceStatus = (s: string) =>
  ({
    paid: { tone: "success" as const, label: "Paid" },
    failed: { tone: "danger" as const, label: "Failed" },
    refunded: { tone: "neutral" as const, label: "Refunded" },
  })[s] ?? { tone: "neutral" as const, label: s.charAt(0).toUpperCase() + s.slice(1) };

onMounted(() => {
  void loadInvoices();
  void billing.ensurePlans();
  void billing.fetchSubscription();
});
</script>

<template>
  <div class="max-w-6xl space-y-5">
    <UiPageHeader title="Plan & billing" description="Your plan, storage and invoices. Prices are final, inclusive of all taxes.">
      <template v-if="hasPlan" #actions>
        <UiButton :to="{ name: 'plans' }">Change plan</UiButton>
      </template>
    </UiPageHeader>

    <!-- Loading -->
    <div v-if="!billing.plansLoaded && !billing.plansError" class="grid gap-5 lg:grid-cols-3" aria-busy="true">
      <UiSkeleton class="h-56 rounded-2xl lg:col-span-2" />
      <UiSkeleton class="h-56 rounded-2xl" />
    </div>

    <!-- No plan yet -->
    <section v-else-if="!hasPlan" class="relative overflow-hidden rounded-2xl border border-line bg-surface p-6 shadow-xs sm:p-8" aria-labelledby="no-plan">
      <div class="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-primary/10 blur-3xl" aria-hidden="true" />
      <div class="relative max-w-xl">
        <span class="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-fg"><HardDrive :size="24" :stroke-width="1.75" aria-hidden="true" /></span>
        <h2 id="no-plan" class="mt-4 text-xl font-semibold tracking-tight text-fg">Choose a plan to start uploading</h2>
        <p class="mt-1.5 text-base text-fg-muted">Plans from 25 GB to 1 TB, prepaid monthly or yearly. You can look around first; uploads unlock as soon as you pay.</p>
        <ul class="mt-4 grid gap-2 sm:grid-cols-2">
          <li v-for="item in INCLUDED_IN_ALL.slice(0, 4)" :key="item" class="flex items-center gap-2 text-sm text-fg">
            <Check :size="16" :stroke-width="2.25" class="shrink-0 text-primary" aria-hidden="true" />{{ item }}
          </li>
        </ul>
        <UiButton class="mt-6" variant="primary" size="lg" :icon-right="ArrowRight" :to="{ name: 'plans' }">See plans</UiButton>
      </div>
    </section>

    <template v-else>
      <div class="grid gap-5 lg:grid-cols-3">
        <!-- Current plan -->
        <section class="rounded-2xl border border-line bg-surface p-5 shadow-xs sm:p-6 lg:col-span-2" aria-labelledby="current-plan">
          <p class="text-sm font-medium text-fg-subtle">Current plan</p>
          <div class="mt-1 flex flex-wrap items-center gap-2">
            <h2 id="current-plan" class="text-2xl font-semibold tracking-tight text-fg">{{ sub?.plan_name }}</h2>
            <UiBadge :tone="status.tone" dot>{{ status.text }}</UiBadge>
          </div>
          <p v-if="plan" class="tabular mt-1 text-base text-fg-muted">
            {{ storageLabel(plan.storage_bytes) }} · {{ formatMoney(priceFor(plan, interval)) }} {{ interval === "yearly" ? "per year" : "per 30 days" }} · prepaid
          </p>

          <UiAlert v-if="ended" tone="warning" class="mt-5">
            Your plan ended on {{ formatDate(sub?.current_period_end) }}, so uploads are paused. Your files are kept until {{ formatDate(sub?.grace_period_ends_at) }}.
          </UiAlert>
          <div v-else class="mt-6">
            <div class="tabular flex justify-between gap-3 text-sm text-fg-muted">
              <span>{{ details?.current_period_start ? `Started ${formatDate(details.current_period_start)}` : "Current period" }}</span>
              <span>Ends {{ formatDate(sub?.current_period_end) }}</span>
            </div>
            <UiProgress class="mt-2" :value="elapsedPct" :tone="daysLeft !== null && daysLeft <= 7 ? 'warning' : 'primary'" label="Time used in this period" />
            <p class="tabular mt-2 text-sm text-fg-muted">
              <span class="font-medium text-fg">{{ daysLeft }} {{ daysLeft === 1 ? "day" : "days" }} left</span> · doesn't renew automatically
            </p>
          </div>

          <ul v-if="plan" class="mt-6 grid gap-2 border-t border-line pt-5 text-sm text-fg sm:grid-cols-3">
            <li class="flex items-center gap-2"><Check :size="16" :stroke-width="2.25" class="shrink-0 text-primary" aria-hidden="true" />Files up to {{ storageLabel(plan.max_file_size) }}</li>
            <li class="flex items-center gap-2"><Check :size="16" :stroke-width="2.25" class="shrink-0 text-primary" aria-hidden="true" />{{ plan.version_retention_days }}-day version history</li>
            <li class="flex items-center gap-2"><Check :size="16" :stroke-width="2.25" class="shrink-0 text-primary" aria-hidden="true" />Unmetered downloads</li>
          </ul>
        </section>

        <!-- Storage -->
        <section class="flex flex-col rounded-2xl border border-line bg-surface p-5 shadow-xs sm:p-6" aria-labelledby="storage-heading">
          <h2 id="storage-heading" class="text-base font-semibold text-fg">Storage</h2>
          <div class="relative mx-auto my-5 h-32 w-32" :class="usedPct >= 95 ? 'text-danger' : usedPct >= 80 ? 'text-warning' : 'text-primary'">
            <UiProgressCircle :value="Math.max(usedPct, 1.5)" :size="128" :stroke="10" label="Storage used" />
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="tabular text-2xl font-semibold text-fg">{{ usedPct < 1 ? "<1" : Math.round(usedPct) }}%</span>
              <span class="text-xs text-fg-subtle">used</span>
            </div>
          </div>
          <p class="tabular text-center text-base text-fg">{{ formatBytes(quota?.bytes_used) }} of {{ plan ? storageLabel(plan.storage_bytes) : formatBytes(quota?.bytes_limit, 0) }}</p>
          <p class="tabular text-center text-sm text-fg-subtle">{{ formatBytes(freeBytes) }} free</p>
          <UiButton class="mt-auto pt-0" variant="ghost" block :to="{ name: 'plans' }">Get more space</UiButton>
        </section>
      </div>

      <!-- Add time -->
      <section v-if="plan" class="rounded-2xl border border-line bg-surface p-5 shadow-xs sm:p-6" aria-labelledby="add-time">
        <div class="flex items-start gap-3">
          <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary"><CalendarPlus :size="18" :stroke-width="1.75" aria-hidden="true" /></span>
          <div>
            <h2 id="add-time" class="text-base font-semibold text-fg">{{ ended ? "Renew your plan" : "Add time to your plan" }}</h2>
            <p class="mt-0.5 text-base text-fg-muted">
              <template v-if="ended">Pay for another period of {{ plan.name }} and uploads start again right away.</template>
              <template v-else>
                Plans don't renew on their own. Adding time keeps {{ plan.name }} and continues from {{ formatDate(sub?.current_period_end) }}, so you don't lose any of your
                remaining {{ daysLeft }} days.
              </template>
            </p>
          </div>
        </div>
        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          <div
            v-for="o in addTimeOptions"
            :key="o.interval"
            class="flex items-center justify-between gap-4 rounded-xl border border-line p-4 transition-colors hover:border-line-strong"
          >
            <div class="min-w-0">
              <p class="flex items-center gap-2 text-base font-semibold text-fg">{{ o.label }} <UiBadge v-if="o.badge" tone="success">{{ o.badge }}</UiBadge></p>
              <p class="tabular mt-0.5 text-sm text-fg-muted">{{ formatMoney(o.price) }} · new end date {{ formatDate(o.until) }}</p>
            </div>
            <UiButton
              class="shrink-0"
              :variant="o.interval === 'yearly' ? 'primary' : 'secondary'"
              :to="{ name: 'checkout', query: { plan: plan.code, interval: o.interval } }"
            >
              {{ ended ? "Renew" : "Add" }} {{ o.label }}
            </UiButton>
          </div>
        </div>
      </section>
    </template>

    <!-- Invoices -->
    <section class="overflow-hidden rounded-2xl border border-line bg-surface shadow-xs" aria-labelledby="invoices-heading">
      <div class="flex items-center justify-between gap-3 px-5 pb-3 pt-5 sm:px-6">
        <h2 id="invoices-heading" class="text-base font-semibold text-fg">Invoices</h2>
        <span v-if="billing.invoices.length" class="tabular text-sm text-fg-subtle">{{ billing.invoices.length }} {{ billing.invoices.length === 1 ? "invoice" : "invoices" }}</span>
      </div>
      <div v-if="loadingInvoices" class="space-y-px border-t border-line" aria-busy="true">
        <div v-for="i in 3" :key="i" class="flex h-12 items-center gap-4 px-5"><UiSkeleton class="h-3.5 w-24" /><UiSkeleton class="h-3.5 w-32" /><UiSkeleton class="ml-auto h-3.5 w-16" /></div>
      </div>
      <UiEmptyState v-else-if="invoicesError" compact :icon="CloudOff" tone="danger" title="Couldn't load invoices" :description="normalizeApiError(invoicesError).message">
        <UiButton @click="loadInvoices">Try again</UiButton>
      </UiEmptyState>
      <UiEmptyState v-else-if="!billing.invoices.length" compact :icon="Receipt" tone="neutral" title="No invoices yet" description="Your invoices appear here after each payment." />
      <table v-else class="tabular w-full border-t border-line text-left text-base">
        <thead class="border-b border-line bg-surface-sunken text-sm text-fg-muted">
          <tr>
            <th scope="col" class="px-5 py-2.5 font-medium sm:px-6">Date</th>
            <th scope="col" class="hidden px-4 py-2.5 font-medium sm:table-cell">Invoice</th>
            <th scope="col" class="hidden px-4 py-2.5 font-medium md:table-cell">Plan</th>
            <th scope="col" class="px-4 py-2.5 text-right font-medium">Amount</th>
            <th scope="col" class="px-4 py-2.5 font-medium">Status</th>
            <th scope="col" class="px-4 py-2.5"><span class="sr-only">Download</span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="inv in billing.invoices" :key="inv.id">
            <td class="px-5 py-3 text-fg sm:px-6">{{ formatDate(inv.issued_at) }}</td>
            <td class="hidden px-4 py-3 font-mono text-sm text-fg-muted sm:table-cell">{{ inv.id.slice(0, 8).toUpperCase() }}</td>
            <td class="hidden px-4 py-3 text-fg md:table-cell">{{ inv.plan_name || "Storage plan" }}<span v-if="inv.billing_interval" class="text-fg-subtle"> · {{ inv.billing_interval === "yearly" ? "Yearly" : "Monthly" }}</span></td>
            <td class="px-4 py-3 text-right font-medium text-fg">{{ formatMoney(parseFloat(inv.amount), inv.currency) }}</td>
            <td class="px-4 py-3"><UiBadge :tone="invoiceStatus(inv.status).tone">{{ invoiceStatus(inv.status).label }}</UiBadge></td>
            <td class="px-3 py-3 text-right">
              <UiButton
                variant="ghost"
                size="sm"
                icon-only
                :icon="Download"
                :loading="downloading === inv.id"
                :aria-label="`Download invoice from ${formatDate(inv.issued_at)}`"
                @click="downloadInvoice(inv)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

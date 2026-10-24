<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Download, Receipt, HardDrive, CloudOff } from "lucide-vue-next";
import UiPageHeader from "../../components/ui/UiPageHeader.vue";
import UiCard from "../../components/ui/UiCard.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiProgress from "../../components/ui/UiProgress.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiEmptyState from "../../components/ui/UiEmptyState.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import PlanList from "./PlanList.vue";
import CompareTable from "./CompareTable.vue";
import CheckoutPanel from "./CheckoutPanel.vue";
import IntervalToggle from "./IntervalToggle.vue";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore, type Invoice, type Plan } from "../../stores/billing";
import { normalizeApiError } from "../../lib/errors";
import { reportError } from "../../lib/reportError";
import { formatBytes, formatDate, formatMoney } from "../../lib/format";
import { RECOMMENDED_CODE, storageLabel } from "./planCatalog";

const route = useRoute();
const authStore = useAuthStore();
const billing = useBillingStore();

const interval = ref<"monthly" | "yearly">("yearly");
const loadingInvoices = ref(true);
const invoicesError = ref<unknown>(null);
const downloading = ref<string | null>(null);
const selectedCode = ref("");
const pickerEl = ref<HTMLElement | null>(null);
const checkoutEl = ref<HTMLElement | null>(null);

const sub = computed(() => authStore.user?.subscription);
const quota = computed(() => authStore.user?.quota);
const hasPlan = computed(() => !!sub.value?.has_active_subscription);
const ended = computed(() => !!sub.value?.plan_code && !sub.value?.can_upload);
const currentPlan = computed(() => billing.plans.find((p) => p.code === sub.value?.plan_code) ?? null);
const currentCode = computed(() => (hasPlan.value ? sub.value?.plan_code ?? null : null));
const usedPct = computed(() => (quota.value?.bytes_limit ? Math.min(100, (quota.value.bytes_used / quota.value.bytes_limit) * 100) : 0));
const daysLeft = computed(() => sub.value?.days_until_expiration ?? null);
const selectedPlan = computed<Plan | null>(() => billing.plans.find((p) => p.code === selectedCode.value) ?? null);

/** Selects a plan and brings the order summary into view (it sits below the list on small screens). */
async function choose(code: string) {
  selectedCode.value = code;
  await nextTick();
  if (!window.matchMedia("(min-width: 1024px)").matches) checkoutEl.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}
function extend() {
  if (currentPlan.value) void choose(currentPlan.value.code);
}

// Arriving with ?plan=… (pricing page, plan picker, renewal banner) preselects that plan.
function applyQuery() {
  if (route.query.interval === "monthly" || route.query.interval === "yearly") interval.value = route.query.interval;
  const wanted = typeof route.query.plan === "string" && billing.plans.some((p) => p.code === route.query.plan) ? route.query.plan : null;
  if (wanted) void choose(wanted);
  return !!wanted;
}
watch(() => route.query, () => billing.plansLoaded && applyQuery());
function scrollToPlans() {
  pickerEl.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}

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

const statusBadge = (status: string) =>
  ({
    paid: { tone: "success" as const, label: "Paid" },
    failed: { tone: "danger" as const, label: "Failed" },
    refunded: { tone: "neutral" as const, label: "Refunded" },
  })[status] ?? { tone: "neutral" as const, label: status.charAt(0).toUpperCase() + status.slice(1) };

onMounted(async () => {
  void loadInvoices();
  void authStore.fetchAuthConfig();
  await billing.ensurePlans();
  if (!applyQuery()) selectedCode.value = currentCode.value ?? RECOMMENDED_CODE;
});
</script>

<template>
  <div class="max-w-6xl space-y-6">
    <UiPageHeader title="Plan & billing" description="Prepaid plans in INR, GST included. Plans don't renew automatically." />

    <!-- Current plan -->
    <UiCard v-if="!billing.plansLoaded && !billing.plansError" aria-busy="true">
      <div class="space-y-3">
        <UiSkeleton class="h-5 w-40" />
        <UiSkeleton class="h-2 w-full" />
        <UiSkeleton class="h-4 w-64" />
      </div>
    </UiCard>
    <UiCard v-else-if="sub?.plan_code">
      <div class="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-md font-semibold text-fg">{{ sub.plan_name }}</h2>
            <UiBadge v-if="ended" tone="warning">Ended</UiBadge>
            <UiBadge v-else-if="daysLeft !== null && daysLeft <= 7" tone="warning">Ends soon</UiBadge>
            <UiBadge v-else tone="success" dot>Active</UiBadge>
          </div>
          <div class="mt-4 max-w-md">
            <UiProgress :value="usedPct" :tone="usedPct >= 95 ? 'danger' : usedPct >= 80 ? 'warning' : 'primary'" label="Storage used" />
            <p class="tabular mt-2 text-base text-fg-muted">
              {{ formatBytes(quota?.bytes_used) }} of {{ currentPlan ? storageLabel(currentPlan.storage_bytes) : formatBytes(quota?.bytes_limit, 0) }} used
            </p>
          </div>
          <p class="tabular mt-3 text-base text-fg-muted">
            <template v-if="ended">
              Ended on {{ formatDate(sub.current_period_end) }}. Your files are kept until {{ formatDate(sub.grace_period_ends_at) }}; renew to upload again.
            </template>
            <template v-else>
              Valid until <span class="font-medium text-fg">{{ formatDate(sub.current_period_end) }}</span>
              <template v-if="daysLeft !== null"> · {{ daysLeft }} {{ daysLeft === 1 ? "day" : "days" }} left</template>
            </template>
          </p>
        </div>
        <div class="flex shrink-0 gap-2">
          <UiButton variant="primary" :disabled="!currentPlan" @click="extend">{{ ended ? "Renew plan" : "Extend plan" }}</UiButton>
          <UiButton @click="scrollToPlans">Change plan</UiButton>
        </div>
      </div>
    </UiCard>
    <UiCard v-else>
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
        <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary"><HardDrive :size="20" :stroke-width="1.75" aria-hidden="true" /></span>
        <div class="flex-1">
          <h2 class="text-md font-semibold text-fg">No plan yet</h2>
          <p class="text-base text-fg-muted">Pick a plan below to start uploading. Your files are encrypted on your device.</p>
        </div>
      </div>
    </UiCard>

    <!-- Plans -->
    <section ref="pickerEl" class="scroll-mt-6" aria-labelledby="plans-heading">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="plans-heading" class="text-md font-semibold text-fg">{{ hasPlan ? "Change or extend your plan" : "Choose a plan" }}</h2>
          <p class="mt-1 max-w-2xl text-base text-fg-muted">Every plan is encrypted on your device, keeps original quality and has unmetered downloads. Prices include GST.</p>
        </div>
        <IntervalToggle v-model="interval" class="shrink-0" />
      </div>
      <UiAlert v-if="billing.plansError" class="mt-5">
        {{ normalizeApiError(billing.plansError).message }}
        <template #action><UiButton size="sm" @click="billing.fetchPlans()">Retry</UiButton></template>
      </UiAlert>
      <div v-else class="mt-5 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div>
          <PlanList
            v-model="selectedCode"
            :plans="billing.plans"
            :interval="interval"
            :current-code="currentCode"
            :used-bytes="quota?.bytes_used"
            :loading="!billing.plansLoaded"
          />
          <details class="mt-5">
            <summary class="inline-flex cursor-pointer select-none items-center gap-1.5 rounded text-base font-medium text-primary hover:underline">
              Compare all features
            </summary>
            <div class="mt-4"><CompareTable :plans="billing.plans" :current-code="currentCode" /></div>
          </details>
        </div>
        <div ref="checkoutEl" class="scroll-mt-6 lg:sticky lg:top-6">
          <CheckoutPanel :interval="interval" :plan="selectedPlan" :used-bytes="quota?.bytes_used" />
        </div>
      </div>
    </section>

    <!-- Invoices -->
    <section aria-labelledby="invoices-heading">
      <h2 id="invoices-heading" class="text-md font-semibold text-fg">Invoices</h2>
      <div class="mt-4 overflow-hidden rounded-lg border border-line bg-surface">
        <div v-if="loadingInvoices" class="space-y-px" aria-busy="true">
          <div v-for="i in 3" :key="i" class="flex h-12 items-center gap-4 px-4"><UiSkeleton class="h-3.5 w-24" /><UiSkeleton class="h-3.5 w-32" /><UiSkeleton class="ml-auto h-3.5 w-16" /></div>
        </div>
        <UiEmptyState v-else-if="invoicesError" compact :icon="CloudOff" tone="danger" title="Couldn't load invoices" :description="normalizeApiError(invoicesError).message">
          <UiButton @click="loadInvoices">Try again</UiButton>
        </UiEmptyState>
        <UiEmptyState v-else-if="!billing.invoices.length" compact :icon="Receipt" tone="neutral" title="No invoices yet" description="Your GST invoices appear here after each payment." />
        <table v-else class="tabular w-full text-left text-base">
          <thead class="border-b border-line bg-surface-sunken text-sm text-fg-muted">
            <tr>
              <th scope="col" class="px-4 py-2.5 font-medium">Date</th>
              <th scope="col" class="hidden px-4 py-2.5 font-medium sm:table-cell">Invoice</th>
              <th scope="col" class="hidden px-4 py-2.5 font-medium md:table-cell">Plan</th>
              <th scope="col" class="px-4 py-2.5 text-right font-medium">Amount</th>
              <th scope="col" class="px-4 py-2.5 font-medium">Status</th>
              <th scope="col" class="px-4 py-2.5"><span class="sr-only">Download</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line">
            <tr v-for="inv in billing.invoices" :key="inv.id">
              <td class="px-4 py-3 text-fg">{{ formatDate(inv.issued_at) }}</td>
              <td class="hidden px-4 py-3 font-mono text-sm text-fg-muted sm:table-cell">{{ inv.id.slice(0, 8).toUpperCase() }}</td>
              <td class="hidden px-4 py-3 text-fg md:table-cell">{{ inv.plan_name || "Storage plan" }}<span v-if="inv.billing_interval" class="text-fg-subtle"> · {{ inv.billing_interval === "yearly" ? "Yearly" : "Monthly" }}</span></td>
              <td class="px-4 py-3 text-right font-medium text-fg">{{ formatMoney(parseFloat(inv.amount), inv.currency) }}</td>
              <td class="px-4 py-3"><UiBadge :tone="statusBadge(inv.status).tone">{{ statusBadge(inv.status).label }}</UiBadge></td>
              <td class="px-2 py-3 text-right">
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
      </div>
    </section>

  </div>
</template>

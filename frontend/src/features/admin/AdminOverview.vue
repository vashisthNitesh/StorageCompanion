<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { Users, HardDrive, IndianRupee, Activity, RefreshCw, Server, AlertTriangle, CalendarClock, CloudOff } from "lucide-vue-next";
import { apiRequest } from "../../lib/api";
import { toast } from "../../lib/toast";
import { confirmDialog } from "../../lib/confirm";
import { normalizeApiError } from "../../lib/errors";
import { formatMoney, formatRelative } from "../../lib/format";
import UiButton from "../../components/ui/UiButton.vue";
import UiCard from "../../components/ui/UiCard.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiProgress from "../../components/ui/UiProgress.vue";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiTooltip from "../../components/ui/UiTooltip.vue";
import UiEmptyState from "../../components/ui/UiEmptyState.vue";

type Period = "daily" | "weekly" | "monthly" | "yearly";
const PERIODS: { value: Period; label: string }[] = [
  { value: "daily", label: "24 h" },
  { value: "weekly", label: "7 days" },
  { value: "monthly", label: "30 days" },
  { value: "yearly", label: "12 months" },
];

const period = ref<Period>("weekly");
const kpis = ref<any>(null);
const pool = ref<any>(null);
const loading = ref(true);
const error = ref<unknown>(null);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    [kpis.value, pool.value] = await Promise.all([
      apiRequest(`/api/v1/admin/kpis/?period=${period.value}`, { timeoutMs: 60_000 }),
      apiRequest("/api/v1/admin/pool/"),
    ]);
  } catch (err) {
    error.value = err;
  } finally {
    loading.value = false;
  }
}

async function runLifecycle() {
  let summary: Record<string, number> = {};
  const ok = await confirmDialog({
    title: "Run the expiry check now?",
    body: "Plans past their end date will be expired or cancelled, and data more than 90 days past expiry will be permanently deleted. This normally runs automatically.",
    confirmLabel: "Run expiry check",
    danger: true,
    action: async () => {
      const res = await apiRequest<{ summary: Record<string, number> }>("/api/v1/admin/process-lifecycle/", { method: "POST" });
      summary = res.summary || {};
    },
  });
  if (!ok) return;
  toast.success(
    `Expiry check done: ${summary.transitioned_to_expired ?? 0} expired, ${summary.transitioned_to_canceled ?? 0} cancelled, ${summary.purged_after_90_days ?? 0} purged.`
  );
  await load();
}

const maxTrend = computed(() => Math.max(1, ...(kpis.value?.activity_trend || []).map((t: any) => t.total || 0)));
const trendTotal = computed(() => (kpis.value?.activity_trend || []).reduce((s: number, t: any) => s + (t.total || 0), 0));
const cards = computed(() => {
  const k = kpis.value?.kpis;
  if (!k) return [];
  return [
    { label: "Customers", value: Number(k.total_users).toLocaleString(), sub: `+${k.new_users} new this period`, icon: Users },
    { label: "Active this period", value: Number(k.active_users).toLocaleString(), sub: `${k.total_files} files · ${k.total_folders} folders`, icon: Activity },
    { label: "Storage used", value: `${k.pool_used_gb} GB`, sub: `of ${k.pool_total_gb} GB pool (${k.pool_percent_used}%)`, icon: HardDrive },
    { label: "Monthly revenue", value: formatMoney(k.monthly_recurring_revenue), sub: `Most popular: ${k.most_popular_plan}`, icon: IndianRupee },
  ];
});
const healthTone = (h: string) => (h === "optimal" ? "success" : h === "warning" ? "warning" : "danger");

const ACTIONS: Record<string, string> = {
  "auth.login": "signed in",
  "auth.google_login": "signed in with Google",
  "user.registered": "created an account",
  "user.registered_google": "created an account with Google",
  "file.uploaded": "uploaded a file",
  "file.downloaded": "downloaded a file",
  "subscription.activated": "activated a plan",
};
const describe = (action: string) => ACTIONS[action] || action.replace(/[._]/g, " ");

watch(period, load);
onMounted(load);
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <UiSegmented v-model="period" :options="PERIODS" label="Period" />
      <div class="flex gap-2">
        <UiButton :icon="RefreshCw" :loading="loading && !!kpis" @click="load">Refresh</UiButton>
        <UiButton :icon="CalendarClock" tooltip="Expire lapsed plans and purge data past its 90-day retention" @click="runLifecycle">Run expiry check</UiButton>
      </div>
    </div>

    <div v-if="error && !kpis" class="rounded-lg border border-line bg-surface">
      <UiEmptyState :icon="CloudOff" tone="danger" title="Couldn't load the dashboard" :description="normalizeApiError(error).message">
        <UiButton @click="load">Try again</UiButton>
      </UiEmptyState>
    </div>

    <template v-else>
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" :aria-busy="loading">
        <template v-if="!kpis">
          <div v-for="i in 4" :key="i" class="rounded-lg border border-line bg-surface p-5">
            <UiSkeleton class="h-3.5 w-24" />
            <UiSkeleton class="mt-3 h-7 w-20" />
            <UiSkeleton class="mt-2 h-3 w-32" />
          </div>
        </template>
        <UiCard v-for="c in cards" v-else :key="c.label">
          <div class="flex items-center justify-between text-sm text-fg-muted">
            {{ c.label }} <component :is="c.icon" :size="16" :stroke-width="1.75" class="text-fg-subtle" aria-hidden="true" />
          </div>
          <p class="tabular mt-2 text-2xl font-semibold tracking-tight text-fg">{{ c.value }}</p>
          <p class="mt-1 truncate text-sm text-fg-subtle">{{ c.sub }}</p>
        </UiCard>
      </div>

      <UiCard v-if="pool">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center gap-2">
            <Server :size="18" :stroke-width="1.75" class="text-fg-subtle" aria-hidden="true" />
            <h2 class="text-md font-semibold text-fg">SpaceByte storage pool</h2>
            <UiBadge :tone="pool.is_connected ? 'success' : 'danger'" dot>{{ pool.is_connected ? "Connected" : "Not configured" }}</UiBadge>
          </div>
          <UiBadge :tone="healthTone(pool.pool_health)" class="self-start capitalize">{{ pool.pool_health }}</UiBadge>
        </div>
        <p class="mt-2 flex items-start gap-2 text-base text-fg-muted">
          <AlertTriangle v-if="pool.pool_health !== 'optimal'" :size="16" class="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
          {{ pool.health_message }}
        </p>
        <div class="mt-4 space-y-4">
          <div>
            <div class="tabular flex justify-between text-sm text-fg-muted"><span>Physically used</span><span>{{ pool.used_gb }} / {{ pool.total_pool_gb }} GB</span></div>
            <UiProgress class="mt-1.5" :value="pool.percent_used" label="Physically used" />
          </div>
          <div>
            <div class="tabular flex justify-between text-sm text-fg-muted"><span>Sold to customers</span><span>{{ pool.committed_gb }} / {{ pool.total_pool_gb }} GB</span></div>
            <UiProgress class="mt-1.5" :value="pool.committed_percent" :tone="pool.committed_percent > 100 ? 'danger' : 'primary'" label="Sold to customers" />
          </div>
        </div>
      </UiCard>

      <div v-if="kpis" class="grid gap-6 lg:grid-cols-3">
        <UiCard class="lg:col-span-2" title="Activity" description="Sign-ins, uploads and downloads">
          <div class="flex h-44 items-end gap-1" role="img" :aria-label="`Activity chart: ${trendTotal} events this period`">
            <UiTooltip
              v-for="t in kpis.activity_trend"
              :key="t.label"
              :content="`${t.label}: ${t.logins} sign-ins · ${t.uploads} uploads · ${t.downloads ?? 0} downloads`"
            >
              <div class="flex h-full flex-1 flex-col justify-end">
                <div class="w-full rounded-t-sm bg-primary/70 transition-colors hover:bg-primary" :style="{ height: `${(t.total / maxTrend) * 100}%`, minHeight: t.total ? '3px' : '0' }" />
              </div>
            </UiTooltip>
          </div>
          <div class="mt-1.5 flex justify-between text-xs text-fg-subtle" aria-hidden="true">
            <span>{{ kpis.activity_trend[0]?.label }}</span><span>{{ kpis.activity_trend.at(-1)?.label }}</span>
          </div>
        </UiCard>
        <UiCard title="Plans">
          <ul class="space-y-3">
            <li v-for="p in kpis.plan_distribution" :key="p.code">
              <div class="flex justify-between text-base"><span class="text-fg">{{ p.name }}</span><span class="tabular text-fg-muted">{{ p.count }}</span></div>
              <UiProgress class="mt-1.5" size="sm" :value="p.percent" :label="`${p.name} share`" />
            </li>
          </ul>
        </UiCard>
      </div>

      <UiCard v-if="kpis" title="Recent activity" :padded="false">
        <ul class="mt-3 divide-y divide-line border-t border-line">
          <li v-if="!kpis.recent_activity.length" class="px-5 py-6 text-center text-base text-fg-muted sm:px-6">No activity yet.</li>
          <li v-for="log in kpis.recent_activity" :key="log.id" class="flex items-center justify-between gap-3 px-5 py-2.5 text-base sm:px-6">
            <span class="min-w-0 truncate text-fg-muted"><span class="font-medium text-fg">{{ log.user_email }}</span> {{ describe(log.action) }}</span>
            <span class="tabular shrink-0 text-sm text-fg-subtle">{{ formatRelative(log.created_at) }}</span>
          </li>
        </ul>
      </UiCard>
    </template>
  </div>
</template>

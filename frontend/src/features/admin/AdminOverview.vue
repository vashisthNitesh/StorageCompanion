<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { Users, HardDrive, IndianRupee, Activity, RefreshCw, Loader2, Server, AlertTriangle } from "lucide-vue-next";
import { apiRequest } from "../../lib/api";
import { useToastStore } from "../../stores/toast";
import { formatMoney, formatRelative } from "../../lib/format";

const toast = useToastStore();
const period = ref<"daily" | "weekly" | "monthly" | "yearly">("weekly");
const kpis = ref<any>(null);
const pool = ref<any>(null);
const loading = ref(true);
const error = ref("");
const runningLifecycle = ref(false);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    [kpis.value, pool.value] = await Promise.all([
      apiRequest(`/api/v1/admin/kpis/?period=${period.value}`, { timeoutMs: 60_000 }),
      apiRequest("/api/v1/admin/pool/"),
    ]);
  } catch (err: any) {
    error.value = err.message || "Couldn't load the dashboard.";
  } finally {
    loading.value = false;
  }
}

async function runLifecycle() {
  runningLifecycle.value = true;
  try {
    const res = await apiRequest<{ summary: Record<string, number> }>("/api/v1/admin/process-lifecycle/", { method: "POST" });
    const s = res.summary || {};
    toast.success(
      `Expiry check done: ${s.transitioned_to_expired ?? 0} expired, ${s.transitioned_to_canceled ?? 0} cancelled, ${s.purged_after_90_days ?? 0} purged.`
    );
    await load();
  } catch (err: any) {
    toast.error(err.message || "Expiry check failed.");
  } finally {
    runningLifecycle.value = false;
  }
}

const maxTrend = computed(() => Math.max(1, ...(kpis.value?.activity_trend || []).map((t: any) => t.total || 0)));
const cards = computed(() => {
  const k = kpis.value?.kpis;
  if (!k) return [];
  return [
    { label: "Customers", value: k.total_users, sub: `+${k.new_users} new this period`, icon: Users },
    { label: "Active this period", value: k.active_users, sub: `${k.total_files} files · ${k.total_folders} folders`, icon: Activity },
    { label: "Storage used", value: `${k.pool_used_gb} GB`, sub: `of ${k.pool_total_gb} GB pool (${k.pool_percent_used}%)`, icon: HardDrive },
    { label: "Monthly revenue", value: formatMoney(k.monthly_recurring_revenue), sub: `Most popular: ${k.most_popular_plan}`, icon: IndianRupee },
  ];
});

const ACTIONS: Record<string, string> = {
  "auth.login": "signed in",
  "auth.google_login": "signed in with Google",
  "user.registered": "created an account",
  "user.registered_google": "created an account with Google",
  "file.uploaded": "uploaded a file",
  "file.downloaded": "downloaded a file",
  "subscription.activated": "activated a plan",
};

watch(period, load);
onMounted(load);
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="inline-flex rounded-lg border border-slate-200 bg-white p-0.5" role="group" aria-label="Period">
        <button
          v-for="p in (['daily', 'weekly', 'monthly', 'yearly'] as const)"
          :key="p"
          class="h-8 rounded-md px-3 text-sm font-medium capitalize"
          :class="period === p ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900'"
          @click="period = p"
        >
          {{ p === "daily" ? "24 h" : p === "weekly" ? "7 days" : p === "monthly" ? "30 days" : "12 months" }}
        </button>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" :disabled="loading" title="Reload" @click="load"><RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" /> Refresh</button>
        <button class="btn-secondary" :disabled="runningLifecycle" title="Expire lapsed plans and purge data past its 90-day retention" @click="runLifecycle">
          <Loader2 v-if="runningLifecycle" class="h-4 w-4 animate-spin" /> Run expiry check
        </button>
      </div>
    </div>

    <div v-if="error" class="alert-error">{{ error }} <button class="ml-2 underline" @click="load">Retry</button></div>

    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <template v-if="loading && !kpis">
        <div v-for="i in 4" :key="i" class="h-28 animate-pulse rounded-xl bg-white ring-1 ring-slate-200"></div>
      </template>
      <div v-for="c in cards" v-else :key="c.label" class="card card-body">
        <div class="flex items-center justify-between text-sm text-slate-500">{{ c.label }} <component :is="c.icon" class="h-4 w-4 text-slate-400" /></div>
        <p class="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{{ c.value }}</p>
        <p class="mt-1 truncate text-xs text-slate-500">{{ c.sub }}</p>
      </div>
    </div>

    <div v-if="pool" class="card card-body">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-2">
          <Server class="h-5 w-5 text-slate-400" />
          <h2 class="section-title">SpaceByte storage pool</h2>
          <span :class="pool.is_connected ? 'badge-green' : 'badge-red'">{{ pool.is_connected ? "Connected" : "Not configured" }}</span>
        </div>
        <span :class="pool.pool_health === 'optimal' ? 'badge-green' : pool.pool_health === 'warning' ? 'badge-amber' : 'badge-red'" class="self-start capitalize">
          {{ pool.pool_health }}
        </span>
      </div>
      <p class="mt-2 flex items-start gap-2 text-sm text-slate-600">
        <AlertTriangle v-if="pool.pool_health !== 'optimal'" class="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
        {{ pool.health_message }}
      </p>
      <div class="mt-4 space-y-3">
        <div>
          <div class="flex justify-between text-xs text-slate-500"><span>Physically used</span><span>{{ pool.used_gb }} / {{ pool.total_pool_gb }} GB</span></div>
          <div class="mt-1 h-2 rounded-full bg-slate-100"><div class="h-2 rounded-full bg-brand-600" :style="{ width: `${Math.min(100, pool.percent_used)}%` }"></div></div>
        </div>
        <div>
          <div class="flex justify-between text-xs text-slate-500"><span>Sold to customers</span><span>{{ pool.committed_gb }} / {{ pool.total_pool_gb }} GB</span></div>
          <div class="mt-1 h-2 rounded-full bg-slate-100">
            <div class="h-2 rounded-full" :class="pool.committed_percent > 100 ? 'bg-rose-500' : 'bg-violet-500'" :style="{ width: `${Math.min(100, pool.committed_percent)}%` }"></div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="kpis" class="grid gap-6 lg:grid-cols-3">
      <div class="card card-body lg:col-span-2">
        <h2 class="section-title">Activity</h2>
        <p class="text-xs text-slate-500">Sign-ins, uploads and downloads</p>
        <div class="mt-4 flex h-44 items-end gap-1" role="img" aria-label="Activity chart">
          <div v-for="t in kpis.activity_trend" :key="t.label" class="group relative flex h-full flex-1 flex-col justify-end">
            <div class="w-full rounded-t bg-brand-500/80 group-hover:bg-brand-600" :style="{ height: `${(t.total / maxTrend) * 100}%`, minHeight: t.total ? '3px' : '0' }"></div>
            <div class="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-900 px-2 py-1 text-[11px] text-white group-hover:block">
              {{ t.label }}: {{ t.logins }} sign-ins · {{ t.uploads }} uploads · {{ t.downloads ?? 0 }} downloads
            </div>
          </div>
        </div>
        <div class="mt-1 flex justify-between text-[11px] text-slate-400">
          <span>{{ kpis.activity_trend[0]?.label }}</span><span>{{ kpis.activity_trend.at(-1)?.label }}</span>
        </div>
      </div>
      <div class="card card-body">
        <h2 class="section-title">Plans</h2>
        <ul class="mt-4 space-y-3">
          <li v-for="p in kpis.plan_distribution" :key="p.code">
            <div class="flex justify-between text-sm"><span class="text-slate-700">{{ p.name }}</span><span class="text-slate-500">{{ p.count }}</span></div>
            <div class="mt-1 h-1.5 rounded-full bg-slate-100"><div class="h-1.5 rounded-full bg-brand-600" :style="{ width: `${p.percent}%` }"></div></div>
          </li>
        </ul>
      </div>
    </div>

    <div v-if="kpis" class="card">
      <h2 class="section-title px-5 pt-5 sm:px-6">Recent activity</h2>
      <ul class="mt-3 divide-y divide-slate-100 border-t border-slate-100">
        <li v-for="log in kpis.recent_activity" :key="log.id" class="flex items-center justify-between gap-3 px-5 py-2.5 text-sm sm:px-6">
          <span class="min-w-0 truncate text-slate-700"><span class="font-medium text-slate-900">{{ log.user_email }}</span> {{ ACTIONS[log.action] || log.action }}</span>
          <span class="shrink-0 text-xs text-slate-500">{{ formatRelative(log.created_at) }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

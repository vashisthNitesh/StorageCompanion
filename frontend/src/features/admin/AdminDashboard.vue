<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { apiRequest } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import {
  ShieldAlert,
  Users,
  HardDrive,
  TrendingUp,
  Activity,
  Layers,
  Search,
  CheckCircle2,
  AlertTriangle,
  Server,
  CreditCard,
  ArrowUpRight,
  RefreshCw,
  Sliders,
  UserCheck,
  UserX,
  FileUp,
  Share2,
  Clock,
  Sparkles,
  ShoppingBag,
  X,
} from "lucide-vue-next";

const authStore = useAuthStore();

// Period filter: daily, weekly, monthly, yearly
const selectedPeriod = ref<"daily" | "weekly" | "monthly" | "yearly">("weekly");
const isLoadingKPIs = ref(false);
const isLoadingUsers = ref(false);
const kpisData = ref<any>(null);
const poolData = ref<any>(null);
const usersData = ref<{
  total_count: number;
  page: number;
  page_size: number;
  results: any[];
}>({
  total_count: 0,
  page: 1,
  page_size: 20,
  results: [],
});

// Filters for user management
const searchQuery = ref("");
const selectedPlanFilter = ref("");
const selectedStatusFilter = ref("");

// Capacity purchase modal state
const showBuyCapacityModal = ref(false);
const purchaseSuccessMsg = ref("");

// Plan upgrade modal state
const showUpgradeModal = ref(false);
const selectedUserForUpgrade = ref<any>(null);
const upgradePlanCode = ref("value");
const upgradeBillingInterval = ref("monthly");
const upgradeCustomLimitGB = ref<number | null>(null);
const isUpgrading = ref(false);
const upgradeMessage = ref("");
const upgradeError = ref("");

// Fetch KPI & Analytics Data
async function fetchKPIs() {
  isLoadingKPIs.value = true;
  try {
    const data = await apiRequest<any>(`/api/v1/admin/kpis/?period=${selectedPeriod.value}`);
    kpisData.value = data;
  } catch (err: any) {
    console.error("Failed to load admin KPIs:", err);
  } finally {
    isLoadingKPIs.value = false;
  }
}

// Fetch Upstream Pool Health & Expansion Details
async function fetchPoolStatus() {
  try {
    const data = await apiRequest<any>("/api/v1/admin/pool/");
    poolData.value = data;
  } catch (err: any) {
    console.error("Failed to load pool status:", err);
  }
}

// Fetch Users List
async function fetchUsers() {
  isLoadingUsers.value = true;
  try {
    const params = new URLSearchParams({
      search: searchQuery.value,
      plan: selectedPlanFilter.value,
      status: selectedStatusFilter.value,
      page: usersData.value.page.toString(),
      page_size: usersData.value.page_size.toString(),
    });
    const data = await apiRequest<any>(`/api/v1/admin/users/?${params.toString()}`);
    usersData.value = data;
  } catch (err: any) {
    console.error("Failed to load users:", err);
  } finally {
    isLoadingUsers.value = false;
  }
}

// Open Plan Upgrade Modal
function openUpgradeModal(user: any) {
  selectedUserForUpgrade.value = user;
  upgradePlanCode.value = user.plan?.code !== "none" ? user.plan?.code : "value";
  upgradeBillingInterval.value = user.plan?.billing_interval || "monthly";
  upgradeCustomLimitGB.value = null;
  upgradeMessage.value = "";
  upgradeError.value = "";
  showUpgradeModal.value = true;
}

// Submit Plan Upgrade
async function submitPlanUpgrade() {
  if (!selectedUserForUpgrade.value) return;
  isUpgrading.value = true;
  upgradeError.value = "";
  upgradeMessage.value = "";
  try {
    const res = await apiRequest<any>(
      `/api/v1/admin/users/${selectedUserForUpgrade.value.id}/upgrade-plan/`,
      {
        method: "POST",
        body: JSON.stringify({
          plan_code: upgradePlanCode.value,
          billing_interval: upgradeBillingInterval.value,
          custom_limit_gb: upgradeCustomLimitGB.value,
        }),
      }
    );
    upgradeMessage.value = res.message || "User plan upgraded successfully!";
    await fetchUsers();
    await fetchKPIs();
    await fetchPoolStatus();
    setTimeout(() => {
      showUpgradeModal.value = false;
    }, 1200);
  } catch (err: any) {
    upgradeError.value = err.message || "Failed to update user plan.";
  } finally {
    isUpgrading.value = false;
  }
}

// Toggle User Status (Suspend / Activate)
async function toggleUserStatus(user: any) {
  try {
    const res = await apiRequest<any>(
      `/api/v1/admin/users/${user.id}/toggle-status/`,
      { method: "POST" }
    );
    user.is_active = res.is_active;
    await fetchKPIs();
  } catch (err: any) {
    alert(err.message || "Failed to toggle user status.");
  }
}

// Capacity Expansion Action
function simulateBuyCapacity(tier: any) {
  purchaseSuccessMsg.value = `Simulated request: Expansion order created for ${tier.label} (${tier.estimated_price}). In production, this contacts SpaceByte API or routes to enterprise billing.`;
  setTimeout(() => {
    purchaseSuccessMsg.value = "";
  }, 6000);
}

// Max value helper for activity trend bars
const maxActivityVal = computed(() => {
  if (!kpisData.value?.activity_trend?.length) return 10;
  const max = Math.max(...kpisData.value.activity_trend.map((t: any) => t.total || 0));
  return max > 0 ? max : 10;
});

// Watch period switcher
watch(selectedPeriod, () => {
  fetchKPIs();
});

// Debounce search
let searchTimer: any = null;
function handleSearchInput() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    usersData.value.page = 1;
    fetchUsers();
  }, 300);
}

onMounted(async () => {
  await Promise.all([fetchKPIs(), fetchPoolStatus(), fetchUsers()]);
});
</script>

<template>
  <div class="space-y-6 max-w-7xl pb-12 text-slate-900 selection:bg-indigo-600 selection:text-white">
    <!-- Top Admin Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
      <div class="space-y-1">
        <div class="flex items-center space-x-2.5">
          <div class="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm shadow-indigo-500/20">
            <ShieldAlert class="w-4 h-4" />
          </div>
          <div>
            <h1 class="text-xl font-extrabold text-slate-900 tracking-tight flex items-center space-x-2">
              <span>Master Admin Control Center</span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                Superuser
              </span>
            </h1>
          </div>
        </div>
        <p class="text-xs text-slate-500">
          Global oversight of upstream SpaceByte storage, user subscription tiers, and system activity metrics.
        </p>
      </div>

      <!-- Timeframe Toggle (Daily / Weekly / Monthly / Yearly) -->
      <div class="flex items-center space-x-3">
        <div class="inline-flex items-center p-1 rounded-2xl bg-slate-100 border border-slate-200 text-xs shadow-2xs">
          <button
            @click="selectedPeriod = 'daily'"
            class="px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer"
            :class="selectedPeriod === 'daily' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            Daily
          </button>
          <button
            @click="selectedPeriod = 'weekly'"
            class="px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer"
            :class="selectedPeriod === 'weekly' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            Weekly
          </button>
          <button
            @click="selectedPeriod = 'monthly'"
            class="px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer"
            :class="selectedPeriod === 'monthly' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            Monthly
          </button>
          <button
            @click="selectedPeriod = 'yearly'"
            class="px-3.5 py-1.5 rounded-xl font-semibold transition-all cursor-pointer"
            :class="selectedPeriod === 'yearly' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
          >
            Yearly
          </button>
        </div>

        <button
          @click="fetchKPIs"
          class="p-2 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors"
          title="Refresh KPIs"
        >
          <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': isLoadingKPIs }" />
        </button>
      </div>
    </div>

    <!-- 4 KPI Summary Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Total & New Users -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs text-slate-500 font-medium">
          <span>Total Registered Users</span>
          <Users class="w-4 h-4 text-blue-600" />
        </div>
        <div class="flex items-baseline space-x-2">
          <span class="text-2xl font-extrabold text-slate-900 font-mono">{{ kpisData?.kpis?.total_users || 0 }}</span>
          <span class="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
            +{{ kpisData?.kpis?.new_users || 0 }} in {{ selectedPeriod }}
          </span>
        </div>
        <p class="text-[11px] text-slate-400">All authenticated vault accounts</p>
      </div>

      <!-- Active Users in Timeframe -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs text-slate-500 font-medium">
          <span>Active Users ({{ selectedPeriod }})</span>
          <Activity class="w-4 h-4 text-emerald-600" />
        </div>
        <div class="flex items-baseline space-x-2">
          <span class="text-2xl font-extrabold text-slate-900 font-mono">{{ kpisData?.kpis?.active_users || 1 }}</span>
          <span class="text-xs font-medium text-slate-500">Active sessions / actions</span>
        </div>
        <p class="text-[11px] text-slate-400">Interacted with vault storage</p>
      </div>

      <!-- Storage Pool Consumed -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs text-slate-500 font-medium">
          <span>SpaceByte Pool Consumed</span>
          <HardDrive class="w-4 h-4 text-indigo-600" />
        </div>
        <div class="flex items-baseline space-x-2">
          <span class="text-2xl font-extrabold text-slate-900 font-mono">{{ poolData?.used_gb || 0 }} GB</span>
          <span class="text-xs text-slate-500">of {{ poolData?.total_pool_gb || 1000 }} GB</span>
        </div>
        <div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
          <div
            class="h-full bg-indigo-600 rounded-full transition-all"
            :style="{ width: `${poolData?.percent_used || 0}%` }"
          ></div>
        </div>
      </div>

      <!-- Estimated Revenue (MRR) -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between text-xs text-slate-500 font-medium">
          <span>Monthly Recurring Revenue</span>
          <TrendingUp class="w-4 h-4 text-emerald-600" />
        </div>
        <div class="flex items-baseline space-x-2">
          <span class="text-2xl font-extrabold text-slate-900 font-mono">₹{{ (kpisData?.kpis?.monthly_recurring_revenue || 0).toLocaleString() }}</span>
          <span class="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-bold uppercase">Estimated</span>
        </div>
        <p class="text-[11px] text-slate-400">Sum of active subscription plans</p>
      </div>
    </div>

    <!-- Master Admin Pool Monitor & Upstream Capacity Buying Decision -->
    <div class="bg-gradient-to-br from-indigo-950 via-slate-900 to-indigo-900 text-white p-6 sm:p-7 rounded-2xl shadow-md space-y-5">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div class="space-y-1.5 max-w-2xl">
          <div class="flex items-center space-x-2">
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
              Master Admin Exclusivity
            </span>
            <span
              class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
              :class="poolData?.is_connected ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30' : 'bg-amber-500/20 text-amber-300 border border-amber-400/30'"
            >
              {{ poolData?.is_connected ? 'SpaceByte.in Connected' : 'Testing Pool Mode' }}
            </span>
          </div>
          <h2 class="text-2xl font-extrabold tracking-tight text-white">
            SpaceByte 1 TB Upstream Storage Pool Monitor
          </h2>
          <p class="text-xs text-slate-300 leading-relaxed">
            This upstream pool monitor is strictly hidden from basic users. As Master Admin, monitor total storage utilized across all users, inspect live capacity, and decide whether to purchase additional upstream capacity.
          </p>
        </div>

        <div class="flex items-center space-x-3 shrink-0">
          <button
            @click="showBuyCapacityModal = true"
            class="px-5 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white text-xs font-bold transition-all shadow-md flex items-center space-x-2 cursor-pointer"
          >
            <ShoppingBag class="w-4 h-4" />
            <span>Buy Upstream Capacity</span>
          </button>
        </div>
      </div>

      <!-- Capacity Usage Bars & Metrics -->
      <div class="space-y-3 pt-2">
        <!-- Dual Bars: Physical vs Committed -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="space-y-1.5 bg-white/5 p-3 rounded-xl border border-white/10">
            <div class="flex items-center justify-between text-xs">
              <span class="text-slate-300 font-medium">Physical Data Uploaded</span>
              <span class="font-mono text-emerald-400 font-bold">{{ poolData?.used_gb || 0 }} GB / {{ poolData?.total_pool_gb || 1000 }} GB ({{ poolData?.percent_used || 0 }}%)</span>
            </div>
            <div class="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="poolData?.percent_used > 85 ? 'bg-rose-500' : 'bg-emerald-500'"
                :style="{ width: `${Math.min(100, poolData?.percent_used || 0)}%` }"
              ></div>
            </div>
            <div class="text-[10px] text-slate-400">Actual encrypted bytes stored on upstream SpaceByte/S3.</div>
          </div>

          <div class="space-y-1.5 bg-white/5 p-3 rounded-xl border border-white/10">
            <div class="flex items-center justify-between text-xs">
              <span class="text-slate-300 font-medium">Committed / Allocated Quota</span>
              <span class="font-mono text-indigo-300 font-bold">{{ poolData?.committed_gb || 0 }} GB / {{ poolData?.total_pool_gb || 1000 }} GB ({{ poolData?.committed_percent || 0 }}%)</span>
            </div>
            <div class="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="poolData?.committed_percent > 90 ? 'bg-amber-500' : 'bg-indigo-500'"
                :style="{ width: `${Math.min(100, poolData?.committed_percent || 0)}%` }"
              ></div>
            </div>
            <div class="text-[10px] text-slate-400">Storage capacity promised to {{ poolData?.active_subscribers_count || 0 }} active subscribers.</div>
          </div>
        </div>
      </div>

      <!-- Capacity Usage 5-Card Metrics Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 pt-3 border-t border-slate-800/80">
        <div class="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div class="text-[11px] text-slate-400">Total Upstream Pool</div>
          <div class="text-xl font-bold font-mono">{{ poolData?.total_pool_gb || 1000 }} GB</div>
          <div class="text-[10px] text-indigo-300">Total master pool</div>
        </div>

        <div class="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div class="text-[11px] text-slate-400">Physical Storage Used</div>
          <div class="text-xl font-bold font-mono text-emerald-400">{{ poolData?.used_gb || 0 }} GB</div>
          <div class="text-[10px] text-slate-400">{{ poolData?.percent_used || 0 }}% disk consumed</div>
        </div>

        <div class="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div class="text-[11px] text-slate-400">Committed Quota</div>
          <div class="text-xl font-bold font-mono text-indigo-300">{{ poolData?.committed_gb || 0 }} GB</div>
          <div class="text-[10px] text-slate-400">{{ poolData?.committed_percent || 0 }}% allocated</div>
        </div>

        <div class="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-1">
          <div class="text-[11px] text-slate-400">Uncommitted Left</div>
          <div class="text-xl font-bold font-mono text-blue-300">{{ poolData?.uncommitted_gb ?? 1000 }} GB</div>
          <div class="text-[10px] text-slate-400">Available to sell</div>
        </div>

        <div class="p-3.5 rounded-xl bg-white/5 border border-white/10 space-y-1 sm:col-span-2 lg:col-span-1">
          <div class="text-[11px] text-slate-400">Pool Health & Status</div>
          <div class="text-sm font-bold uppercase tracking-wider flex items-center space-x-1.5" :class="poolData?.pool_health === 'critical' ? 'text-rose-400' : (poolData?.pool_health === 'warning' ? 'text-amber-400' : 'text-emerald-400')">
            <CheckCircle2 class="w-4 h-4" />
            <span>{{ poolData?.pool_health || 'Optimal' }}</span>
          </div>
          <div class="text-[10px] text-slate-400 truncate">{{ poolData?.health_message }}</div>
        </div>
      </div>
    </div>

    <!-- 2 Column Analytics: Plan Popularity & Activity Time-Series -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Plan Popularity & Distribution (Span 1) -->
      <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
        <div class="flex items-center justify-between">
          <div class="space-y-0.5">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2">
              <Layers class="w-4 h-4 text-blue-600" />
              <span>Plan Popularity Distribution</span>
            </h3>
            <p class="text-[11px] text-slate-500">Which pack is most used by customers</p>
          </div>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
            {{ kpisData?.kpis?.most_popular_plan || 'None Yet' }}
          </span>
        </div>

        <!-- Plan Bars -->
        <div class="space-y-3.5">
          <div
            v-for="plan in kpisData?.plan_distribution || []"
            :key="plan.code"
            class="space-y-1.5"
          >
            <div class="flex items-center justify-between text-xs">
              <span class="font-semibold text-slate-800 flex items-center space-x-1.5">
                <span>{{ plan.name }}</span>
                <span class="text-[10px] text-slate-400 font-normal">({{ plan.storage_gb }} GB)</span>
              </span>
              <span class="font-mono text-slate-600 text-[11px]">
                <strong class="text-slate-900">{{ plan.count }}</strong> users ({{ plan.percent }}%)
              </span>
            </div>
            <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="plan.count > 0 ? 'bg-blue-600' : 'bg-slate-300'"
                :style="{ width: `${Math.max(plan.percent, 3)}%` }"
              ></div>
            </div>
          </div>
        </div>

        <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
          <div class="font-bold text-slate-900 flex items-center space-x-1.5">
            <Sparkles class="w-3.5 h-3.5 text-amber-600" />
            <span>Platform Status</span>
          </div>
          <p class="text-[11px] text-slate-500 leading-relaxed">
            <template v-if="kpisData?.kpis?.most_popular_plan && kpisData?.kpis?.most_popular_plan !== 'None Yet'">
              The <strong>{{ kpisData.kpis.most_popular_plan }}</strong> is currently the top choice among customers.
            </template>
            <template v-else>
              Clean state ready for operation. Active customer plan trends will appear here as users subscribe.
            </template>
          </p>
        </div>
      </div>

      <!-- Activity Timeline Chart (Span 2) -->
      <div class="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="space-y-0.5">
            <h3 class="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2">
              <Activity class="w-4 h-4 text-emerald-600" />
              <span>System Activity Trend ({{ selectedPeriod.toUpperCase() }})</span>
            </h3>
            <p class="text-[11px] text-slate-500">Hourly / Daily activity volume (Logins, Uploads, Shares)</p>
          </div>
          <div class="flex items-center space-x-4 text-[11px] text-slate-500">
            <div class="flex items-center space-x-1.5">
              <span class="w-2.5 h-2.5 rounded-full bg-blue-600"></span>
              <span>Uploads</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span>Logins</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
              <span>Shares</span>
            </div>
          </div>
        </div>

        <!-- Interactive Bar Visualization -->
        <div class="pt-4">
          <div class="h-44 flex items-end justify-between gap-1 sm:gap-2 px-1 border-b border-slate-200">
            <div
              v-for="(point, idx) in kpisData?.activity_trend || []"
              :key="idx"
              class="flex-1 flex flex-col items-center group relative h-full justify-end"
            >
              <!-- Bar Tooltip -->
              <div class="absolute -top-12 hidden group-hover:flex flex-col items-center bg-slate-900 text-white text-[10px] px-2 py-1 rounded shadow-lg z-20 pointer-events-none whitespace-nowrap">
                <span>{{ point.label }}</span>
                <span class="font-mono text-indigo-300">Total: {{ point.total }} events</span>
              </div>

              <!-- Bar Stack -->
              <div class="w-full max-w-[28px] rounded-t-sm flex flex-col justify-end overflow-hidden transition-all group-hover:brightness-110" :style="{ height: `${Math.min(100, Math.max(8, (point.total / maxActivityVal) * 100))}%` }">
                <div class="w-full bg-blue-600" :style="{ height: `${point.total ? (point.uploads / point.total) * 100 : 33}%` }"></div>
                <div class="w-full bg-emerald-500" :style="{ height: `${point.total ? (point.logins / point.total) * 100 : 33}%` }"></div>
                <div class="w-full bg-indigo-500" :style="{ height: `${point.total ? (point.shares / point.total) * 100 : 34}%` }"></div>
              </div>
            </div>
          </div>

          <!-- X-Axis Labels -->
          <div class="flex justify-between text-[9px] text-slate-400 font-mono pt-2 px-1">
            <span>{{ kpisData?.activity_trend?.[0]?.label || 'Start' }}</span>
            <span>{{ kpisData?.activity_trend?.[Math.floor((kpisData?.activity_trend?.length || 0)/2)]?.label || 'Mid' }}</span>
            <span>{{ kpisData?.activity_trend?.[(kpisData?.activity_trend?.length || 1) - 1]?.label || 'Now' }}</span>
          </div>
        </div>

        <!-- Metric badges footer -->
        <div class="grid grid-cols-3 gap-3 pt-3 border-t border-slate-100 text-center">
          <div class="p-2.5 rounded-xl bg-slate-50">
            <div class="text-[10px] text-slate-500">Vault Files Staged</div>
            <div class="text-base font-bold font-mono text-slate-900">{{ kpisData?.kpis?.total_files || 0 }}</div>
          </div>
          <div class="p-2.5 rounded-xl bg-slate-50">
            <div class="text-[10px] text-slate-500">Vault Folders Created</div>
            <div class="text-base font-bold font-mono text-slate-900">{{ kpisData?.kpis?.total_folders || 0 }}</div>
          </div>
          <div class="p-2.5 rounded-xl bg-slate-50">
            <div class="text-[10px] text-slate-500">Timeframe Events</div>
            <div class="text-base font-bold font-mono text-slate-900">
              {{ (kpisData?.activity_trend || []).reduce((acc: number, cur: any) => acc + (cur.total || 0), 0) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- User Management Table & Plan Upgrade Actions -->
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 class="text-base font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Users class="w-4 h-4 text-indigo-600" />
            <span>User Management & Plan Control</span>
          </h3>
          <p class="text-xs text-slate-500">
            Manage all registered users, upgrade or adjust storage quotas, and toggle account states.
          </p>
        </div>

        <!-- Filter Controls -->
        <div class="flex flex-wrap items-center gap-2.5">
          <!-- Search input -->
          <div class="relative">
            <Search class="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              v-model="searchQuery"
              @input="handleSearchInput"
              placeholder="Search user or email..."
              class="pl-9 pr-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <!-- Plan filter -->
          <select
            v-model="selectedPlanFilter"
            @change="fetchUsers"
            class="px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Plans</option>
            <option value="entry">Entry Pack (25 GB)</option>
            <option value="smart">Smart Pack (100 GB)</option>
            <option value="value">Value Pack (200 GB)</option>
            <option value="super">Super Pack (400 GB)</option>
            <option value="mega">Mega Pack (1 TB)</option>
          </select>

          <!-- Status filter -->
          <select
            v-model="selectedStatusFilter"
            @change="fetchUsers"
            class="px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="suspended">Suspended Only</option>
          </select>
        </div>
      </div>

      <!-- Users Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider bg-slate-50/70">
              <th class="py-3 px-4 rounded-l-xl">User Profile</th>
              <th class="py-3 px-4">Subscription Plan</th>
              <th class="py-3 px-4">Storage Consumed</th>
              <th class="py-3 px-4">Account Status</th>
              <th class="py-3 px-4">Joined Date</th>
              <th class="py-3 px-4 text-right rounded-r-xl">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="user in usersData.results"
              :key="user.id"
              class="hover:bg-slate-50/70 transition-colors"
            >
              <!-- Profile -->
              <td class="py-3 px-4">
                <div class="flex items-center space-x-2.5">
                  <div
                    class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shrink-0 border"
                    :class="user.is_staff ? 'bg-indigo-100 text-indigo-700 border-indigo-200' : 'bg-slate-100 text-slate-700 border-slate-200'"
                  >
                    {{ (user.full_name || user.email || 'U')[0].toUpperCase() }}
                  </div>
                  <div>
                    <div class="font-bold text-slate-900 flex items-center space-x-1.5">
                      <span>{{ user.full_name }}</span>
                      <span v-if="user.is_staff" class="text-[9px] bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.2 rounded font-mono font-bold uppercase">
                        Admin
                      </span>
                    </div>
                    <div class="text-slate-500 font-mono text-[11px]">{{ user.email }}</div>
                  </div>
                </div>
              </td>

              <!-- Plan -->
              <td class="py-3 px-4">
                <div class="space-y-0.5">
                  <div class="font-semibold text-slate-900">{{ user.plan.name }}</div>
                  <div class="text-[10px] text-slate-500 uppercase tracking-wider font-mono">
                    {{ user.plan.billing_interval }} • {{ user.plan.status }}
                  </div>
                </div>
              </td>

              <!-- Storage Used vs Quota -->
              <td class="py-3 px-4">
                <div class="space-y-1 max-w-[160px]">
                  <div class="flex justify-between text-[11px] font-mono">
                    <span class="text-slate-700 font-semibold">{{ user.storage.used_formatted }}</span>
                    <span class="text-slate-400">/ {{ user.storage.limit_formatted }}</span>
                  </div>
                  <div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all"
                      :class="user.storage.percent_used > 85 ? 'bg-rose-500' : 'bg-blue-600'"
                      :style="{ width: `${user.storage.percent_used}%` }"
                    ></div>
                  </div>
                </div>
              </td>

              <!-- Status -->
              <td class="py-3 px-4">
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider"
                  :class="user.is_active ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'"
                >
                  {{ user.is_active ? 'Active' : 'Suspended' }}
                </span>
              </td>

              <!-- Joined -->
              <td class="py-3 px-4 text-slate-500 text-[11px]">
                {{ new Date(user.date_joined).toLocaleDateString() }}
              </td>

              <!-- Action Buttons -->
              <td class="py-3 px-4 text-right">
                <div class="flex items-center justify-end space-x-2">
                  <button
                    v-if="!user.is_staff && !user.is_superuser"
                    @click="openUpgradeModal(user)"
                    class="px-3 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-xs transition-colors border border-indigo-200 cursor-pointer"
                  >
                    Change Plan
                  </button>
                  <span
                    v-else
                    class="px-2.5 py-1 text-[10px] font-mono text-indigo-600 font-semibold bg-indigo-50 rounded-lg border border-indigo-100"
                  >
                    System Manager
                  </span>

                  <button
                    v-if="!user.is_staff"
                    @click="toggleUserStatus(user)"
                    class="p-1 rounded-lg text-slate-400 hover:text-slate-700 transition-colors"
                    :title="user.is_active ? 'Suspend User' : 'Activate User'"
                  >
                    <UserX v-if="user.is_active" class="w-4 h-4 text-rose-500" />
                    <UserCheck v-else class="w-4 h-4 text-emerald-600" />
                  </button>
                </div>
              </td>
            </tr>

            <tr v-if="usersData.results.length === 0">
              <td colspan="6" class="py-8 text-center text-slate-500 text-xs">
                No users matched the search query or filters.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Recent Audit Activity Stream -->
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2">
          <Clock class="w-4 h-4 text-slate-500" />
          <span>Recent Administrative & User Activity</span>
        </h3>
        <span class="text-xs text-slate-400">Live system audit events</span>
      </div>

      <div class="divide-y divide-slate-100 max-h-64 overflow-y-auto">
        <div
          v-for="log in kpisData?.recent_activity || []"
          :key="log.id"
          class="py-2.5 flex items-center justify-between text-xs"
        >
          <div class="flex items-center space-x-3">
            <span
              class="w-2 h-2 rounded-full"
              :class="log.action.startsWith('admin') ? 'bg-indigo-600' : 'bg-emerald-500'"
            ></span>
            <span class="font-mono font-semibold text-slate-800">{{ log.action }}</span>
            <span class="text-slate-500 font-mono text-[11px]">{{ log.user_email }}</span>
          </div>
          <div class="text-[11px] text-slate-400 font-mono">
            {{ new Date(log.created_at).toLocaleTimeString() }}
          </div>
        </div>
      </div>
    </div>

    <!-- Capacity Purchase Modal -->
    <div
      v-if="showBuyCapacityModal"
      class="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4"
    >
      <div class="bg-white max-w-lg w-full rounded-2xl border border-slate-200 shadow-2xl p-6 space-y-5">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <div class="flex items-center space-x-2">
            <Server class="w-5 h-5 text-indigo-600" />
            <h3 class="text-base font-bold text-slate-900">Purchase Upstream SpaceByte Capacity</h3>
          </div>
          <button @click="showBuyCapacityModal = false" class="text-slate-400 hover:text-slate-700">
            <X class="w-5 h-5" />
          </button>
        </div>

        <p class="text-xs text-slate-600 leading-relaxed">
          Expand the global upstream SpaceByte.in storage pool beyond the current 1 TB testing allocation. When selected, capacity will automatically be updated in <code class="font-mono bg-slate-100 px-1 rounded text-indigo-700">SPACEBYTE_STORAGE_POOL_LIMIT_BYTES</code>.
        </p>

        <!-- Expansion Tiers -->
        <div class="space-y-3">
          <div
            v-for="tier in poolData?.expansion_tiers || []"
            :key="tier.size_gb"
            class="p-4 rounded-xl border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/30 transition-all flex items-center justify-between"
          >
            <div>
              <div class="font-bold text-slate-900 text-sm">{{ tier.label }}</div>
              <div class="text-xs text-slate-500 font-mono">Capacity: +{{ tier.size_gb }} GB</div>
            </div>
            <div class="text-right space-y-1">
              <div class="font-bold text-indigo-700 text-sm font-mono">{{ tier.estimated_price }}</div>
              <button
                @click="simulateBuyCapacity(tier)"
                class="px-3 py-1 rounded-lg bg-indigo-600 text-white font-semibold text-[11px] hover:bg-indigo-500 transition-colors cursor-pointer"
              >
                Expand Pool
              </button>
            </div>
          </div>
        </div>

        <div v-if="purchaseSuccessMsg" class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
          {{ purchaseSuccessMsg }}
        </div>

        <div class="pt-2 flex justify-end">
          <button
            @click="showBuyCapacityModal = false"
            class="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- User Plan Upgrade Modal -->
    <div
      v-if="showUpgradeModal"
      class="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4"
    >
      <div class="bg-white max-w-md w-full rounded-2xl border border-slate-200 shadow-2xl p-6 space-y-5">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3">
          <div class="flex items-center space-x-2">
            <Sliders class="w-5 h-5 text-indigo-600" />
            <h3 class="text-base font-bold text-slate-900">Manage User Plan & Quota</h3>
          </div>
          <button @click="showUpgradeModal = false" class="text-slate-400 hover:text-slate-700">
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-0.5">
          <div class="text-slate-500">Target User:</div>
          <div class="font-bold text-slate-900">{{ selectedUserForUpgrade?.full_name }} ({{ selectedUserForUpgrade?.email }})</div>
          <div class="text-[11px] text-slate-500 font-mono">Current: {{ selectedUserForUpgrade?.plan?.name }}</div>
        </div>

        <div class="space-y-4">
          <!-- Select Plan -->
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Select Subscription Plan</label>
            <select
              v-model="upgradePlanCode"
              class="w-full px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
            >
              <option value="entry">Entry Pack (25 GB - ₹39/mo)</option>
              <option value="smart">Smart Pack (100 GB - ₹89/mo)</option>
              <option value="value">Value Pack (200 GB - ₹149/mo) [Popular]</option>
              <option value="super">Super Pack (400 GB - ₹249/mo)</option>
              <option value="mega">Mega Pack (1 TB - ₹449/mo)</option>
            </select>
          </div>

          <!-- Billing Interval -->
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Billing Interval</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                @click="upgradeBillingInterval = 'monthly'"
                class="py-2 px-3 rounded-xl text-xs font-semibold border transition-all"
                :class="upgradeBillingInterval === 'monthly' ? 'bg-indigo-50 border-indigo-400 text-indigo-700 shadow-xs' : 'border-slate-200 text-slate-600'"
              >
                Monthly
              </button>
              <button
                type="button"
                @click="upgradeBillingInterval = 'yearly'"
                class="py-2 px-3 rounded-xl text-xs font-semibold border transition-all"
                :class="upgradeBillingInterval === 'yearly' ? 'bg-indigo-50 border-indigo-400 text-indigo-700 shadow-xs' : 'border-slate-200 text-slate-600'"
              >
                Yearly
              </button>
            </div>
          </div>

          <!-- Custom Quota Override (Optional) -->
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Custom Quota Override (GB, Optional)</label>
            <input
              type="number"
              v-model.number="upgradeCustomLimitGB"
              placeholder="Leave empty to use plan default"
              class="w-full px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div v-if="upgradeMessage" class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center space-x-2">
          <CheckCircle2 class="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{{ upgradeMessage }}</span>
        </div>

        <div v-if="upgradeError" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
          <AlertTriangle class="w-4 h-4 text-rose-600 shrink-0" />
          <span>{{ upgradeError }}</span>
        </div>

        <div class="pt-2 flex items-center justify-end space-x-2.5">
          <button
            @click="showUpgradeModal = false"
            class="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer"
          >
            Cancel
          </button>
          <button
            @click="submitPlanUpgrade"
            :disabled="isUpgrading"
            class="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-sm flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw v-if="isUpgrading" class="w-3.5 h-3.5 animate-spin" />
            <span>{{ isUpgrading ? 'Applying...' : 'Apply Plan Upgrade' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

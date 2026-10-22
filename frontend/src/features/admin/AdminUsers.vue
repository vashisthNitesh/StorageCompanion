<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from "vue";
import { Search, UserPlus, Loader2, MoreHorizontal, ChevronLeft, ChevronRight } from "lucide-vue-next";
import { apiRequest } from "../../lib/api";
import { useBillingStore } from "../../stores/billing";
import { useToastStore } from "../../stores/toast";
import { formatDate } from "../../lib/format";
import BaseModal from "../../components/BaseModal.vue";
import ConfirmDialog from "../../components/ConfirmDialog.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  date_joined: string;
  plan: {
    code: string;
    name: string;
    status: string;
    billing_interval: string;
    current_period_end: string | null;
    retention_days_remaining: number;
    days_until_expiration: number;
  };
  storage: { percent_used: number; used_formatted: string; limit_formatted: string };
}

const billing = useBillingStore();
const toast = useToastStore();

const users = ref<AdminUser[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const search = ref("");
const plan = ref("");
const status = ref("");
const loading = ref(false);
const error = ref("");
const openMenuFor = ref<string | null>(null);

const pages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams({ search: search.value, plan: plan.value, status: status.value, page: String(page.value), page_size: String(pageSize) });
    const data = await apiRequest<{ total_count: number; results: AdminUser[] }>(`/api/v1/admin/users/?${params}`);
    users.value = data.results;
    total.value = data.total_count;
  } catch (err: any) {
    error.value = err.message || "Couldn't load customers.";
  } finally {
    loading.value = false;
  }
}

let timer: ReturnType<typeof setTimeout> | undefined;
watch([search, plan, status], () => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    page.value = 1;
    void load();
  }, 300);
});
watch(page, load);

function statusBadge(u: AdminUser) {
  if (!u.is_active) return { cls: "badge-red", text: "Suspended" };
  const s = u.plan.status;
  if (s === "active") return { cls: "badge-green", text: "Active" };
  if (s === "extended") return { cls: "badge-blue", text: "Extended" };
  if (["expired", "grace_period", "canceled"].includes(s)) return { cls: "badge-amber", text: `Expired · ${u.plan.retention_days_remaining}d left` };
  if (s === "purged") return { cls: "badge-gray", text: "Data purged" };
  return { cls: "badge-gray", text: "No plan" };
}

// --- Actions -----------------------------------------------------------------
const planDialog = ref<AdminUser | null>(null);
const planForm = ref({ code: "", interval: "monthly", customGb: "" as string | number });
const validityDialog = ref<AdminUser | null>(null);
const validityForm = ref({ action: "extend" as "extend" | "reduce" | "set_date", days: 30, date: "" });
const createOpen = ref(false);
const createForm = ref({ email: "", full_name: "", password: "", role: "customer", plan_code: "none" });
const purgeTarget = ref<AdminUser | null>(null);
const busy = ref(false);
const dialogError = ref("");

function openPlan(u: AdminUser) {
  planDialog.value = u;
  planForm.value = { code: u.plan.code !== "none" ? u.plan.code : billing.plans[0]?.code || "", interval: u.plan.billing_interval || "monthly", customGb: "" };
  dialogError.value = "";
}
function openValidity(u: AdminUser) {
  validityDialog.value = u;
  validityForm.value = { action: "extend", days: 30, date: u.plan.current_period_end ? u.plan.current_period_end.slice(0, 10) : "" };
  dialogError.value = "";
}

async function submit(fn: () => Promise<{ message?: string }>, close: () => void) {
  busy.value = true;
  dialogError.value = "";
  try {
    const res = await fn();
    toast.success(res.message || "Saved.");
    close();
    await load();
  } catch (err: any) {
    dialogError.value = err.message || "Something went wrong.";
  } finally {
    busy.value = false;
  }
}

const savePlan = () =>
  submit(
    () =>
      apiRequest(`/api/v1/admin/users/${planDialog.value!.id}/upgrade-plan/`, {
        method: "POST",
        body: JSON.stringify({ plan_code: planForm.value.code, billing_interval: planForm.value.interval, custom_limit_gb: planForm.value.customGb || null }),
      }),
    () => (planDialog.value = null)
  );

const saveValidity = () =>
  submit(() => {
    const f = validityForm.value;
    const body = f.action === "set_date" ? { action: f.action, expiry_date: f.date } : { action: f.action, days: f.days };
    return apiRequest(`/api/v1/admin/users/${validityDialog.value!.id}/validity/`, { method: "POST", body: JSON.stringify(body) });
  }, () => (validityDialog.value = null));

const createUser = () =>
  submit(
    () => apiRequest("/api/v1/admin/users/create/", { method: "POST", body: JSON.stringify(createForm.value) }),
    () => (createOpen.value = false)
  );

async function toggleActive(u: AdminUser) {
  openMenuFor.value = null;
  try {
    const res = await apiRequest<{ is_active: boolean }>(`/api/v1/admin/users/${u.id}/toggle-status/`, { method: "POST" });
    u.is_active = res.is_active;
    toast.success(res.is_active ? `${u.email} reactivated.` : `${u.email} suspended and signed out.`);
  } catch (err: any) {
    toast.error(err.message || "Couldn't change account status.");
  }
}

async function purge() {
  const res = await apiRequest<{ message?: string }>(`/api/v1/admin/users/${purgeTarget.value!.id}/purge-data/`, { method: "POST" });
  toast.success(res.message || "Data purged.");
  await load();
}

function closeMenu(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest("[data-row-menu]")) openMenuFor.value = null;
}

onMounted(() => {
  void load();
  if (!billing.plans.length) void billing.fetchPlans();
  document.addEventListener("click", closeMenu);
});
onUnmounted(() => document.removeEventListener("click", closeMenu));
</script>

<template>
  <div>
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
      <div class="relative flex-1">
        <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input v-model="search" type="search" class="input pl-9" placeholder="Search by name or email" aria-label="Search customers" />
      </div>
      <div class="flex flex-wrap gap-2">
        <select v-model="plan" class="input h-10 w-auto" aria-label="Filter by plan">
          <option value="">All plans</option>
          <option v-for="p in billing.plans" :key="p.code" :value="p.code">{{ p.name }}</option>
        </select>
        <select v-model="status" class="input h-10 w-auto" aria-label="Filter by status">
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="extended">Extended</option>
          <option value="expired">Expired</option>
          <option value="suspended">Suspended</option>
          <option value="purged">Purged</option>
        </select>
        <button class="btn-primary h-10" @click="createOpen = true; dialogError = ''"><UserPlus class="h-4 w-4" /> Add user</button>
      </div>
    </div>

    <div v-if="error" class="alert-error mt-4">{{ error }} <button class="ml-2 underline" @click="load">Retry</button></div>

    <div class="mt-4 card overflow-x-auto">
      <table class="w-full min-w-[720px] text-left text-sm">
        <thead class="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th class="px-4 py-2.5 font-medium">Customer</th>
            <th class="px-4 py-2.5 font-medium">Plan</th>
            <th class="px-4 py-2.5 font-medium">Status</th>
            <th class="px-4 py-2.5 font-medium">Storage</th>
            <th class="px-4 py-2.5"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-if="loading && !users.length"><td colspan="5" class="px-4 py-10 text-center text-slate-500"><Loader2 class="mx-auto h-5 w-5 animate-spin" /></td></tr>
          <tr v-else-if="!users.length"><td colspan="5" class="px-4 py-10 text-center text-slate-500">No customers match.</td></tr>
          <tr v-for="u in users" :key="u.id" :class="{ 'opacity-60': loading }">
            <td class="px-4 py-3">
              <p class="font-medium text-slate-900">{{ u.full_name }}</p>
              <p class="text-xs text-slate-500">{{ u.email }} · joined {{ formatDate(u.date_joined) }}</p>
            </td>
            <td class="px-4 py-3">
              <p class="text-slate-800">{{ u.plan.name }}</p>
              <p v-if="u.plan.current_period_end" class="text-xs text-slate-500">until {{ formatDate(u.plan.current_period_end) }}</p>
            </td>
            <td class="px-4 py-3"><span :class="statusBadge(u).cls">{{ statusBadge(u).text }}</span></td>
            <td class="px-4 py-3">
              <p class="text-xs text-slate-600">{{ u.storage.used_formatted }} / {{ u.storage.limit_formatted }}</p>
              <div class="mt-1 h-1.5 w-28 rounded-full bg-slate-100"><div class="h-1.5 rounded-full bg-brand-600" :style="{ width: `${Math.min(100, u.storage.percent_used)}%` }"></div></div>
            </td>
            <td class="relative px-4 py-3 text-right" data-row-menu>
              <button class="icon-btn" :aria-label="`Actions for ${u.email}`" @click="openMenuFor = openMenuFor === u.id ? null : u.id">
                <MoreHorizontal class="h-4 w-4" />
              </button>
              <div v-if="openMenuFor === u.id" class="absolute right-4 top-12 z-20 w-52 rounded-xl border border-slate-200 bg-white p-1.5 text-left shadow-pop">
                <button class="block w-full rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="openPlan(u); openMenuFor = null">Change plan</button>
                <button v-if="u.plan.code !== 'none'" class="block w-full rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="openValidity(u); openMenuFor = null">Adjust validity</button>
                <button class="block w-full rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100" @click="toggleActive(u)">{{ u.is_active ? "Suspend account" : "Reactivate account" }}</button>
                <button
                  v-if="['expired', 'grace_period', 'canceled'].includes(u.plan.status)"
                  class="block w-full rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50"
                  @click="purgeTarget = u; openMenuFor = null"
                >
                  Purge stored files
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="pages > 1" class="mt-4 flex items-center justify-between text-sm text-slate-600">
      <span>{{ total }} customers</span>
      <div class="flex items-center gap-2">
        <button class="icon-btn" :disabled="page <= 1" aria-label="Previous page" @click="page--"><ChevronLeft class="h-4 w-4" /></button>
        <span>Page {{ page }} of {{ pages }}</span>
        <button class="icon-btn" :disabled="page >= pages" aria-label="Next page" @click="page++"><ChevronRight class="h-4 w-4" /></button>
      </div>
    </div>

    <!-- Change plan -->
    <BaseModal :open="!!planDialog" title="Change plan" @close="planDialog = null">
      <form id="plan-form" class="space-y-4" @submit.prevent="savePlan">
        <p class="text-sm text-slate-600">{{ planDialog?.email }}</p>
        <div>
          <label class="label" for="plan-code">Plan</label>
          <select id="plan-code" v-model="planForm.code" class="input">
            <option v-for="p in billing.plans" :key="p.code" :value="p.code">{{ p.name }}</option>
          </select>
        </div>
        <div>
          <label class="label" for="plan-interval">Period</label>
          <select id="plan-interval" v-model="planForm.interval" class="input">
            <option value="monthly">30 days</option>
            <option value="yearly">365 days</option>
          </select>
        </div>
        <div>
          <label class="label" for="plan-custom">Custom storage limit (GB) <span class="font-normal text-slate-400">optional</span></label>
          <input id="plan-custom" v-model="planForm.customGb" type="number" min="1" class="input" placeholder="Use the plan's limit" />
        </div>
        <div v-if="dialogError" class="alert-error">{{ dialogError }}</div>
      </form>
      <template #footer>
        <button class="btn-secondary" @click="planDialog = null">Cancel</button>
        <button type="submit" form="plan-form" class="btn-primary" :disabled="busy"><Loader2 v-if="busy" class="h-4 w-4 animate-spin" /> Save</button>
      </template>
    </BaseModal>

    <!-- Validity -->
    <BaseModal :open="!!validityDialog" title="Adjust validity" @close="validityDialog = null">
      <form id="validity-form" class="space-y-4" @submit.prevent="saveValidity">
        <p class="text-sm text-slate-600">
          {{ validityDialog?.email }} · currently until {{ formatDate(validityDialog?.plan.current_period_end) }}
        </p>
        <div class="grid grid-cols-3 gap-1 rounded-lg bg-slate-100 p-1 text-sm">
          <button
            v-for="opt in ([['extend', 'Extend'], ['reduce', 'Shorten'], ['set_date', 'Set date']] as const)"
            :key="opt[0]"
            type="button"
            class="rounded-md py-1.5 font-medium"
            :class="validityForm.action === opt[0] ? 'bg-white shadow-sm text-slate-900' : 'text-slate-600'"
            @click="validityForm.action = opt[0]"
          >
            {{ opt[1] }}
          </button>
        </div>
        <div v-if="validityForm.action !== 'set_date'">
          <label class="label" for="validity-days">Days</label>
          <input id="validity-days" v-model.number="validityForm.days" type="number" min="1" max="3650" class="input" required />
        </div>
        <div v-else>
          <label class="label" for="validity-date">New end date</label>
          <input id="validity-date" v-model="validityForm.date" type="date" class="input" required />
          <p class="hint">A date in the past expires the plan and starts the 90-day retention period.</p>
        </div>
        <div v-if="dialogError" class="alert-error">{{ dialogError }}</div>
      </form>
      <template #footer>
        <button class="btn-secondary" @click="validityDialog = null">Cancel</button>
        <button type="submit" form="validity-form" class="btn-primary" :disabled="busy"><Loader2 v-if="busy" class="h-4 w-4 animate-spin" /> Save</button>
      </template>
    </BaseModal>

    <!-- Create user -->
    <BaseModal :open="createOpen" title="Add user" @close="createOpen = false">
      <form id="create-form" class="space-y-4" @submit.prevent="createUser">
        <div>
          <label class="label" for="new-email">Email</label>
          <input id="new-email" v-model="createForm.email" type="email" class="input" required />
        </div>
        <div>
          <label class="label" for="new-name">Full name</label>
          <input id="new-name" v-model="createForm.full_name" class="input" />
        </div>
        <div>
          <label class="label" for="new-password">Temporary password</label>
          <UiPasswordInput id="new-password" v-model="createForm.password" autocomplete="new-password" :minlength="10" required />
          <p class="hint">Share it securely. The person's encrypted vault is created the first time they sign in.</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label" for="new-role">Role</label>
            <select id="new-role" v-model="createForm.role" class="input">
              <option value="customer">Customer</option>
              <option value="admin">Administrator</option>
            </select>
          </div>
          <div v-if="createForm.role === 'customer'">
            <label class="label" for="new-plan">Plan</label>
            <select id="new-plan" v-model="createForm.plan_code" class="input">
              <option value="none">No plan</option>
              <option v-for="p in billing.plans" :key="p.code" :value="p.code">{{ p.name }}</option>
            </select>
          </div>
        </div>
        <div v-if="dialogError" class="alert-error">{{ dialogError }}</div>
      </form>
      <template #footer>
        <button class="btn-secondary" @click="createOpen = false">Cancel</button>
        <button type="submit" form="create-form" class="btn-primary" :disabled="busy"><Loader2 v-if="busy" class="h-4 w-4 animate-spin" /> Create user</button>
      </template>
    </BaseModal>

    <ConfirmDialog
      :open="!!purgeTarget"
      title="Purge this customer's files?"
      :message="`All files stored by ${purgeTarget?.email} will be permanently deleted from storage. This can't be undone.`"
      confirm-label="Purge files"
      danger
      :action="purge"
      @close="purgeTarget = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from "vue";
import { UserPlus, MoreHorizontal, CreditCard, CalendarClock, UserX, UserCheck, Trash2, CloudOff, SearchX } from "lucide-vue-next";
import { apiRequest } from "../../lib/api";
import { useBillingStore } from "../../stores/billing";
import { toast } from "../../lib/toast";
import { confirmDialog } from "../../lib/confirm";
import { reportError } from "../../lib/reportError";
import { normalizeApiError } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { rules, useForm } from "../../composables/useForm";
import UiButton from "../../components/ui/UiButton.vue";
import UiSearchInput from "../../components/ui/UiSearchInput.vue";
import UiSelect from "../../components/ui/UiSelect.vue";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiProgress from "../../components/ui/UiProgress.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import UiEmptyState from "../../components/ui/UiEmptyState.vue";
import UiPagination from "../../components/ui/UiPagination.vue";
import UiDropdownMenu from "../../components/ui/UiDropdownMenu.vue";
import UiModal from "../../components/ui/UiModal.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import type { MenuEntry } from "../../components/ui/menuTypes";

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

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "extended", label: "Extended" },
  { value: "expired", label: "Expired" },
  { value: "suspended", label: "Suspended" },
  { value: "purged", label: "Purged" },
];
const planOptions = computed(() => billing.plans.map((p) => ({ value: p.code, label: p.name })));
const planFilterOptions = computed(() => [{ value: "", label: "All plans" }, ...planOptions.value]);

const users = ref<AdminUser[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const search = ref("");
const plan = ref("");
const status = ref("");
const loading = ref(false);
const loaded = ref(false);
const error = ref<unknown>(null);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const params = new URLSearchParams({ search: search.value, plan: plan.value, status: status.value, page: String(page.value), page_size: String(pageSize) });
    const data = await apiRequest<{ total_count: number; results: AdminUser[] }>(`/api/v1/admin/users/?${params}`);
    users.value = data.results;
    total.value = data.total_count;
    loaded.value = true;
  } catch (err) {
    error.value = err;
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

const isLapsed = (u: AdminUser) => ["expired", "grace_period", "canceled"].includes(u.plan.status);
function statusBadge(u: AdminUser): { tone: "success" | "info" | "warning" | "danger" | "neutral"; text: string } {
  if (!u.is_active) return { tone: "danger", text: "Suspended" };
  const s = u.plan.status;
  if (s === "active") return { tone: "success", text: "Active" };
  if (s === "extended") return { tone: "info", text: "Extended" };
  if (isLapsed(u)) return { tone: "warning", text: `Expired · ${u.plan.retention_days_remaining}d left` };
  if (s === "purged") return { tone: "neutral", text: "Data purged" };
  return { tone: "neutral", text: "No plan" };
}
const storageTone = (pct: number) => (pct >= 100 ? "danger" : pct >= 90 ? "warning" : "primary");

// --- Change plan ----------------------------------------------------------------
const planTarget = ref<AdminUser | null>(null);
const planOpen = ref(false);
const positiveWhole = (v: string) => (v === "" || v == null || (Number.isInteger(Number(v)) && Number(v) >= 1) ? null : "Enter a whole number of GB, 1 or more.");
const planForm = useForm(
  { plan_code: "", billing_interval: "monthly" as "monthly" | "yearly", custom_limit_gb: "" },
  { plan_code: [rules.required("Choose a plan.")], custom_limit_gb: [positiveWhole] }
);
function openPlan(u: AdminUser) {
  planTarget.value = u;
  planForm.reset({
    plan_code: u.plan.code !== "none" ? u.plan.code : billing.plans[0]?.code || "",
    billing_interval: u.plan.billing_interval === "yearly" ? "yearly" : "monthly",
  });
  planOpen.value = true;
}
async function savePlan() {
  const u = planTarget.value;
  if (!u) return;
  let message = "";
  const ok = await planForm.submit(async (v) => {
    const res = await apiRequest<{ message?: string }>(`/api/v1/admin/users/${u.id}/upgrade-plan/`, {
      method: "POST",
      body: JSON.stringify({ ...v, custom_limit_gb: v.custom_limit_gb === "" ? null : Number(v.custom_limit_gb) }),
    });
    message = res.message || `Plan updated for ${u.email}`;
  });
  if (ok) {
    planOpen.value = false;
    toast.success(message);
    void load();
  }
}

// --- Validity -------------------------------------------------------------------
type ValidityAction = "extend" | "reduce" | "set_date";
const VALIDITY_OPTIONS: { value: ValidityAction; label: string }[] = [
  { value: "extend", label: "Extend" },
  { value: "reduce", label: "Shorten" },
  { value: "set_date", label: "Set date" },
];
const validityTarget = ref<AdminUser | null>(null);
const validityOpen = ref(false);
const validityForm = useForm(
  { action: "extend" as ValidityAction, days: "30", expiry_date: "" },
  {
    days: [(v, all) => (all.action === "set_date" ? null : Number.isInteger(Number(v)) && Number(v) >= 1 && Number(v) <= 3650 ? null : "Enter a number of days from 1 to 3650.")],
    expiry_date: [(v, all) => (all.action === "set_date" && !v ? "Choose the new end date." : null)],
  }
);
function openValidity(u: AdminUser) {
  validityTarget.value = u;
  validityForm.reset({ expiry_date: u.plan.current_period_end ? u.plan.current_period_end.slice(0, 10) : "" });
  validityOpen.value = true;
}
async function saveValidity() {
  const u = validityTarget.value;
  if (!u) return;
  let message = "";
  const ok = await validityForm.submit(async (v) => {
    const body = v.action === "set_date" ? { action: v.action, expiry_date: v.expiry_date } : { action: v.action, days: Number(v.days) };
    const res = await apiRequest<{ message?: string }>(`/api/v1/admin/users/${u.id}/validity/`, { method: "POST", body: JSON.stringify(body) });
    message = res.message || `Validity updated for ${u.email}`;
  });
  if (ok) {
    validityOpen.value = false;
    toast.success(message);
    void load();
  }
}

// --- Create user ----------------------------------------------------------------
const createOpen = ref(false);
const ROLE_OPTIONS = [
  { value: "customer", label: "Customer" },
  { value: "admin", label: "Administrator" },
];
const createPlanOptions = computed(() => [{ value: "none", label: "No plan" }, ...planOptions.value]);
const createForm = useForm(
  { email: "", full_name: "", password: "", role: "customer", plan_code: "none" },
  {
    email: [rules.required("Enter an email address."), rules.email()],
    full_name: [rules.maxLength(120)],
    password: [rules.required("Set a temporary password."), rules.minLength(10)],
  }
);
function openCreate() {
  createForm.reset();
  createOpen.value = true;
}
async function createUser() {
  let email = "";
  const ok = await createForm.submit(async (v) => {
    email = v.email.trim();
    await apiRequest("/api/v1/admin/users/create/", { method: "POST", body: JSON.stringify({ ...v, email }) });
  });
  if (ok) {
    createOpen.value = false;
    toast.success(`Account created for ${email}`);
    void load();
  }
}

// --- Row actions ------------------------------------------------------------------
async function setActive(u: AdminUser, active: boolean) {
  const run = async () => {
    const res = await apiRequest<{ is_active: boolean }>(`/api/v1/admin/users/${u.id}/toggle-status/`, { method: "POST" });
    u.is_active = res.is_active;
  };
  if (!active) {
    const ok = await confirmDialog({
      title: `Suspend ${u.email}?`,
      body: "They'll be signed out everywhere and won't be able to sign in until you reactivate the account. Their files are kept.",
      confirmLabel: "Suspend account",
      danger: true,
      action: run,
    });
    if (ok) toast.success(`${u.email} suspended and signed out`);
    return;
  }
  try {
    await run();
    toast.success(`${u.email} reactivated`);
  } catch (err) {
    reportError(err);
  }
}

async function purge(u: AdminUser) {
  const ok = await confirmDialog({
    title: "Purge this customer's files?",
    body: `All files stored by ${u.email} will be permanently deleted from storage. This can't be undone.`,
    confirmLabel: "Purge files",
    danger: true,
    typeToConfirm: "purge",
    action: async () => {
      await apiRequest(`/api/v1/admin/users/${u.id}/purge-data/`, { method: "POST" });
    },
  });
  if (ok) {
    toast.success(`Files purged for ${u.email}`);
    void load();
  }
}

function menuFor(u: AdminUser): MenuEntry[] {
  const items: MenuEntry[] = [{ label: "Change plan", icon: CreditCard, onSelect: () => openPlan(u) }];
  if (u.plan.code !== "none") items.push({ label: "Adjust validity", icon: CalendarClock, onSelect: () => openValidity(u) });
  items.push(
    { separator: true },
    u.is_active
      ? { label: "Suspend account", icon: UserX, onSelect: () => void setActive(u, false) }
      : { label: "Reactivate account", icon: UserCheck, onSelect: () => void setActive(u, true) }
  );
  if (isLapsed(u)) items.push({ label: "Purge stored files", icon: Trash2, danger: true, onSelect: () => void purge(u) });
  return items;
}

onMounted(() => {
  void load();
  void billing.ensurePlans();
});
</script>

<template>
  <div>
    <div class="flex flex-col gap-2 lg:flex-row lg:items-center">
      <UiSearchInput v-model="search" class="flex-1" placeholder="Search by name or email" aria-label="Search customers" />
      <div class="flex flex-wrap gap-2">
        <UiSelect v-model="plan" :options="planFilterOptions" :block="false" aria-label="Filter by plan" />
        <UiSelect v-model="status" :options="STATUS_OPTIONS" :block="false" aria-label="Filter by status" />
        <UiButton variant="primary" :icon="UserPlus" @click="openCreate">Add user</UiButton>
      </div>
    </div>

    <div v-if="error && !users.length" class="mt-4 rounded-lg border border-line bg-surface">
      <UiEmptyState :icon="CloudOff" tone="danger" title="Couldn't load customers" :description="normalizeApiError(error).message">
        <UiButton @click="load">Try again</UiButton>
      </UiEmptyState>
    </div>
    <div v-else class="mt-4 overflow-x-auto rounded-lg border border-line bg-surface">
      <table class="w-full min-w-[720px] text-left text-base">
        <thead class="border-b border-line bg-surface-sunken text-sm text-fg-muted">
          <tr>
            <th scope="col" class="px-4 py-2.5 font-medium">Customer</th>
            <th scope="col" class="px-4 py-2.5 font-medium">Plan</th>
            <th scope="col" class="px-4 py-2.5 font-medium">Status</th>
            <th scope="col" class="px-4 py-2.5 font-medium">Storage</th>
            <th scope="col" class="w-14 px-4 py-2.5"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line" :aria-busy="loading">
          <template v-if="loading && !loaded">
            <tr v-for="i in 6" :key="i">
              <td class="px-4 py-3"><UiSkeleton class="h-3.5 w-36" /><UiSkeleton class="mt-2 h-3 w-48" /></td>
              <td class="px-4 py-3"><UiSkeleton class="h-3.5 w-24" /></td>
              <td class="px-4 py-3"><UiSkeleton class="h-5 w-16 rounded-full" /></td>
              <td class="px-4 py-3"><UiSkeleton class="h-3 w-28" /></td>
              <td />
            </tr>
          </template>
          <tr v-else-if="!users.length">
            <td colspan="5"><UiEmptyState :icon="SearchX" tone="neutral" title="No customers match" description="Try a different search or filter." /></td>
          </tr>
          <tr v-for="u in users" :key="u.id" class="transition-opacity hover:bg-canvas-subtle" :class="{ 'opacity-60': loading }">
            <td class="px-4 py-3">
              <p class="font-medium text-fg">{{ u.full_name || u.email }}</p>
              <p class="text-sm text-fg-subtle">{{ u.email }} · joined {{ formatDate(u.date_joined) }}</p>
            </td>
            <td class="px-4 py-3">
              <p class="text-fg">{{ u.plan.name }}</p>
              <p v-if="u.plan.current_period_end" class="tabular text-sm text-fg-subtle">until {{ formatDate(u.plan.current_period_end) }}</p>
            </td>
            <td class="px-4 py-3"><UiBadge :tone="statusBadge(u).tone" dot>{{ statusBadge(u).text }}</UiBadge></td>
            <td class="px-4 py-3">
              <p class="tabular text-sm text-fg-muted">{{ u.storage.used_formatted }} / {{ u.storage.limit_formatted }}</p>
              <UiProgress class="mt-1 w-28" size="sm" :value="u.storage.percent_used" :tone="storageTone(u.storage.percent_used)" :label="`Storage used by ${u.email}`" />
            </td>
            <td class="px-4 py-3 text-right">
              <UiDropdownMenu :items="menuFor(u)" align="end">
                <UiButton variant="ghost" size="sm" icon-only :icon="MoreHorizontal" :aria-label="`Actions for ${u.email}`" />
              </UiDropdownMenu>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <UiPagination v-model="page" class="mt-4" :total="total" :page-size="pageSize" label="Customer pages" />

    <UiModal v-model:open="planOpen" title="Change plan" :description="planTarget?.email" size="sm" :dismissible="!planForm.submitting.value">
      <form :ref="(el) => (planForm.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="savePlan">
        <UiFormField label="Plan" :error="planForm.errors.plan_code">
          <UiSelect v-model="planForm.values.plan_code" :options="planOptions" placeholder="Choose a plan" />
        </UiFormField>
        <UiFormField label="Period">
          <UiSegmented
            v-model="planForm.values.billing_interval"
            :options="[{ value: 'monthly', label: '30 days' }, { value: 'yearly', label: '365 days' }]"
            label="Period"
          />
        </UiFormField>
        <UiFormField label="Custom storage limit (GB)" optional hint="Leave empty to use the plan's limit." :error="planForm.errors.custom_limit_gb">
          <UiInput v-model="planForm.values.custom_limit_gb" inputmode="numeric" @blur="planForm.blur('custom_limit_gb')" />
        </UiFormField>
        <UiAlert v-if="planForm.formError.value">{{ planForm.formError.value }}</UiAlert>
        <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
      </form>
      <template #footer>
        <UiButton :disabled="planForm.submitting.value" @click="planOpen = false">Cancel</UiButton>
        <UiButton variant="primary" :loading="planForm.submitting.value" @click="savePlan">Save plan</UiButton>
      </template>
    </UiModal>

    <UiModal
      v-model:open="validityOpen"
      title="Adjust validity"
      :description="validityTarget ? `${validityTarget.email} · currently until ${formatDate(validityTarget.plan.current_period_end)}` : undefined"
      size="sm"
      :dismissible="!validityForm.submitting.value"
    >
      <form :ref="(el) => (validityForm.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="saveValidity">
        <UiSegmented v-model="validityForm.values.action" :options="VALIDITY_OPTIONS" label="Change" />
        <UiFormField v-if="validityForm.values.action !== 'set_date'" label="Days" :error="validityForm.errors.days">
          <UiInput v-model="validityForm.values.days" inputmode="numeric" @blur="validityForm.blur('days')" />
        </UiFormField>
        <UiFormField
          v-else
          label="New end date"
          hint="A date in the past expires the plan and starts the 90-day retention period."
          :error="validityForm.errors.expiry_date"
        >
          <UiInput v-model="validityForm.values.expiry_date" type="date" @blur="validityForm.blur('expiry_date')" />
        </UiFormField>
        <UiAlert v-if="validityForm.formError.value">{{ validityForm.formError.value }}</UiAlert>
        <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
      </form>
      <template #footer>
        <UiButton :disabled="validityForm.submitting.value" @click="validityOpen = false">Cancel</UiButton>
        <UiButton variant="primary" :loading="validityForm.submitting.value" @click="saveValidity">Save</UiButton>
      </template>
    </UiModal>

    <UiModal v-model:open="createOpen" title="Add user" :dismissible="!createForm.submitting.value">
      <form :ref="(el) => (createForm.formEl.value = el as HTMLFormElement)" novalidate class="space-y-4" @submit.prevent="createUser">
        <UiFormField label="Email" :error="createForm.errors.email">
          <UiInput v-model="createForm.values.email" type="email" autocomplete="off" @blur="createForm.blur('email')" />
        </UiFormField>
        <UiFormField label="Full name" optional :error="createForm.errors.full_name">
          <UiInput v-model="createForm.values.full_name" autocomplete="off" @blur="createForm.blur('full_name')" />
        </UiFormField>
        <UiFormField
          label="Temporary password"
          hint="Share it securely. Their encrypted vault is created the first time they sign in."
          :error="createForm.errors.password"
        >
          <UiPasswordInput v-model="createForm.values.password" autocomplete="new-password" @blur="createForm.blur('password')" />
        </UiFormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <UiFormField label="Role">
            <UiSelect v-model="createForm.values.role" :options="ROLE_OPTIONS" />
          </UiFormField>
          <UiFormField v-if="createForm.values.role === 'customer'" label="Plan">
            <UiSelect v-model="createForm.values.plan_code" :options="createPlanOptions" />
          </UiFormField>
        </div>
        <UiAlert v-if="createForm.formError.value">{{ createForm.formError.value }}</UiAlert>
        <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
      </form>
      <template #footer>
        <UiButton :disabled="createForm.submitting.value" @click="createOpen = false">Cancel</UiButton>
        <UiButton variant="primary" :loading="createForm.submitting.value" @click="createUser">Create user</UiButton>
      </template>
    </UiModal>
  </div>
</template>

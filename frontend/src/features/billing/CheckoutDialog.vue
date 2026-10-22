<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { CheckCircle2, XCircle, ShieldCheck } from "lucide-vue-next";
import UiModal from "../../components/ui/UiModal.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiSelect from "../../components/ui/UiSelect.vue";
import UiSegmented from "../../components/ui/UiSegmented.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import { useAuthStore } from "../../stores/auth";
import { useBillingStore, PaymentCancelled, PaymentFailed, type Plan } from "../../stores/billing";
import { GST_STATES } from "../../lib/gstStates";
import { formatDate, formatMoney } from "../../lib/format";
import { normalizeApiError } from "../../lib/errors";
import { actionFor, gstBreakdown, priceFor, storageLabel, yearlySavingsPercent } from "./planCatalog";

const open = defineModel<boolean>("open", { default: false });
const interval = defineModel<"monthly" | "yearly">("interval", { default: "yearly" });
const props = defineProps<{ plan: Plan | null }>();

const router = useRouter();
const authStore = useAuthStore();
const billing = useBillingStore();

type Step = "summary" | "success" | "failed";
const step = ref<Step>("summary");
const busy = ref(false);
const error = ref("");
const stateError = ref("");
const orderRef = ref("");
const state = ref(readState());

function readState() {
  try {
    return localStorage.getItem("sc_billing_state") || "";
  } catch {
    return "";
  }
}

watch(open, (o) => {
  if (o) {
    step.value = "summary";
    error.value = "";
    stateError.value = "";
  }
});

const sub = computed(() => authStore.user?.subscription);
const currentCode = computed(() => (sub.value?.has_active_subscription ? sub.value.plan_code : null));
const action = computed(() => (props.plan ? actionFor(props.plan, currentCode.value, billing.plans) : "choose"));
const total = computed(() => (props.plan ? priceFor(props.plan, interval.value) : 0));
const breakdown = computed(() => gstBreakdown(total.value));
const days = computed(() => (interval.value === "yearly" ? 365 : 30));
const validUntil = computed(() => {
  const now = Date.now();
  const end = sub.value?.current_period_end ? new Date(sub.value.current_period_end).getTime() : 0;
  const start = action.value === "extend" && end > now ? end : now;
  return new Date(start + days.value * 86_400_000).toISOString();
});
const savings = computed(() => yearlySavingsPercent(billing.plans));
const stateOptions = GST_STATES.map((s) => ({ value: s.code, label: s.name }));

async function pay() {
  if (!props.plan) return;
  if (!state.value) {
    stateError.value = "Select your state so we can add the right GST to your invoice.";
    return;
  }
  try {
    localStorage.setItem("sc_billing_state", state.value);
  } catch {}
  busy.value = true;
  error.value = "";
  try {
    await billing.checkout(props.plan.code, interval.value, state.value);
    step.value = "success";
  } catch (err) {
    if (err instanceof PaymentCancelled) {
      error.value = "Payment cancelled. You haven't been charged.";
    } else if (err instanceof PaymentFailed) {
      orderRef.value = err.orderId;
      step.value = "failed";
    } else if (err instanceof Error && err.message === "razorpay_unavailable") {
      error.value = "The payment window couldn't load. Turn off ad blockers for this site and try again.";
    } else {
      const n = normalizeApiError(err);
      error.value = n.status === 503 ? "Online payments are unavailable right now. Please try again later." : n.message;
    }
  } finally {
    busy.value = false;
  }
}

function startUploading() {
  open.value = false;
  router.push("/app/files");
}
</script>

<template>
  <UiModal v-model:open="open" :title="step === 'summary' ? 'Review your plan' : step === 'success' ? 'Payment complete' : 'Payment didn’t go through'" size="md" :dismissible="!busy">
    <template v-if="plan && step === 'summary'">
      <form novalidate class="space-y-5" @submit.prevent="pay">
        <div class="flex items-start justify-between gap-4 rounded-lg border border-line bg-canvas-subtle p-4">
          <div>
            <p class="font-semibold text-fg">{{ plan.name }}</p>
            <p class="text-sm text-fg-muted">{{ storageLabel(plan.storage_bytes) }} · files up to {{ storageLabel(plan.max_file_size) }}</p>
          </div>
          <UiSegmented
            v-model="interval"
            label="Billing period"
            size="sm"
            :options="[
              { value: 'monthly', label: 'Monthly' },
              { value: 'yearly', label: 'Yearly', badge: savings ? `−${savings}%` : undefined },
            ]"
          />
        </div>

        <dl class="tabular space-y-2 text-base">
          <div class="flex justify-between"><dt class="text-fg-muted">Plan price ({{ interval === "yearly" ? "1 year" : "30 days" }})</dt><dd class="text-fg">{{ formatMoney(breakdown.base) }}</dd></div>
          <div class="flex justify-between"><dt class="text-fg-muted">GST (18%)</dt><dd class="text-fg">{{ formatMoney(breakdown.gst) }}</dd></div>
          <div class="flex justify-between border-t border-line pt-2 font-semibold"><dt class="text-fg">Total</dt><dd class="text-fg">{{ formatMoney(breakdown.total) }}</dd></div>
          <div class="flex justify-between text-sm"><dt class="text-fg-subtle">Valid until</dt><dd class="text-fg-muted">{{ formatDate(validUntil) }}</dd></div>
        </dl>

        <p v-if="action === 'extend'" class="text-sm text-fg-muted">This adds {{ days }} days to your current plan.</p>
        <p v-else-if="action === 'upgrade' || action === 'switch'" class="text-sm text-fg-muted">
          Your new plan starts today. Time left on your current plan isn't carried over.
        </p>

        <UiFormField label="Your state" hint="Used to calculate CGST/SGST or IGST on your invoice." :error="stateError" required>
          <UiSelect v-model="state" :options="stateOptions" placeholder="Search for your state" @update:model-value="stateError = ''" />
        </UiFormField>

        <UiAlert v-if="!authStore.paymentsEnabled" tone="warning">Online payments are unavailable right now. Please try again later.</UiAlert>
        <UiAlert v-if="error">{{ error }}</UiAlert>
        <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
      </form>
    </template>

    <div v-else-if="step === 'success'" class="py-4 text-center">
      <CheckCircle2 :size="40" :stroke-width="1.5" class="mx-auto text-success" aria-hidden="true" />
      <p class="mt-3 text-md font-semibold text-fg">You're on {{ plan?.name }}</p>
      <p class="mt-1 text-base text-fg-muted">Valid until {{ formatDate(validUntil) }}. Your invoice is in Plan & billing.</p>
    </div>

    <div v-else class="py-4 text-center">
      <XCircle :size="40" :stroke-width="1.5" class="mx-auto text-danger" aria-hidden="true" />
      <p class="mt-3 text-base text-fg-muted">The payment was declined, so your plan hasn't changed. Try again, or use a different payment method.</p>
      <p v-if="orderRef" class="mt-3 text-sm text-fg-subtle">Reference: <span class="font-mono">{{ orderRef }}</span> — keep this if you contact us.</p>
    </div>

    <template #footer>
      <template v-if="step === 'summary'">
        <p class="mr-auto hidden items-center gap-1.5 text-sm text-fg-subtle sm:flex"><ShieldCheck :size="14" /> Secure payment by Razorpay</p>
        <UiButton :disabled="busy" @click="open = false">Cancel</UiButton>
        <UiButton variant="primary" :loading="busy" :disabled="!authStore.paymentsEnabled" @click="pay">Pay {{ formatMoney(total) }}</UiButton>
      </template>
      <template v-else-if="step === 'success'">
        <UiButton @click="open = false">Close</UiButton>
        <UiButton variant="primary" @click="startUploading">Start uploading</UiButton>
      </template>
      <template v-else>
        <UiButton @click="open = false">Close</UiButton>
        <UiButton variant="primary" @click="step = 'summary'">Try again</UiButton>
      </template>
    </template>
  </UiModal>
</template>

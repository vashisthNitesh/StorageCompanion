<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { PinInputRoot, PinInputInput } from "reka-ui";
import { ShieldCheck, ShieldOff, Copy, Download, Check } from "lucide-vue-next";
import UiCard from "../../components/ui/UiCard.vue";
import UiBadge from "../../components/ui/UiBadge.vue";
import UiButton from "../../components/ui/UiButton.vue";
import UiModal from "../../components/ui/UiModal.vue";
import UiCheckbox from "../../components/ui/UiCheckbox.vue";
import UiAlert from "../../components/ui/UiAlert.vue";
import UiFormField from "../../components/ui/UiFormField.vue";
import UiPasswordInput from "../../components/ui/UiPasswordInput.vue";
import UiInput from "../../components/ui/UiInput.vue";
import UiSkeleton from "../../components/ui/UiSkeleton.vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest } from "../../lib/api";
import { normalizeApiError } from "../../lib/errors";
import { toast } from "../../lib/toast";

const authStore = useAuthStore();
const enabled = computed(() => !!authStore.user?.mfa_enabled);
const isGoogleOnly = computed(() => !!authStore.user?.has_google && !authStore.user?.wrapped_master_key);

// --- Setup (stepped) -------------------------------------------------------------
const setupOpen = ref(false);
const step = ref<1 | 2 | 3>(1);
const enrol = ref<{ qr: string; secret: string; codes: string[] } | null>(null);
const enrolError = ref("");
const pin = ref<(number | undefined)[]>([]);
const verifyError = ref("");
const verifying = ref(false);
const saved = ref(false);
const copied = ref<"secret" | "codes" | null>(null);

async function startSetup() {
  setupOpen.value = true;
  step.value = 1;
  enrol.value = null;
  enrolError.value = "";
  pin.value = [];
  saved.value = false;
  try {
    const data = await apiRequest<{ qr_code: string; secret: string; backup_codes: string[] }>("/api/v1/auth/mfa/enroll", { method: "POST" });
    enrol.value = { qr: data.qr_code, secret: data.secret, codes: data.backup_codes };
  } catch (err) {
    enrolError.value = normalizeApiError(err).message;
  }
}

// Move focus into the code boxes when step 2 opens.
watch(step, async (s) => {
  if (s !== 2) return;
  await nextTick();
  document.querySelector<HTMLInputElement>("[data-pin-root] input")?.focus();
});

async function verify() {
  const code = pin.value.map((d) => d ?? "").join("");
  if (code.length !== 6) {
    verifyError.value = "Enter all 6 digits.";
    return;
  }
  verifying.value = true;
  verifyError.value = "";
  try {
    await apiRequest("/api/v1/auth/mfa/verify", { method: "POST", body: JSON.stringify({ code }) });
    await authStore.fetchProfile();
    step.value = 3;
  } catch (err) {
    const n = normalizeApiError(err);
    verifyError.value = n.kind === "validation" ? "That code didn't work. Check the time on your phone and try the newest code." : n.message;
    pin.value = [];
  } finally {
    verifying.value = false;
  }
}

async function copy(what: "secret" | "codes") {
  if (!enrol.value) return;
  try {
    await navigator.clipboard.writeText(what === "secret" ? enrol.value.secret : enrol.value.codes.join("\n"));
    copied.value = what;
    setTimeout(() => (copied.value = null), 2000);
  } catch {
    toast.error("Couldn't copy. Select the text and copy it manually.");
  }
}

function downloadCodes() {
  if (!enrol.value) return;
  const text = [
    "SmartSpace recovery codes",
    `Account: ${authStore.user?.email}`,
    "Each code works once if you can't use your authenticator app.",
    "",
    ...enrol.value.codes,
  ].join("\n");
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "smartspace-recovery-codes.txt";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function finish() {
  setupOpen.value = false;
  enrol.value = null;
  toast.success("Two-step verification is on.");
}

// --- Turn off ------------------------------------------------------------------------
const disableOpen = ref(false);
const disableSecret = ref("");
const disableError = ref("");
const disabling = ref(false);
async function disable() {
  if (!disableSecret.value) {
    disableError.value = isGoogleOnly.value ? "Enter a code from your authenticator app." : "Enter your password.";
    return;
  }
  disabling.value = true;
  disableError.value = "";
  try {
    const body = isGoogleOnly.value ? { code: disableSecret.value } : { password: disableSecret.value };
    await apiRequest("/api/v1/auth/mfa/disable", { method: "POST", body: JSON.stringify(body) });
    await authStore.fetchProfile();
    disableOpen.value = false;
    disableSecret.value = "";
    toast.info("Two-step verification is off.");
  } catch (err) {
    const n = normalizeApiError(err);
    disableError.value = n.kind === "validation" ? (isGoogleOnly.value ? "That code didn't work." : "That password isn't right.") : n.message;
  } finally {
    disabling.value = false;
  }
}
defineExpose({ startSetup });
</script>

<template>
  <UiCard
    id="two-step"
    class="scroll-mt-6"
    :icon="enabled ? ShieldCheck : ShieldOff"
    :icon-tone="enabled ? 'success' : 'warning'"
    title="Two-step verification"
    description="Ask for a code from an authenticator app (Google Authenticator, 1Password, Authy) every time you sign in."
  >
    <template #actions>
      <UiBadge :tone="enabled ? 'success' : 'neutral'" :icon="enabled ? ShieldCheck : ShieldOff">{{ enabled ? "On" : "Off" }}</UiBadge>
    </template>
    <div class="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between" :class="enabled ? 'border-success/25 bg-success-soft/50' : 'border-warning/30 bg-warning-soft/50'">
      <p class="text-base" :class="enabled ? 'text-success' : 'text-warning'">
        {{ enabled ? "On. You'll enter a 6-digit code after signing in." : "Off. A stolen password is enough to get into your account." }}
      </p>
      <UiButton v-if="enabled" class="shrink-0" @click="disableOpen = true; disableError = ''; disableSecret = ''">Turn off</UiButton>
      <UiButton v-else variant="primary" class="shrink-0" @click="startSetup">Turn on</UiButton>
    </div>
  </UiCard>

  <UiModal
    v-model:open="setupOpen"
    :title="step === 1 ? 'Scan the QR code' : step === 2 ? 'Enter the 6-digit code' : 'Save your recovery codes'"
    :description="`Step ${step} of 3`"
    size="md"
    :dismissible="step !== 3"
  >
    <!-- Step indicator -->
    <ol class="mb-5 flex gap-2" aria-hidden="true">
      <li v-for="i in 3" :key="i" class="h-1 flex-1 rounded-full" :class="i <= step ? 'bg-primary' : 'bg-line'" />
    </ol>

    <template v-if="step === 1">
      <UiAlert v-if="enrolError">{{ enrolError }}</UiAlert>
      <div v-else class="flex flex-col items-center gap-5 sm:flex-row sm:items-start">
        <UiSkeleton v-if="!enrol" class="h-44 w-44 shrink-0" />
        <img v-else :src="enrol.qr" alt="QR code to add SmartSpace to your authenticator app" class="h-44 w-44 shrink-0 rounded-lg bg-white p-2 ring-1 ring-line" />
        <div class="min-w-0 space-y-3 text-base text-fg-muted">
          <p>Open your authenticator app and scan this code.</p>
          <p>Can't scan it? Enter this key instead:</p>
          <div class="flex items-center gap-2">
            <code class="min-w-0 flex-1 break-all rounded border border-line bg-canvas-subtle px-2 py-1.5 font-mono text-sm text-fg">{{ enrol?.secret ?? "…" }}</code>
            <UiButton size="sm" icon-only :icon="copied === 'secret' ? Check : Copy" :aria-label="copied === 'secret' ? 'Copied' : 'Copy key'" :disabled="!enrol" @click="copy('secret')" />
          </div>
        </div>
      </div>
    </template>

    <form v-else-if="step === 2" novalidate class="space-y-4" @submit.prevent="verify">
      <p class="text-base text-fg-muted">Enter the code your app shows for SmartSpace.</p>
      <PinInputRoot
        v-model="pin"
        otp
        type="number"
        placeholder="·"
        class="flex gap-2"
        data-pin-root
        aria-label="6-digit code"
        @complete="verify"
      >
        <PinInputInput
          v-for="(_, i) in 6"
          :key="i"
          :index="i"
          class="h-12 w-11 rounded border border-line-strong bg-surface text-center font-mono text-lg text-fg shadow-xs outline-none focus:border-primary focus:ring-4 focus:ring-primary/15"
          :class="verifyError ? 'border-danger' : ''"
          :aria-label="`Digit ${i + 1}`"
          :autofocus="i === 0"
        />
      </PinInputRoot>
      <p v-if="verifyError" class="text-sm text-danger" role="alert">{{ verifyError }}</p>
      <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
    </form>

    <div v-else class="space-y-4">
      <p class="text-base text-fg-muted">If you lose your phone, each code lets you sign in once. Keep them somewhere safe, like a password manager.</p>
      <div class="grid grid-cols-2 gap-x-6 gap-y-1.5 rounded-lg border border-line bg-canvas-subtle p-4 font-mono text-base text-fg">
        <span v-for="c in enrol?.codes" :key="c">{{ c }}</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiButton size="sm" :icon="copied === 'codes' ? Check : Copy" @click="copy('codes')">{{ copied === "codes" ? "Copied" : "Copy" }}</UiButton>
        <UiButton size="sm" :icon="Download" @click="downloadCodes">Download .txt</UiButton>
      </div>
      <UiCheckbox v-model="saved" label="I've saved these codes somewhere safe" />
    </div>

    <template #footer>
      <template v-if="step === 1">
        <UiButton @click="setupOpen = false">Cancel</UiButton>
        <UiButton variant="primary" :disabled="!enrol" @click="step = 2">Next</UiButton>
      </template>
      <template v-else-if="step === 2">
        <UiButton @click="step = 1">Back</UiButton>
        <UiButton variant="primary" :loading="verifying" @click="verify">Verify</UiButton>
      </template>
      <UiButton v-else variant="primary" :disabled="!saved" tooltip="Confirm you've saved the codes first" @click="finish">Finish</UiButton>
    </template>
  </UiModal>

  <UiModal v-model:open="disableOpen" title="Turn off two-step verification?" size="sm" :dismissible="!disabling">
    <form novalidate class="space-y-4" @submit.prevent="disable">
      <p class="text-base text-fg-muted">Your account will only be protected by {{ isGoogleOnly ? "your Google account" : "your password" }}.</p>
      <UiFormField v-if="isGoogleOnly" label="Code from your authenticator app" :error="disableError">
        <UiInput v-model="disableSecret" inputmode="numeric" autocomplete="one-time-code" />
      </UiFormField>
      <UiFormField v-else label="Password" :error="disableError">
        <UiPasswordInput v-model="disableSecret" autocomplete="current-password" />
      </UiFormField>
      <button type="submit" class="hidden" tabindex="-1" aria-hidden="true" />
    </form>
    <template #footer>
      <UiButton :disabled="disabling" @click="disableOpen = false">Cancel</UiButton>
      <UiButton variant="danger" :loading="disabling" @click="disable">Turn off</UiButton>
    </template>
  </UiModal>
</template>

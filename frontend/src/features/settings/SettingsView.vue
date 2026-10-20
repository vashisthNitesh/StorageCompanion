<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Laptop, Smartphone, ShieldCheck, ShieldOff, Loader2, KeyRound, History, Copy, Check } from "lucide-vue-next";
import { useAuthStore } from "../../stores/auth";
import { useToastStore } from "../../stores/toast";
import { apiRequest } from "../../lib/api";
import { deriveKEK, DEFAULT_KDF_PARAMS, generateRandomSalt } from "../../lib/crypto/kdf";
import { wrapKey } from "../../lib/crypto/keys";
import { formatDateTime, formatRelative } from "../../lib/format";
import PasswordInput from "../auth/PasswordInput.vue";
import BaseModal from "../../components/BaseModal.vue";

const authStore = useAuthStore();
const toast = useToastStore();
const user = computed(() => authStore.user);
const isGoogleOnly = computed(() => !!user.value?.has_google && !user.value?.wrapped_master_key && !authStore.isMasterAdmin);

// --- Password -----------------------------------------------------------------
const pw = ref({ current: "", next: "", confirm: "" });
const pwBusy = ref(false);
const pwError = ref("");

async function changePassword() {
  pwError.value = "";
  if (pw.value.next.length < 10) return (pwError.value = "Use at least 10 characters.");
  if (pw.value.next !== pw.value.confirm) return (pwError.value = "The new passwords don't match.");
  if (user.value?.wrapped_master_key && !authStore.masterKey) return (pwError.value = "Unlock your vault first (open My files).");

  pwBusy.value = true;
  try {
    const payload: Record<string, unknown> = { current_password: pw.value.current, new_password: pw.value.next };
    if (authStore.masterKey && user.value?.wrapped_master_key) {
      // Re-wrap the vault key with the new password; files don't need to be re-encrypted.
      const salt = generateRandomSalt(16);
      const kek = await deriveKEK(pw.value.next, salt, DEFAULT_KDF_PARAMS);
      payload.new_wrapped_master_key = await wrapKey(kek, authStore.masterKey);
      payload.new_kdf_salt = salt;
      payload.new_kdf_params = DEFAULT_KDF_PARAMS;
    }
    const res = await apiRequest<{ message: string }>("/api/v1/auth/password", { method: "POST", body: JSON.stringify(payload) });
    pw.value = { current: "", next: "", confirm: "" };
    toast.success(res.message);
    await Promise.all([authStore.fetchProfile(), loadSessions()]);
  } catch (err: any) {
    pwError.value = err.message || "Couldn't change your password.";
  } finally {
    pwBusy.value = false;
  }
}

// --- Two-step verification ----------------------------------------------------
const mfa = ref<null | { qr: string; secret: string; backupCodes: string[] }>(null);
const mfaCode = ref("");
const mfaBusy = ref(false);
const mfaError = ref("");
const disableOpen = ref(false);
const disableSecret = ref("");
const copied = ref(false);

async function startMfa() {
  mfaBusy.value = true;
  mfaError.value = "";
  try {
    const data = await apiRequest<{ qr_code: string; secret: string; backup_codes: string[] }>("/api/v1/auth/mfa/enroll", { method: "POST" });
    mfa.value = { qr: data.qr_code, secret: data.secret, backupCodes: data.backup_codes };
    mfaCode.value = "";
  } catch (err: any) {
    toast.error(err.message || "Couldn't start setup.");
  } finally {
    mfaBusy.value = false;
  }
}

async function confirmMfa() {
  mfaBusy.value = true;
  mfaError.value = "";
  try {
    await apiRequest("/api/v1/auth/mfa/verify", { method: "POST", body: JSON.stringify({ code: mfaCode.value }) });
    await authStore.fetchProfile();
    mfa.value = null;
    toast.success("Two-step verification is on.");
  } catch (err: any) {
    mfaError.value = err.message || "That code didn't work.";
  } finally {
    mfaBusy.value = false;
  }
}

async function disableMfa() {
  mfaBusy.value = true;
  mfaError.value = "";
  try {
    const body = isGoogleOnly.value ? { code: disableSecret.value } : { password: disableSecret.value };
    await apiRequest("/api/v1/auth/mfa/disable", { method: "POST", body: JSON.stringify(body) });
    await authStore.fetchProfile();
    disableOpen.value = false;
    disableSecret.value = "";
    toast.info("Two-step verification is off.");
  } catch (err: any) {
    mfaError.value = err.message || "Couldn't turn it off.";
  } finally {
    mfaBusy.value = false;
  }
}

async function copyCodes() {
  if (!mfa.value) return;
  await navigator.clipboard.writeText(mfa.value.backupCodes.join("\n"));
  copied.value = true;
  setTimeout(() => (copied.value = false), 2000);
}

// --- Sessions & activity ------------------------------------------------------
interface SessionRow {
  id: string;
  device_label: string;
  ip_address: string | null;
  last_seen: string;
  created_at: string;
  is_current: boolean;
}
const sessions = ref<SessionRow[]>([]);
const sessionsLoading = ref(true);
const revoking = ref<string | null>(null);
const activity = ref<{ id: string; action: string; ip: string | null; created_at: string }[]>([]);

async function loadSessions() {
  try {
    sessions.value = await apiRequest<SessionRow[]>("/api/v1/auth/sessions");
  } catch {
    sessions.value = [];
  } finally {
    sessionsLoading.value = false;
  }
}

async function loadActivity() {
  try {
    const data = await apiRequest<any>("/api/v1/audit-logs/");
    activity.value = (Array.isArray(data) ? data : data.results || []).slice(0, 15);
  } catch {
    activity.value = [];
  }
}

async function revoke(s: SessionRow) {
  revoking.value = s.id;
  try {
    await apiRequest(`/api/v1/auth/sessions/${s.id}`, { method: "DELETE" });
    sessions.value = sessions.value.filter((x) => x.id !== s.id);
    toast.success(`Signed out ${s.device_label}.`);
  } catch (err: any) {
    toast.error(err.message || "Couldn't sign out that device.");
  } finally {
    revoking.value = null;
  }
}

async function revokeOthers() {
  for (const s of sessions.value.filter((x) => !x.is_current)) await revoke(s);
}

const ACTIONS: Record<string, string> = {
  "auth.login": "Signed in",
  "auth.google_login": "Signed in with Google",
  "auth.logout": "Signed out",
  "user.registered": "Account created",
  "user.registered_google": "Account created with Google",
  "user.password_changed": "Password changed",
  "mfa.enabled": "Two-step verification turned on",
  "mfa.disabled": "Two-step verification turned off",
  "session.revoked": "Signed out a device",
  "file.uploaded": "Uploaded a file",
  "file.downloaded": "Downloaded a file",
  "node.trashed": "Moved an item to trash",
  "node.restored": "Restored an item",
  "node.deleted_permanently": "Deleted an item forever",
  "node.updated": "Renamed or moved an item",
  "folder.created": "Created a folder",
  "subscription.activated": "Plan activated",
  "subscription.canceled": "Plan set not to renew",
  "vault.created": "Vault created",
};
const actionLabel = (a: string) => ACTIONS[a] || a.replace(/[._]/g, " ");
const isMobile = (label: string) => /iOS|Android/.test(label);

onMounted(() => {
  void loadSessions();
  void loadActivity();
});
</script>

<template>
  <div class="max-w-3xl">
    <h1 class="page-title">Security</h1>
    <p class="page-subtitle">Signed in as {{ user?.email }}</p>

    <!-- Password -->
    <section class="mt-6 card card-body">
      <div class="flex items-center gap-2">
        <KeyRound class="h-5 w-5 text-slate-400" />
        <h2 class="section-title">Password</h2>
      </div>
      <p v-if="isGoogleOnly" class="mt-2 text-sm text-slate-600">
        You sign in with Google, so there's no SmartSpace password to change. Manage your Google account's security at
        <a href="https://myaccount.google.com/security" target="_blank" rel="noopener" class="text-brand-600 hover:underline">myaccount.google.com</a>.
      </p>
      <form v-else class="mt-4 grid gap-4 sm:grid-cols-2" @submit.prevent="changePassword">
        <div class="sm:col-span-2">
          <label for="pw-current" class="label">Current password</label>
          <PasswordInput id="pw-current" v-model="pw.current" autocomplete="current-password" required />
        </div>
        <div>
          <label for="pw-new" class="label">New password</label>
          <PasswordInput id="pw-new" v-model="pw.next" autocomplete="new-password" :minlength="10" required />
        </div>
        <div>
          <label for="pw-confirm" class="label">Confirm new password</label>
          <PasswordInput id="pw-confirm" v-model="pw.confirm" autocomplete="new-password" required />
        </div>
        <div v-if="pwError" class="alert-error sm:col-span-2">{{ pwError }}</div>
        <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-xs text-slate-500">Changing it signs out your other devices. Your files stay encrypted and don't need re-uploading.</p>
          <button type="submit" class="btn-primary shrink-0" :disabled="pwBusy">
            <Loader2 v-if="pwBusy" class="h-4 w-4 animate-spin" /> Update password
          </button>
        </div>
      </form>
    </section>

    <!-- 2FA -->
    <section class="mt-6 card card-body">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div class="flex items-start gap-2">
          <ShieldCheck v-if="user?.mfa_enabled" class="mt-0.5 h-5 w-5 text-emerald-600" />
          <ShieldOff v-else class="mt-0.5 h-5 w-5 text-slate-400" />
          <div>
            <h2 class="section-title">Two-step verification</h2>
            <p class="mt-1 text-sm text-slate-600">
              {{ user?.mfa_enabled ? "On. You'll enter a code from your authenticator app when signing in." : "Add a code from an authenticator app (Google Authenticator, 1Password, Authy…) to every sign-in." }}
            </p>
          </div>
        </div>
        <button v-if="user?.mfa_enabled" class="btn-secondary shrink-0" @click="disableOpen = true; mfaError = ''">Turn off</button>
        <button v-else-if="!mfa" class="btn-primary shrink-0" :disabled="mfaBusy" @click="startMfa">
          <Loader2 v-if="mfaBusy" class="h-4 w-4 animate-spin" /> Set up
        </button>
      </div>

      <div v-if="mfa" class="mt-5 grid gap-6 border-t border-slate-100 pt-5 md:grid-cols-[auto_1fr]">
        <div>
          <img :src="mfa.qr" alt="QR code for your authenticator app" class="h-40 w-40 rounded-lg ring-1 ring-slate-200" />
          <p class="mt-2 max-w-[10rem] break-all font-mono text-[11px] text-slate-500">{{ mfa.secret }}</p>
        </div>
        <div class="space-y-4">
          <ol class="list-decimal space-y-1 pl-4 text-sm text-slate-600">
            <li>Scan the QR code with your authenticator app (or enter the key below it).</li>
            <li>Save the backup codes somewhere safe. Each works once if you lose your phone.</li>
            <li>Enter the 6-digit code the app shows.</li>
          </ol>
          <div class="rounded-lg bg-slate-50 p-3">
            <div class="flex items-center justify-between">
              <p class="text-xs font-medium uppercase tracking-wide text-slate-500">Backup codes</p>
              <button class="btn-ghost btn-sm" @click="copyCodes">
                <Check v-if="copied" class="h-4 w-4 text-emerald-600" /><Copy v-else class="h-4 w-4" />{{ copied ? "Copied" : "Copy" }}
              </button>
            </div>
            <div class="mt-2 grid grid-cols-2 gap-1 font-mono text-sm text-slate-800 sm:grid-cols-5">
              <span v-for="c in mfa.backupCodes" :key="c">{{ c }}</span>
            </div>
          </div>
          <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="confirmMfa">
            <input v-model="mfaCode" class="input font-mono tracking-widest sm:w-40" inputmode="numeric" autocomplete="one-time-code" placeholder="123456" maxlength="6" required />
            <button type="submit" class="btn-primary" :disabled="mfaBusy">
              <Loader2 v-if="mfaBusy" class="h-4 w-4 animate-spin" /> Verify and turn on
            </button>
            <button type="button" class="btn-ghost" @click="mfa = null">Cancel</button>
          </form>
          <p v-if="mfaError" class="text-sm text-rose-600">{{ mfaError }}</p>
        </div>
      </div>
    </section>

    <!-- Sessions -->
    <section class="mt-6 card">
      <div class="flex items-center justify-between gap-3 px-5 pt-5 sm:px-6">
        <div>
          <h2 class="section-title">Where you're signed in</h2>
          <p class="mt-1 text-sm text-slate-600">Signing out a device takes effect immediately.</p>
        </div>
        <button v-if="sessions.some((s) => !s.is_current)" class="btn-secondary btn-sm shrink-0" @click="revokeOthers">Sign out all others</button>
      </div>
      <div v-if="sessionsLoading" class="m-5 h-12 animate-pulse rounded-lg bg-slate-100"></div>
      <ul v-else class="mt-4 divide-y divide-slate-100 border-t border-slate-100">
        <li v-for="s in sessions" :key="s.id" class="flex items-center gap-3 px-5 py-3 sm:px-6">
          <Smartphone v-if="isMobile(s.device_label)" class="h-5 w-5 shrink-0 text-slate-400" />
          <Laptop v-else class="h-5 w-5 shrink-0 text-slate-400" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-slate-900">
              {{ s.device_label }} <span v-if="s.is_current" class="badge-green ml-1">This device</span>
            </p>
            <p class="text-xs text-slate-500">{{ s.ip_address || "Unknown IP" }} · active {{ formatRelative(s.last_seen) }}</p>
          </div>
          <button v-if="!s.is_current" class="btn-ghost btn-sm" :disabled="revoking === s.id" @click="revoke(s)">
            <Loader2 v-if="revoking === s.id" class="h-4 w-4 animate-spin" /> Sign out
          </button>
        </li>
      </ul>
    </section>

    <!-- Activity -->
    <section class="mt-6 card">
      <div class="flex items-center gap-2 px-5 pt-5 sm:px-6">
        <History class="h-5 w-5 text-slate-400" />
        <h2 class="section-title">Recent activity</h2>
      </div>
      <p v-if="!activity.length" class="px-5 py-5 text-sm text-slate-500 sm:px-6">No activity yet.</p>
      <ul v-else class="mt-4 divide-y divide-slate-100 border-t border-slate-100">
        <li v-for="a in activity" :key="a.id" class="flex items-center justify-between gap-3 px-5 py-2.5 text-sm sm:px-6">
          <span class="text-slate-800">{{ actionLabel(a.action) }}</span>
          <span class="shrink-0 text-xs text-slate-500" :title="formatDateTime(a.created_at)">{{ formatRelative(a.created_at) }}</span>
        </li>
      </ul>
    </section>

    <BaseModal :open="disableOpen" title="Turn off two-step verification?" size="sm" @close="disableOpen = false">
      <form id="disable-mfa" class="space-y-3" @submit.prevent="disableMfa">
        <p class="text-sm text-slate-600">
          {{ isGoogleOnly ? "Enter a current code from your authenticator app to confirm." : "Enter your password to confirm." }}
        </p>
        <input v-if="isGoogleOnly" v-model="disableSecret" class="input font-mono" inputmode="numeric" placeholder="123456" required />
        <PasswordInput v-else id="disable-mfa-password" v-model="disableSecret" autocomplete="current-password" required />
        <p v-if="mfaError" class="text-sm text-rose-600">{{ mfaError }}</p>
      </form>
      <template #footer>
        <button class="btn-secondary" @click="disableOpen = false">Cancel</button>
        <button type="submit" form="disable-mfa" class="btn-danger" :disabled="mfaBusy">
          <Loader2 v-if="mfaBusy" class="h-4 w-4 animate-spin" /> Turn off
        </button>
      </template>
    </BaseModal>
  </div>
</template>

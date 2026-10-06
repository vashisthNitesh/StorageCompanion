<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest } from "../../lib/api";
import { deriveKEK, DEFAULT_KDF_PARAMS, generateRandomSalt } from "../../lib/crypto/kdf";
import { wrapKey, generateMasterKey } from "../../lib/crypto/keys";
import {
  Shield,
  Key,
  Smartphone,
  History,
  Lock,
  CheckCircle2,
  AlertCircle,
  QrCode,
  Trash2,
} from "lucide-vue-next";

const authStore = useAuthStore();

// Password Change
const currentPassword = ref("");
const newPassword = ref("");
const confirmNewPassword = ref("");
const passwordMessage = ref("");
const passwordError = ref("");
const isChangingPassword = ref(false);

// MFA
const mfaStep = ref<"initial" | "enrolling">("initial");
const mfaQrCode = ref("");
const mfaSecret = ref("");
const mfaVerifyCode = ref("");
const mfaMessage = ref("");
const mfaError = ref("");
const mfaBusy = ref(false);
const mfaBackupCodes = ref<string[]>([]);
const mfaDisablePassword = ref("");
const showMfaDisable = ref(false);

// Sessions
const sessions = ref<any[]>([]);
const auditLogs = ref<any[]>([]);

onMounted(async () => {
  await Promise.all([fetchSessions(), fetchAuditLogs()]);
});

async function fetchSessions() {
  try {
    const data = await apiRequest("/api/v1/auth/sessions");
    sessions.value = Array.isArray(data) ? data : data.results || [];
  } catch {}
}

async function fetchAuditLogs() {
  try {
    const data = await apiRequest("/api/v1/audit-logs/");
    auditLogs.value = Array.isArray(data) ? data : data.results || [];
  } catch {}
}

async function handleChangePassword() {
  passwordMessage.value = "";
  passwordError.value = "";

  // Explicit validation (the form uses novalidate so every problem gets a visible message)
  if (!currentPassword.value || !newPassword.value || !confirmNewPassword.value) {
    passwordError.value = "Please fill in your current password and the new password twice.";
    return;
  }
  if (newPassword.value.length < 10) {
    passwordError.value = "New password must be at least 10 characters.";
    return;
  }
  if (newPassword.value !== confirmNewPassword.value) {
    passwordError.value = "New passwords do not match.";
    return;
  }
  if (newPassword.value === currentPassword.value) {
    passwordError.value = "New password must be different from the current password.";
    return;
  }

  isChangingPassword.value = true;
  try {
    // The vault key is needed to re-wrap it under the new password. Previously a locked vault
    // (new tab, or admin accounts which have no usable vault) failed with "Vault must be
    // unlocked" before the server was even asked. Unlock with the current password instead.
    let masterKey = authStore.masterKey;
    if (!masterKey) {
      try {
        await authStore.unlockVault(currentPassword.value);
        masterKey = authStore.masterKey;
      } catch {
        if (!authStore.isMasterAdmin) {
          throw new Error("Current password is incorrect.");
        }
        // Admin portal accounts store no files; give them a fresh vault key. The server still
        // verifies the current password before accepting the change.
        masterKey = generateMasterKey();
      }
    }
    if (!masterKey) throw new Error("Could not unlock your vault. Please log out and back in.");

    // 1. Derive new KEK with new password and a fresh salt
    const newSalt = generateRandomSalt();
    const newKek = await deriveKEK(newPassword.value, newSalt, DEFAULT_KDF_PARAMS);
    // 2. Re-wrap Master Key with new KEK (does NOT re-encrypt files!)
    const newWrappedMasterKey = await wrapKey(newKek, masterKey);

    await apiRequest("/api/v1/auth/password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword.value,
        new_password: newPassword.value,
        new_wrapped_master_key: newWrappedMasterKey,
        new_kdf_salt: newSalt,
        new_kdf_params: DEFAULT_KDF_PARAMS,
      }),
    });

    await authStore.fetchProfile();
    passwordMessage.value = "Password changed. Your files stay encrypted with the same keys.";
    currentPassword.value = "";
    newPassword.value = "";
    confirmNewPassword.value = "";
  } catch (err: any) {
    passwordError.value = err?.message || "Failed to update password.";
  } finally {
    isChangingPassword.value = false;
  }
}

async function startMfaEnroll() {
  mfaError.value = "";
  mfaMessage.value = "";
  mfaBusy.value = true;
  try {
    const data = await apiRequest<{ qr_code: string; secret: string; backup_codes?: string[] }>(
      "/api/v1/auth/mfa/enroll",
      { method: "POST" }
    );
    if (!data?.qr_code || !data?.secret) throw new Error("The server did not return an authenticator QR code.");
    mfaQrCode.value = data.qr_code;
    mfaSecret.value = data.secret;
    mfaBackupCodes.value = data.backup_codes || [];
    mfaVerifyCode.value = "";
    mfaStep.value = "enrolling";
  } catch (err: any) {
    mfaError.value = err?.message || "Failed to start MFA setup.";
  } finally {
    mfaBusy.value = false;
  }
}

function cancelMfaEnroll() {
  mfaStep.value = "initial";
  mfaQrCode.value = "";
  mfaSecret.value = "";
  mfaBackupCodes.value = [];
  mfaVerifyCode.value = "";
  mfaError.value = "";
}

async function verifyMfa() {
  mfaError.value = "";
  const code = mfaVerifyCode.value.replace(/\s+/g, "");
  if (!/^\d{6}$/.test(code)) {
    mfaError.value = "Enter the 6-digit code from your authenticator app.";
    return;
  }
  mfaBusy.value = true;
  try {
    await apiRequest("/api/v1/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
    mfaMessage.value = "Two-Factor Authentication is now enabled. Keep your backup codes somewhere safe.";
    mfaStep.value = "initial";
    mfaQrCode.value = "";
    mfaSecret.value = "";
    await authStore.fetchProfile();
  } catch (err: any) {
    mfaError.value = err?.message || "Invalid verification code.";
  } finally {
    mfaBusy.value = false;
  }
}

async function disableMfa() {
  mfaError.value = "";
  mfaMessage.value = "";
  if (!mfaDisablePassword.value) {
    mfaError.value = "Enter your password to turn off two-factor authentication.";
    return;
  }
  mfaBusy.value = true;
  try {
    await apiRequest("/api/v1/auth/mfa/disable", {
      method: "POST",
      body: JSON.stringify({ password: mfaDisablePassword.value }),
    });
    mfaDisablePassword.value = "";
    showMfaDisable.value = false;
    mfaBackupCodes.value = [];
    mfaMessage.value = "Two-Factor Authentication has been turned off.";
    await authStore.fetchProfile();
  } catch (err: any) {
    mfaError.value = err?.message || "Could not disable two-factor authentication.";
  } finally {
    mfaBusy.value = false;
  }
}

async function revokeSession(sessionId: string) {
  await apiRequest(`/api/v1/auth/sessions/${sessionId}`, { method: "DELETE" });
  await fetchSessions();
}
</script>

<template>
  <div class="space-y-8 max-w-4xl">
    <div>
      <h1 class="text-xl font-bold text-slate-900">Security & Settings</h1>
      <p class="text-xs text-slate-500">Manage your credentials, 2FA, active sessions, and security audit logs.</p>
    </div>

    <!-- 1. Change Password & Re-wrap Key -->
    <div class="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-4">
      <div class="flex items-center space-x-2 text-slate-900 font-bold text-base">
        <Lock class="w-5 h-5 text-brand-600" />
        <h2>Change Password & Re-wrap Master Key</h2>
      </div>
      <p class="text-xs text-slate-600">
        Re-encrypts your Master Key with a new Argon2id KEK. Your files do not need to be re-uploaded or re-encrypted.
      </p>

      <div v-if="passwordMessage" class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
        {{ passwordMessage }}
      </div>
      <div v-if="passwordError" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
        {{ passwordError }}
      </div>

      <form @submit.prevent="handleChangePassword" novalidate class="space-y-3 max-w-md">
        <input
          type="password"
          v-model="currentPassword"
          required
          placeholder="Current password"
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
        />
        <input
          type="password"
          v-model="newPassword"
          required
          minlength="10"
          placeholder="New password (min 10 chars)"
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
        />
        <input
          type="password"
          v-model="confirmNewPassword"
          required
          minlength="10"
          placeholder="Confirm new password"
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 transition-all"
        />

        <button
          type="submit"
          :disabled="isChangingPassword"
          class="btn-primary px-5 py-2.5 rounded-xl text-white font-semibold text-xs shadow-xs hover:shadow-md transition-all"
        >
          {{ isChangingPassword ? 'Re-wrapping Key...' : 'Update Password' }}
        </button>
      </form>
    </div>

    <!-- 2. Two-Factor Authentication -->
    <div class="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-4">
      <div class="flex items-center space-x-2 text-slate-900 font-bold text-base">
        <Smartphone class="w-5 h-5 text-brand-600" />
        <h2>Two-Factor Authentication (TOTP)</h2>
      </div>
      <p class="text-xs text-slate-600">
        Protect your account with an authenticator app (Google Authenticator, Authy, 1Password).
      </p>

      <div v-if="mfaMessage" class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
        {{ mfaMessage }}
      </div>
      <div v-if="mfaError" class="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
        {{ mfaError }}
      </div>

      <div v-if="mfaBackupCodes.length && authStore.user?.mfa_enabled" class="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-2">
        <p class="font-bold">Backup codes: each one works once if you lose your phone. They won't be shown again.</p>
        <div class="grid grid-cols-2 gap-1 font-mono">
          <span v-for="code in mfaBackupCodes" :key="code">{{ code }}</span>
        </div>
      </div>

      <div v-if="authStore.user?.mfa_enabled" class="space-y-3">
        <div class="flex items-center space-x-2 text-emerald-700 text-xs font-bold">
          <CheckCircle2 class="w-4 h-4 text-emerald-600" />
          <span>Two-Factor Authentication is Active</span>
        </div>
        <button
          v-if="!showMfaDisable"
          type="button"
          @click="showMfaDisable = true"
          class="px-4 py-2 rounded-xl bg-white hover:bg-rose-50 text-rose-700 font-semibold text-xs border border-rose-200 transition-colors"
        >
          Turn off two-factor authentication
        </button>
        <form v-else @submit.prevent="disableMfa" novalidate class="flex flex-wrap gap-2 max-w-md">
          <input
            type="password"
            v-model="mfaDisablePassword"
            placeholder="Current password"
            class="flex-1 min-w-0 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:bg-white focus:outline-none focus:border-brand-500"
          />
          <button type="submit" :disabled="mfaBusy" class="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs disabled:opacity-60">
            {{ mfaBusy ? 'Turning off...' : 'Confirm' }}
          </button>
          <button type="button" @click="showMfaDisable = false; mfaDisablePassword = ''" class="px-3 py-2 rounded-xl text-slate-600 text-xs hover:bg-slate-100">
            Cancel
          </button>
        </form>
      </div>

      <div v-else-if="mfaStep === 'initial'">
        <button
          type="button"
          @click="startMfaEnroll"
          :disabled="mfaBusy"
          class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs border border-slate-200 transition-colors disabled:opacity-60"
        >
          {{ mfaBusy ? 'Preparing QR code...' : 'Enable Authenticator App' }}
        </button>
      </div>

      <!-- Enrollment Step -->
      <div v-else-if="mfaStep === 'enrolling'" class="space-y-4 max-w-sm">
        <p class="text-xs text-slate-600">
          Scan this QR code with Google Authenticator, 1Password, Authy or similar, then enter the 6-digit code to finish.
        </p>
        <div class="p-3 bg-white border border-slate-200 rounded-2xl inline-block shadow-xs">
          <img :src="mfaQrCode" alt="MFA QR Code" class="w-44 h-44" />
        </div>
        <div class="text-xs text-slate-600 break-all">
          Manual code: <code class="text-brand-700 font-mono font-bold">{{ mfaSecret }}</code>
        </div>
        <div class="flex space-x-2">
          <input
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="7"
            v-model="mfaVerifyCode"
            @keyup.enter="verifyMfa"
            placeholder="6-digit code"
            class="flex-1 min-w-0 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-center font-mono text-slate-900 text-sm focus:bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <button
            type="button"
            @click="verifyMfa"
            :disabled="mfaBusy"
            class="btn-primary px-4 py-2 rounded-xl text-white font-semibold text-xs shadow-xs disabled:opacity-60"
          >
            {{ mfaBusy ? 'Verifying...' : 'Verify & Enable' }}
          </button>
        </div>
        <button type="button" @click="cancelMfaEnroll" class="text-xs text-slate-500 hover:text-slate-700 underline">
          Cancel setup
        </button>
      </div>
    </div>

    <!-- 3. Active Sessions -->
    <div class="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-4">
      <div class="flex items-center space-x-2 text-slate-900 font-bold text-base">
        <Shield class="w-5 h-5 text-brand-600" />
        <h2>Active Sessions</h2>
      </div>
      <p class="text-xs text-slate-600">
        Review connected browsers and devices with revocable session tokens.
      </p>

      <div class="divide-y divide-slate-100 rounded-xl bg-slate-50 border border-slate-200 overflow-hidden">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="p-4 flex items-center justify-between text-xs"
        >
          <div>
            <div class="font-bold text-slate-900">{{ s.device_label }}</div>
            <div class="text-[10px] text-slate-500 font-mono mt-0.5">
              IP: {{ s.ip_address || 'Unknown' }} • Last active: {{ new Date(s.last_seen).toLocaleString() }}
            </div>
          </div>
          <button
            v-if="s.is_active"
            @click="revokeSession(s.id)"
            class="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold transition-colors"
          >
            Revoke
          </button>
          <span v-else class="text-slate-400 text-[10px] uppercase font-bold">Revoked</span>
        </div>
      </div>
    </div>

    <!-- 4. Append-Only Audit Log Viewer -->
    <div class="bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-xs space-y-4">
      <div class="flex items-center space-x-2 text-slate-900 font-bold text-base">
        <History class="w-5 h-5 text-brand-600" />
        <h2>Security Audit Logs</h2>
      </div>
      <p class="text-xs text-slate-600">
        Cryptographically tracked append-only log of every security event, upload, download, and credential update.
      </p>

      <div class="rounded-xl border border-slate-200 bg-slate-50 overflow-hidden max-h-72 overflow-y-auto divide-y divide-slate-100 font-mono text-xs">
        <div v-for="log in auditLogs" :key="log.id" class="p-3 flex items-center justify-between">
          <div>
            <span class="text-brand-700 font-bold">{{ log.action }}</span>
            <span class="text-slate-500 ml-2 text-[11px]">{{ log.target_type }}:{{ log.target_id.slice(0, 8) }}</span>
          </div>
          <span class="text-slate-400 text-[10px]">{{ new Date(log.created_at).toLocaleTimeString() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

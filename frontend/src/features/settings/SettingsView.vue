<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import { apiRequest } from "../../lib/api";
import { deriveKEK, DEFAULT_KDF_PARAMS } from "../../lib/crypto/kdf";
import { wrapKey } from "../../lib/crypto/keys";
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

  if (newPassword.value !== confirmNewPassword.value) {
    passwordError.value = "New passwords do not match.";
    return;
  }
  if (!authStore.masterKey) {
    passwordError.value = "Vault must be unlocked to change password.";
    return;
  }

  isChangingPassword.value = true;
  try {
    // 1. Derive new KEK with new password
    const newKek = await deriveKEK(newPassword.value, authStore.user!.kdf_salt, DEFAULT_KDF_PARAMS);
    // 2. Re-wrap Master Key with new KEK (does NOT re-encrypt files!)
    const newWrappedMasterKey = await wrapKey(newKek, authStore.masterKey);

    await apiRequest("/api/v1/auth/password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword.value,
        new_password: newPassword.value,
        new_wrapped_master_key: newWrappedMasterKey,
        new_kdf_salt: authStore.user!.kdf_salt,
        new_kdf_params: DEFAULT_KDF_PARAMS,
      }),
    });

    passwordMessage.value = "Password changed and Master Key re-wrapped successfully!";
    currentPassword.value = "";
    newPassword.value = "";
    confirmNewPassword.value = "";
  } catch (err: any) {
    passwordError.value = err.message || "Failed to update password.";
  } finally {
    isChangingPassword.value = false;
  }
}

async function startMfaEnroll() {
  mfaError.value = "";
  try {
    const data = await apiRequest<{ qr_code: string; secret: string }>("/api/v1/auth/mfa/enroll", {
      method: "POST",
    });
    mfaQrCode.value = data.qr_code;
    mfaSecret.value = data.secret;
    mfaStep.value = "enrolling";
  } catch (err: any) {
    mfaError.value = err.message || "Failed to start MFA setup.";
  }
}

async function verifyMfa() {
  mfaError.value = "";
  try {
    await apiRequest("/api/v1/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ code: mfaVerifyCode.value }),
    });
    mfaMessage.value = "Two-Factor Authentication is now enabled!";
    mfaStep.value = "initial";
    await authStore.fetchProfile();
  } catch (err: any) {
    mfaError.value = err.message || "Invalid verification code.";
  }
}

async function revokeSession(sessionId: string) {
  await apiRequest(`/api/v1/auth/sessions/${sessionId}`, { method: "DELETE" });
  await fetchSessions();
}
</script>

<template>
  <div class="space-y-10 max-w-4xl">
    <div>
      <h1 class="text-xl font-bold text-white">Security & Settings</h1>
      <p class="text-xs text-slate-400">Manage your credentials, 2FA, active sessions, and security audit logs.</p>
    </div>

    <!-- 1. Change Password & Re-wrap Key -->
    <div class="glass-panel p-6 rounded-3xl border border-slate-800 space-y-4">
      <div class="flex items-center space-x-2 text-white font-bold text-base">
        <Lock class="w-5 h-5 text-brand-400" />
        <h2>Change Password & Re-wrap Master Key</h2>
      </div>
      <p class="text-xs text-slate-400">
        Re-encrypts your Master Key with a new Argon2id KEK. Your files do not need to be re-uploaded or re-encrypted.
      </p>

      <div v-if="passwordMessage" class="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs">
        {{ passwordMessage }}
      </div>
      <div v-if="passwordError" class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
        {{ passwordError }}
      </div>

      <form @submit.prevent="handleChangePassword" class="space-y-3 max-w-md">
        <input
          type="password"
          v-model="currentPassword"
          required
          placeholder="Current password"
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-brand-500"
        />
        <input
          type="password"
          v-model="newPassword"
          required
          minlength="10"
          placeholder="New password (min 10 chars)"
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-brand-500"
        />
        <input
          type="password"
          v-model="confirmNewPassword"
          required
          minlength="10"
          placeholder="Confirm new password"
          class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-brand-500"
        />

        <button
          type="submit"
          :disabled="isChangingPassword"
          class="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs shadow-md transition-colors"
        >
          {{ isChangingPassword ? 'Re-wrapping Key...' : 'Update Password' }}
        </button>
      </form>
    </div>

    <!-- 2. Two-Factor Authentication -->
    <div class="glass-panel p-6 rounded-3xl border border-slate-800 space-y-4">
      <div class="flex items-center space-x-2 text-white font-bold text-base">
        <Smartphone class="w-5 h-5 text-brand-400" />
        <h2>Two-Factor Authentication (TOTP)</h2>
      </div>
      <p class="text-xs text-slate-400">
        Protect your account with an authenticator app (Google Authenticator, Authy, 1Password).
      </p>

      <div v-if="mfaMessage" class="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs">
        {{ mfaMessage }}
      </div>
      <div v-if="mfaError" class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
        {{ mfaError }}
      </div>

      <div v-if="authStore.user?.mfa_enabled" class="flex items-center space-x-2 text-emerald-400 text-xs font-bold">
        <CheckCircle2 class="w-4 h-4" />
        <span>Two-Factor Authentication is Active</span>
      </div>

      <div v-else-if="mfaStep === 'initial'">
        <button
          @click="startMfaEnroll"
          class="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs border border-slate-700 transition-colors"
        >
          Enable Authenticator App
        </button>
      </div>

      <!-- Enrollment Step -->
      <div v-else-if="mfaStep === 'enrolling'" class="space-y-4 max-w-sm">
        <div class="p-3 bg-white rounded-2xl inline-block">
          <img :src="mfaQrCode" alt="MFA QR Code" class="w-44 h-44" />
        </div>
        <div class="text-xs text-slate-300">
          Manual code: <code class="text-brand-400 font-mono">{{ mfaSecret }}</code>
        </div>
        <div class="flex space-x-2">
          <input
            type="text"
            v-model="mfaVerifyCode"
            placeholder="6-digit code"
            class="flex-1 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-center font-mono text-white text-sm focus:outline-none"
          />
          <button
            @click="verifyMfa"
            class="px-4 py-2 rounded-xl bg-brand-600 text-white font-bold text-xs"
          >
            Verify & Enable
          </button>
        </div>
      </div>
    </div>

    <!-- 3. Active Sessions -->
    <div class="glass-panel p-6 rounded-3xl border border-slate-800 space-y-4">
      <div class="flex items-center space-x-2 text-white font-bold text-base">
        <Shield class="w-5 h-5 text-brand-400" />
        <h2>Active Sessions</h2>
      </div>
      <p class="text-xs text-slate-400">
        Review connected browsers and devices with revocable session tokens.
      </p>

      <div class="divide-y divide-slate-800/80 rounded-2xl bg-slate-900/40 border border-slate-800 overflow-hidden">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="p-4 flex items-center justify-between text-xs"
        >
          <div>
            <div class="font-bold text-white">{{ s.device_label }}</div>
            <div class="text-[10px] text-slate-400 font-mono mt-0.5">
              IP: {{ s.ip_address || 'Unknown' }} • Last active: {{ new Date(s.last_seen).toLocaleString() }}
            </div>
          </div>
          <button
            v-if="s.is_active"
            @click="revokeSession(s.id)"
            class="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold"
          >
            Revoke
          </button>
          <span v-else class="text-slate-500 text-[10px] uppercase font-bold">Revoked</span>
        </div>
      </div>
    </div>

    <!-- 4. Append-Only Audit Log Viewer -->
    <div class="glass-panel p-6 rounded-3xl border border-slate-800 space-y-4">
      <div class="flex items-center space-x-2 text-white font-bold text-base">
        <History class="w-5 h-5 text-brand-400" />
        <h2>Security Audit Logs</h2>
      </div>
      <p class="text-xs text-slate-400">
        Cryptographically tracked append-only log of every security event, upload, download, and credential update.
      </p>

      <div class="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden max-h-72 overflow-y-auto divide-y divide-slate-800/60 font-mono text-xs">
        <div v-for="log in auditLogs" :key="log.id" class="p-3 flex items-center justify-between">
          <div>
            <span class="text-brand-400 font-bold">{{ log.action }}</span>
            <span class="text-slate-400 ml-2 text-[11px]">{{ log.target_type }}:{{ log.target_id.slice(0, 8) }}</span>
          </div>
          <span class="text-slate-500 text-[10px]">{{ new Date(log.created_at).toLocaleTimeString() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

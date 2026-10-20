import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  apiRequest,
  setAccessToken,
  getAccessToken,
  refreshAccessToken,
  setSessionExpiredHandler,
} from "../lib/api";
import {
  generateRandomSalt,
  deriveKEK,
  DEFAULT_KDF_PARAMS,
  uint8ArrayToBase64,
  base64ToUint8Array,
  hexToUint8Array,
} from "../lib/crypto/kdf";
import { generateMasterKey, generateUserKeypair, wrapKey, unwrapKey } from "../lib/crypto/keys";
import { generateRecoveryPhrase, deriveRecoveryKey } from "../lib/crypto/recovery";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  wrapped_master_key: string;
  kdf_salt: string;
  kdf_params: any;
  public_key: string;
  wrapped_private_key: string;
  recovery_wrapped_master_key: string;
  mfa_enabled: boolean;
  has_google?: boolean;
  created_at?: string;
  subscription?: {
    has_active_subscription: boolean;
    status: string;
    plan_name: string | null;
    plan_code: string | null;
    is_in_grace_period?: boolean;
    retention_days_remaining?: number;
    days_until_expiration?: number;
    can_upload?: boolean;
    current_period_end?: string | null;
    grace_period_ends_at?: string | null;
  };
  quota?: {
    bytes_used: number;
    bytes_limit: number;
    percent_used: number;
  };
}

export type LoginResult = { success: true } | { mfaRequired: true };

const VAULT_KEY_STORAGE_KEY = "sc_vault_mk";

function saveMasterKeyToSession(key: Uint8Array | null) {
  if (typeof window === "undefined" || !window.sessionStorage) return;
  if (key) sessionStorage.setItem(VAULT_KEY_STORAGE_KEY, uint8ArrayToBase64(key));
  else sessionStorage.removeItem(VAULT_KEY_STORAGE_KEY);
}

function loadMasterKeyFromSession(): Uint8Array | null {
  if (typeof window === "undefined" || !window.sessionStorage) return null;
  const stored = sessionStorage.getItem(VAULT_KEY_STORAGE_KEY);
  if (!stored) return null;
  try {
    return base64ToUint8Array(stored);
  } catch {
    sessionStorage.removeItem(VAULT_KEY_STORAGE_KEY);
    return null;
  }
}

/** Generates a fresh vault (master key, sharing keypair, recovery wrap) protected by `password`. */
async function createVaultMaterial(password: string) {
  const recoveryKey = await deriveRecoveryKey(generateRecoveryPhrase());
  const kdfSalt = generateRandomSalt(16);
  const kek = await deriveKEK(password, kdfSalt, DEFAULT_KDF_PARAMS);
  const masterKey = generateMasterKey();
  const keypair = await generateUserKeypair();
  return {
    masterKey,
    payload: {
      wrapped_master_key: await wrapKey(kek, masterKey),
      kdf_salt: kdfSalt,
      kdf_params: DEFAULT_KDF_PARAMS,
      public_key: keypair.publicKeyBase64,
      wrapped_private_key: await wrapKey(masterKey, keypair.privateKeyBytes),
      recovery_wrapped_master_key: await wrapKey(recoveryKey, masterKey),
    },
  };
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<UserProfile | null>(null);
  const masterKey = ref<Uint8Array | null>(null);
  const isLoading = ref(false);
  const isInitialized = ref(false);
  const googleClientId = ref("");
  const paymentsEnabled = ref(false);
  const authConfigLoaded = ref(false);

  const isAuthenticated = computed(() => !!user.value && !!getAccessToken());
  const isVaultUnlocked = computed(() => !!masterKey.value);
  const isMasterAdmin = computed(() => !!user.value?.is_staff || !!user.value?.is_superuser);
  const hasActiveSubscription = computed(
    () => isMasterAdmin.value || !!user.value?.subscription?.has_active_subscription
  );
  const canUpload = computed(() => !isMasterAdmin.value && !!user.value?.subscription?.can_upload);
  /** Password-protected vault (unlocked with the account password) vs. Google-derived vault key. */
  const hasPasswordVault = computed(() => !!user.value?.wrapped_master_key);
  const needsVaultSetup = computed(
    () => !!user.value && !isMasterAdmin.value && !user.value.wrapped_master_key && !user.value.has_google
  );

  function clearSession() {
    user.value = null;
    masterKey.value = null;
    setAccessToken(null);
    saveMasterKeyToSession(null);
  }

  setSessionExpiredHandler(() => {
    if (user.value) {
      clearSession();
      if (typeof window !== "undefined" && window.location.pathname.startsWith("/app")) {
        window.location.assign(`/login?expired=1&redirect=${encodeURIComponent(window.location.pathname)}`);
      }
    }
  });

  function setMasterKey(key: Uint8Array | null) {
    masterKey.value = key;
    saveMasterKeyToSession(key);
  }

  async function register(email: string, password: string, fullName = "") {
    isLoading.value = true;
    try {
      const { masterKey: newMasterKey, payload } = await createVaultMaterial(password);
      const response = await apiRequest<{ user: UserProfile; access_token: string }>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name: fullName, ...payload }),
      });
      setAccessToken(response.access_token);
      user.value = response.user;
      setMasterKey(newMasterKey);
      return { user: response.user };
    } finally {
      isLoading.value = false;
    }
  }

  async function unlockWithPassword(profile: UserProfile, password: string) {
    const kek = await deriveKEK(password, profile.kdf_salt, profile.kdf_params || DEFAULT_KDF_PARAMS);
    setMasterKey(await unwrapKey(kek, profile.wrapped_master_key));
  }

  async function login(email: string, password: string, totpCode?: string): Promise<LoginResult> {
    isLoading.value = true;
    try {
      const response = await apiRequest<{ user: UserProfile; access_token: string; mfa_required?: boolean }>(
        "/api/v1/auth/login",
        { method: "POST", body: JSON.stringify({ email, password, totp_code: totpCode || undefined }) }
      );
      if (response.mfa_required) return { mfaRequired: true };

      setAccessToken(response.access_token);
      user.value = response.user;

      const profile = response.user;
      const isAdmin = profile.is_staff || profile.is_superuser;
      if (profile.wrapped_master_key && profile.kdf_salt) {
        try {
          await unlockWithPassword(profile, password);
        } catch (err) {
          // Admin accounts do not use a vault; customers must be able to decrypt.
          if (!isAdmin) {
            clearSession();
            throw new Error("Your password was accepted but the vault could not be decrypted. Please contact support.");
          }
        }
      } else if (!isAdmin && !profile.has_google) {
        // Account created without a vault (e.g. by an administrator): create it now.
        await setupVault(password);
      }
      return { success: true };
    } finally {
      isLoading.value = false;
    }
  }

  async function setupVault(password: string) {
    const { masterKey: newMasterKey, payload } = await createVaultMaterial(password);
    const res = await apiRequest<{ user: UserProfile }>("/api/v1/auth/vault", {
      method: "POST",
      body: JSON.stringify({ password, ...payload }),
    });
    user.value = res.user;
    setMasterKey(newMasterKey);
  }

  async function fetchAuthConfig() {
    if (authConfigLoaded.value) return;
    try {
      const config = await apiRequest<{ google_client_id: string; payments_enabled: boolean }>("/api/v1/auth/config");
      googleClientId.value = config.google_client_id || "";
      paymentsEnabled.value = !!config.payments_enabled;
      authConfigLoaded.value = true;
    } catch {
      // Leave defaults; the UI shows Google sign-in as unavailable.
    }
  }

  async function loginWithGoogle(credential: string, totpCode?: string): Promise<LoginResult> {
    isLoading.value = true;
    try {
      const response = await apiRequest<{
        user: UserProfile;
        access_token: string;
        oauth_vault_hex?: string | null;
        mfa_required?: boolean;
      }>("/api/v1/auth/google", {
        method: "POST",
        body: JSON.stringify({ credential, totp_code: totpCode || undefined }),
      });
      if (response.mfa_required) return { mfaRequired: true };

      setAccessToken(response.access_token);
      user.value = response.user;
      // Google-created accounts get their vault key from the server. Accounts with a
      // password vault stay locked until the password is entered.
      setMasterKey(response.oauth_vault_hex ? hexToUint8Array(response.oauth_vault_hex) : null);
      return { success: true };
    } finally {
      isLoading.value = false;
    }
  }

  /** Re-opens the vault of a Google-created account (e.g. in a new browser tab). */
  async function restoreGoogleVault(): Promise<boolean> {
    if (masterKey.value || !user.value?.has_google || user.value.wrapped_master_key) return !!masterKey.value;
    try {
      const res = await apiRequest<{ oauth_vault_hex: string }>("/api/v1/auth/vault/google-key");
      setMasterKey(hexToUint8Array(res.oauth_vault_hex));
      return true;
    } catch {
      return false;
    }
  }

  async function unlockVault(password: string) {
    if (!user.value?.wrapped_master_key) throw new Error("This account has no password-protected vault.");
    try {
      await unlockWithPassword(user.value, password);
    } catch {
      throw new Error("That password didn't unlock your vault. Please try again.");
    }
  }

  async function fetchProfile() {
    try {
      user.value = await apiRequest<UserProfile>("/api/v1/auth/me");
    } catch (err: any) {
      if (err?.status === 401) clearSession();
    }
  }

  let initPromise: Promise<boolean> | null = null;

  async function initAuth(): Promise<boolean> {
    if (isInitialized.value) return isAuthenticated.value;
    if (initPromise) return initPromise;

    initPromise = (async () => {
      try {
        if (!masterKey.value) masterKey.value = loadMasterKeyFromSession();

        if (getAccessToken()) {
          try {
            user.value = await apiRequest<UserProfile>("/api/v1/auth/me");
            return true;
          } catch {
            // Access token expired; fall through to the refresh cookie.
          }
        }

        const refreshData = await refreshAccessToken();
        if (refreshData?.access_token) {
          user.value = refreshData.user || (await apiRequest<UserProfile>("/api/v1/auth/me"));
          return true;
        }

        clearSession();
        return false;
      } catch {
        clearSession();
        return false;
      } finally {
        isInitialized.value = true;
        initPromise = null;
      }
    })();

    return initPromise;
  }

  async function logout() {
    try {
      await apiRequest("/api/v1/auth/logout", { method: "POST", timeoutMs: 8000 });
    } catch {
      // Ignore network failures on logout
    } finally {
      clearSession();
    }
  }

  return {
    user,
    masterKey,
    isLoading,
    isInitialized,
    googleClientId,
    paymentsEnabled,
    isAuthenticated,
    isVaultUnlocked,
    isMasterAdmin,
    hasActiveSubscription,
    canUpload,
    hasPasswordVault,
    needsVaultSetup,
    register,
    login,
    loginWithGoogle,
    fetchAuthConfig,
    unlockVault,
    restoreGoogleVault,
    setupVault,
    fetchProfile,
    initAuth,
    logout,
  };
});

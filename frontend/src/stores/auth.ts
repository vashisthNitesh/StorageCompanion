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
import { deriveAuthKey } from "../lib/crypto/authKey";
import { generateRecoveryKey, recoveryProofHash, recoveryWrappingKey } from "../lib/crypto/recoveryKey";
import { toast } from "../lib/toast";
import { COPY } from "../lib/errors";

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
  /** A recovery key exists and the user confirmed saving it. */
  has_recovery_key?: boolean;
  recovery_key_confirmed_at?: string | null;
  /** "auth_key": signs in with a key derived from the password; "password": staff and older accounts. */
  auth_scheme?: "auth_key" | "password";
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

/** The key-encryption key for a password, and the auth key derived from it (sent instead of the password). */
export async function passwordKeys(password: string, saltHex: string, params: unknown = DEFAULT_KDF_PARAMS) {
  const kek = await deriveKEK(password, saltHex, params);
  return { kek, authKey: await deriveAuthKey(kek) };
}

/** A new recovery key for `masterKey`: the text to show once, and what the server stores. */
export async function createRecoveryMaterial(masterKey: Uint8Array) {
  const { secret, display } = generateRecoveryKey();
  return {
    display,
    payload: {
      recovery_wrapped_master_key: await wrapKey(await recoveryWrappingKey(secret), masterKey),
      recovery_auth_hash: await recoveryProofHash(secret),
    },
  };
}

/**
 * Generates a fresh vault (master key, sharing keypair) protected by `password`, plus a recovery
 * key unless `withRecovery` is false. Nothing secret leaves the browser unwrapped.
 */
export async function createVaultMaterial(password: string, { withRecovery = true } = {}) {
  const kdfSalt = generateRandomSalt(16);
  const { kek, authKey } = await passwordKeys(password, kdfSalt, DEFAULT_KDF_PARAMS);
  const masterKey = generateMasterKey();
  const keypair = await generateUserKeypair();
  const recovery = withRecovery ? await createRecoveryMaterial(masterKey) : null;
  return {
    masterKey,
    authKey,
    recoveryKey: recovery?.display ?? null,
    payload: {
      wrapped_master_key: await wrapKey(kek, masterKey),
      kdf_salt: kdfSalt,
      kdf_params: DEFAULT_KDF_PARAMS,
      public_key: keypair.publicKeyBase64,
      wrapped_private_key: await wrapKey(masterKey, keypair.privateKeyBytes),
      ...(recovery?.payload ?? {}),
    },
  };
}

type Prelogin = { scheme: "auth_key" | "password"; kdf_salt: string; kdf_params: unknown };

export const useAuthStore = defineStore("auth", () => {
  const user = ref<UserProfile | null>(null);
  const masterKey = ref<Uint8Array | null>(null);
  const isLoading = ref(false);
  const isInitialized = ref(false);
  const googleClientId = ref("");
  const paymentsEnabled = ref(false);
  const authConfigLoaded = ref(false);
  /** Recovery key made with the vault (sign-up or first vault setup), shown until the user confirms saving it. Memory only. */
  const pendingRecoveryKey = ref<string | null>(null);
  /** Proof of the password from this page's sign-in or unlock, so a recovery key can be made without asking again. Memory only. */
  let recentProof: Record<string, string> | null = null;

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
  /** Password vaults without a saved recovery key are asked to make one. */
  const needsRecoveryKey = computed(
    () => !!user.value && !isMasterAdmin.value && !!user.value.wrapped_master_key && !user.value.has_recovery_key
  );

  function clearSession() {
    user.value = null;
    masterKey.value = null;
    pendingRecoveryKey.value = null;
    recentProof = null;
    setAccessToken(null);
    saveMasterKeyToSession(null);
  }

  setSessionExpiredHandler(async () => {
    if (!user.value) return;
    clearSession();
    const path = window.location.pathname;
    if (!path.startsWith("/app")) return;
    toast.info(COPY.session);
    // Imported lazily: the router module itself depends on this store.
    const { router } = await import("../router");
    router.replace({ name: "login", query: { redirect: path } });
  });

  function setMasterKey(key: Uint8Array | null) {
    masterKey.value = key;
    saveMasterKeyToSession(key);
  }

  async function register(email: string, password: string, fullName = "") {
    isLoading.value = true;
    try {
      const vault = await createVaultMaterial(password);
      const response = await apiRequest<{ user: UserProfile; access_token: string }>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, auth_key: vault.authKey, full_name: fullName, ...vault.payload }),
      });
      setAccessToken(response.access_token);
      user.value = response.user;
      setMasterKey(vault.masterKey);
      recentProof = { auth_key: vault.authKey };
      pendingRecoveryKey.value = vault.recoveryKey;
      return { user: response.user, recoveryKey: vault.recoveryKey };
    } finally {
      isLoading.value = false;
    }
  }

  /** Proof of `password` in the form this account signs in with. */
  async function proofFor(password: string): Promise<Record<string, string>> {
    const u = user.value;
    if (u?.auth_scheme === "auth_key" && u.kdf_salt) {
      return { auth_key: (await passwordKeys(password, u.kdf_salt, u.kdf_params || DEFAULT_KDF_PARAMS)).authKey };
    }
    return { password };
  }

  async function unlockWithPassword(profile: UserProfile, password: string) {
    const { kek, authKey } = await passwordKeys(password, profile.kdf_salt, profile.kdf_params || DEFAULT_KDF_PARAMS);
    setMasterKey(await unwrapKey(kek, profile.wrapped_master_key));
    recentProof = profile.auth_scheme === "auth_key" ? { auth_key: authKey } : { password };
  }

  // Argon2id takes about a second; reuse it when the same sign-in is retried with a 2FA code.
  let lastDerivation: { email: string; password: string; salt: string; keys: { kek: Uint8Array; authKey: string } } | null = null;

  async function login(email: string, password: string, totpCode?: string): Promise<LoginResult> {
    isLoading.value = true;
    try {
      const pre = await apiRequest<Prelogin>("/api/v1/auth/prelogin", { method: "POST", body: JSON.stringify({ email }) });
      let keys: { kek: Uint8Array; authKey: string } | null = null;
      if (pre.kdf_salt) {
        const cached = lastDerivation;
        keys =
          cached && cached.email === email && cached.password === password && cached.salt === pre.kdf_salt
            ? cached.keys
            : await passwordKeys(password, pre.kdf_salt, pre.kdf_params || DEFAULT_KDF_PARAMS);
        lastDerivation = { email, password, salt: pre.kdf_salt, keys };
      }
      // Upgraded accounts never send the password. Older accounts send it with the derived key
      // once, and the server switches them over.
      const secret = pre.scheme === "auth_key" ? { auth_key: keys?.authKey } : { password, auth_key: keys?.authKey };
      const response = await apiRequest<{ user: UserProfile; access_token: string; mfa_required?: boolean }>(
        "/api/v1/auth/login",
        { method: "POST", body: JSON.stringify({ email, ...secret, totp_code: totpCode || undefined }) }
      );
      if (response.mfa_required) return { mfaRequired: true };
      lastDerivation = null;

      setAccessToken(response.access_token);
      user.value = response.user;

      const profile = response.user;
      const isAdmin = profile.is_staff || profile.is_superuser;
      if (profile.wrapped_master_key && profile.kdf_salt) {
        try {
          const kek = keys && profile.kdf_salt === pre.kdf_salt ? keys.kek : (await passwordKeys(password, profile.kdf_salt, profile.kdf_params)).kek;
          setMasterKey(await unwrapKey(kek, profile.wrapped_master_key));
          recentProof = profile.auth_scheme === "auth_key" ? { auth_key: keys?.authKey ?? "" } : { password };
        } catch {
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
    const vault = await createVaultMaterial(password);
    const res = await apiRequest<{ user: UserProfile }>("/api/v1/auth/vault", {
      method: "POST",
      body: JSON.stringify({ password, auth_key: vault.authKey, ...vault.payload }),
    });
    user.value = res.user;
    setMasterKey(vault.masterKey);
    recentProof = { auth_key: vault.authKey };
    pendingRecoveryKey.value = vault.recoveryKey;
  }

  /** Marks the recovery key made with the vault as saved. */
  async function confirmRecoveryKey() {
    const res = await apiRequest<{ user: UserProfile }>("/api/v1/auth/recovery-key/confirm", { method: "POST" });
    user.value = res.user;
    pendingRecoveryKey.value = null;
  }

  /** Whether making a new recovery key needs the password typed again. */
  const recoveryNeedsPassword = () => !recentProof;

  /**
   * Makes a new recovery key for the unlocked vault. Nothing is saved until `save()` is called,
   * after the user confirms they've stored the key.
   */
  async function prepareRecoveryKey() {
    if (!masterKey.value) throw new Error("Unlock your files first.");
    const material = await createRecoveryMaterial(masterKey.value);
    return {
      display: material.display,
      save: async (password?: string) => {
        const proof = password ? await proofFor(password) : recentProof;
        if (!proof) throw new Error("Enter your password.");
        const res = await apiRequest<{ user: UserProfile }>("/api/v1/auth/recovery-key", {
          method: "PUT",
          body: JSON.stringify({ ...proof, ...material.payload }),
        });
        user.value = res.user;
        pendingRecoveryKey.value = null;
        if (password) recentProof = proof;
      },
    };
  }

  /** Re-wraps the vault key with a new password; files don't need re-encrypting. */
  async function changePassword(current: string, next: string) {
    const u = user.value;
    if (!u) throw new Error("Sign in first.");
    let body: Record<string, unknown>;
    if (u.wrapped_master_key) {
      const { kek: currentKek, authKey: currentAuthKey } = await passwordKeys(current, u.kdf_salt, u.kdf_params || DEFAULT_KDF_PARAMS);
      let key: Uint8Array;
      try {
        key = await unwrapKey(currentKek, u.wrapped_master_key);
      } catch {
        throw Object.assign(new Error("That's not your current password."), { field: "current" });
      }
      const salt = generateRandomSalt(16);
      const { kek, authKey } = await passwordKeys(next, salt, DEFAULT_KDF_PARAMS);
      body = {
        ...(u.auth_scheme === "auth_key" ? { current_auth_key: currentAuthKey } : { current_password: current }),
        new_auth_key: authKey,
        new_wrapped_master_key: await wrapKey(kek, key),
        new_kdf_salt: salt,
        new_kdf_params: DEFAULT_KDF_PARAMS,
      };
      const res = await apiRequest<{ user: UserProfile }>("/api/v1/auth/password", { method: "POST", body: JSON.stringify(body) });
      user.value = res.user;
      setMasterKey(key);
      recentProof = { auth_key: authKey };
    } else {
      body = { current_password: current, new_password: next };
      const res = await apiRequest<{ user?: UserProfile }>("/api/v1/auth/password", { method: "POST", body: JSON.stringify(body) });
      if (res.user) user.value = res.user;
    }
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
    needsRecoveryKey,
    pendingRecoveryKey,
    register,
    login,
    loginWithGoogle,
    fetchAuthConfig,
    unlockVault,
    restoreGoogleVault,
    setupVault,
    confirmRecoveryKey,
    prepareRecoveryKey,
    recoveryNeedsPassword,
    changePassword,
    proofFor,
    fetchProfile,
    initAuth,
    logout,
  };
});

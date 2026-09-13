import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { apiRequest, setAccessToken, getAccessToken, refreshAccessToken } from "../lib/api";
import {
  generateRandomSalt,
  deriveKEK,
  DEFAULT_KDF_PARAMS,
  uint8ArrayToHex,
  uint8ArrayToBase64,
  base64ToUint8Array,
} from "../lib/crypto/kdf";
import {
  generateMasterKey,
  generateUserKeypair,
  wrapKey,
  unwrapKey,
} from "../lib/crypto/keys";
import {
  generateRecoveryPhrase,
  deriveRecoveryKey,
} from "../lib/crypto/recovery";

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

const VAULT_KEY_STORAGE_KEY = "sc_vault_mk";

function saveMasterKeyToSession(key: Uint8Array | null) {
  if (typeof window === "undefined" || !window.sessionStorage) return;
  if (key) {
    sessionStorage.setItem(VAULT_KEY_STORAGE_KEY, uint8ArrayToBase64(key));
  } else {
    sessionStorage.removeItem(VAULT_KEY_STORAGE_KEY);
  }
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

export const useAuthStore = defineStore("auth", () => {
  const user = ref<UserProfile | null>(null);
  const masterKey = ref<Uint8Array | null>(null);
  const isLoading = ref<boolean>(false);
  const isInitialized = ref<boolean>(false);
  const pendingRecoveryPhrase = ref<string[] | null>(null);

  const isAuthenticated = computed(() => !!user.value && !!getAccessToken());
  const isVaultUnlocked = computed(() => !!masterKey.value);
  const isMasterAdmin = computed(
    () => !!user.value?.is_staff || !!user.value?.is_superuser
  );
  const hasActiveSubscription = computed(
    () => isMasterAdmin.value || !!user.value?.subscription?.has_active_subscription
  );

  async function register(email: string, password: string, fullName: string = "") {
    isLoading.value = true;
    try {
      // 1. Generate 24-word recovery phrase and derive recovery key
      const recoveryWords = generateRecoveryPhrase();
      const recoveryKey = await deriveRecoveryKey(recoveryWords);

      // 2. Generate random KDF salt and derive KEK
      const kdfSalt = generateRandomSalt(16);
      const kek = await deriveKEK(password, kdfSalt, DEFAULT_KDF_PARAMS);

      // 3. Generate random 256-bit Master Key
      const newMasterKey = generateMasterKey();

      // 4. Generate user asymmetric keypair for file sharing
      const keypair = await generateUserKeypair();

      // 5. Wrap Master Key with KEK & with Recovery Key
      const wrappedMasterKey = await wrapKey(kek, newMasterKey);
      const recoveryWrappedMasterKey = await wrapKey(recoveryKey, newMasterKey);

      // 6. Wrap user's private key with Master Key
      const wrappedPrivateKey = await wrapKey(newMasterKey, keypair.privateKeyBytes);

      // 7. Send registration payload to backend
      const response = await apiRequest<{
        user: UserProfile;
        access_token: string;
      }>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
          wrapped_master_key: wrappedMasterKey,
          kdf_salt: kdfSalt,
          kdf_params: DEFAULT_KDF_PARAMS,
          public_key: keypair.publicKeyBase64,
          wrapped_private_key: wrappedPrivateKey,
          recovery_wrapped_master_key: recoveryWrappedMasterKey,
        }),
      });

      setAccessToken(response.access_token);
      user.value = response.user;
      masterKey.value = newMasterKey;
      saveMasterKeyToSession(newMasterKey);
      pendingRecoveryPhrase.value = recoveryWords;

      return { user: response.user, recoveryWords };
    } finally {
      isLoading.value = false;
    }
  }

  async function login(email: string, password: string, totpCode?: string) {
    isLoading.value = true;
    try {
      const response = await apiRequest<{
        user: UserProfile;
        access_token: string;
        mfa_required?: boolean;
      }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, totp_code: totpCode }),
      });

      if (response.mfa_required) {
        return { mfaRequired: true };
      }

      setAccessToken(response.access_token);
      user.value = response.user;
      if (!response.user.subscription) {
        await fetchProfile();
      }

      // Derive KEK and unwrap Master Key
      if (response.user.wrapped_master_key && response.user.kdf_salt) {
        try {
          const kek = await deriveKEK(
            password,
            response.user.kdf_salt,
            response.user.kdf_params || DEFAULT_KDF_PARAMS
          );
          masterKey.value = await unwrapKey(kek, response.user.wrapped_master_key);
          saveMasterKeyToSession(masterKey.value);
        } catch (err) {
          console.warn("Could not unwrap master key:", err);
          // For staff/admin accounts, allow portal access even if key derivation fails
          if (!response.user.is_staff && !response.user.is_superuser) {
            throw err;
          }
        }
      }

      return { success: true };
    } finally {
      isLoading.value = false;
    }
  }

  async function unlockVault(password: string) {
    if (!user.value || !user.value.wrapped_master_key) {
      throw new Error("No user profile found to unlock.");
    }
    const kek = await deriveKEK(
      password,
      user.value.kdf_salt,
      user.value.kdf_params || DEFAULT_KDF_PARAMS
    );
    masterKey.value = await unwrapKey(kek, user.value.wrapped_master_key);
    saveMasterKeyToSession(masterKey.value);
  }

  async function fetchProfile() {
    try {
      const profile = await apiRequest<UserProfile>("/api/v1/auth/me");
      user.value = profile;
    } catch {
      user.value = null;
      masterKey.value = null;
      setAccessToken(null);
      saveMasterKeyToSession(null);
    }
  }

  let initPromise: Promise<boolean> | null = null;

  async function initAuth(): Promise<boolean> {
    if (isInitialized.value) {
      return isAuthenticated.value;
    }
    if (initPromise) {
      return initPromise;
    }

    initPromise = (async () => {
      try {
        // 1. Restore masterKey from sessionStorage if present
        if (!masterKey.value) {
          const restoredKey = loadMasterKeyFromSession();
          if (restoredKey) {
            masterKey.value = restoredKey;
          }
        }

        // 2. If we already have an access token, verify and fetch profile
        const existingToken = getAccessToken();
        if (existingToken) {
          try {
            const profile = await apiRequest<UserProfile>("/api/v1/auth/me");
            user.value = profile;
            return true;
          } catch {
            // Access token might be invalid or expired; try refresh next
          }
        }

        // 3. Attempt silent refresh using the HTTP-only cookie
        const refreshData = await refreshAccessToken();
        if (refreshData?.access_token) {
          if (refreshData.user) {
            user.value = refreshData.user;
          } else {
            const profile = await apiRequest<UserProfile>("/api/v1/auth/me");
            user.value = profile;
          }
          return true;
        }

        // Neither access token nor refresh token worked
        user.value = null;
        masterKey.value = null;
        setAccessToken(null);
        saveMasterKeyToSession(null);
        return false;
      } catch (err) {
        console.warn("Auth initialization failed:", err);
        user.value = null;
        masterKey.value = null;
        setAccessToken(null);
        saveMasterKeyToSession(null);
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
      await apiRequest("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Ignore network failures on logout
    } finally {
      user.value = null;
      masterKey.value = null;
      setAccessToken(null);
      saveMasterKeyToSession(null);
    }
  }

  function clearRecoveryPhrase() {
    pendingRecoveryPhrase.value = null;
  }

  return {
    user,
    masterKey,
    isLoading,
    isInitialized,
    pendingRecoveryPhrase,
    isAuthenticated,
    isVaultUnlocked,
    isMasterAdmin,
    hasActiveSubscription,
    register,
    login,
    unlockVault,
    fetchProfile,
    initAuth,
    logout,
    clearRecoveryPhrase,
  };
});

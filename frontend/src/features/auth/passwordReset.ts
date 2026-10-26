import { apiRequest } from "../../lib/api";
import { normalizeApiError } from "../../lib/errors";
import { unwrapKey, wrapKey } from "../../lib/crypto/keys";
import { DEFAULT_KDF_PARAMS, generateRandomSalt } from "../../lib/crypto/kdf";
import { parseRecoveryKey, recoveryProof, recoveryWrappingKey } from "../../lib/crypto/recoveryKey";
import { createVaultMaterial, passwordKeys } from "../../stores/auth";

// Forgot-password flow. The email link carries a single-use token; the new password, the vault
// key and the recovery key stay in the browser. Only derived keys and wrapped blobs are sent.

export type ResetLink = { uid: string; token: string };
export type ResetInfo = { email: string; has_recovery_key: boolean; recovery_wrapped_master_key: string; has_vault: boolean };

export class RecoveryKeyMismatch extends Error {
  constructor() {
    super("That recovery key doesn't match this account. Check it and try again.");
  }
}

/** Reads uid and token from the link's fragment (#uid=…&token=…). */
export function readResetLink(hash: string): ResetLink | null {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const uid = params.get("uid");
  const token = params.get("token");
  return uid && token ? { uid, token } : null;
}

export function requestPasswordReset(email: string) {
  return apiRequest<{ message: string }>("/api/v1/auth/password-reset", { method: "POST", body: JSON.stringify({ email }) });
}

export function checkResetLink(link: ResetLink) {
  return apiRequest<ResetInfo>("/api/v1/auth/password-reset/check", { method: "POST", body: JSON.stringify(link) });
}

/** Unwraps the vault key with the recovery key and re-wraps it with the new password. Files stay readable. */
export async function resetWithRecoveryKey(link: ResetLink, info: ResetInfo, recoveryKeyText: string, newPassword: string) {
  const secret = parseRecoveryKey(recoveryKeyText);
  let masterKey: Uint8Array;
  try {
    masterKey = await unwrapKey(await recoveryWrappingKey(secret), info.recovery_wrapped_master_key);
  } catch {
    throw new RecoveryKeyMismatch();
  }
  const salt = generateRandomSalt(16);
  const { kek, authKey } = await passwordKeys(newPassword, salt, DEFAULT_KDF_PARAMS);
  try {
    await apiRequest("/api/v1/auth/password-reset/complete", {
      method: "POST",
      body: JSON.stringify({
        ...link,
        mode: "recovery",
        recovery_auth: await recoveryProof(secret),
        auth_key: authKey,
        wrapped_master_key: await wrapKey(kek, masterKey),
        kdf_salt: salt,
        kdf_params: DEFAULT_KDF_PARAMS,
      }),
    });
  } catch (err) {
    if (normalizeApiError(err).code === "RECOVERY_KEY_MISMATCH") throw new RecoveryKeyMismatch();
    throw err;
  }
}

/** No recovery key: a new, empty vault. Files uploaded before can't be decrypted afterwards. */
export async function resetWithoutRecoveryKey(link: ResetLink, newPassword: string) {
  const vault = await createVaultMaterial(newPassword, { withRecovery: false });
  await apiRequest("/api/v1/auth/password-reset/complete", {
    method: "POST",
    body: JSON.stringify({ ...link, mode: "reset", confirm_data_loss: true, auth_key: vault.authKey, ...vault.payload }),
  });
}

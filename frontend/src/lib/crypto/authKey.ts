import { hkdf } from "./hkdf";
import { uint8ArrayToHex } from "./kdf";

/**
 * The sign-in secret sent to the server instead of the password. It is derived one-way from the
 * password's key-encryption key (Argon2id), so the server can verify it but can't use it to
 * unwrap the vault key.
 */
export async function deriveAuthKey(kek: Uint8Array): Promise<string> {
  return uint8ArrayToHex(await hkdf(kek, "smartspace-auth-v1"));
}

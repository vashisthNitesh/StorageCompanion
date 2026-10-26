import { argon2id } from "hash-wasm";
import { hkdf } from "./hkdf";
import { generateRandomBytes } from "./keys";
import { hexToUint8Array, uint8ArrayToHex } from "./kdf";

/**
 * Keys for public file links. A random link key travels only in the URL fragment (after #),
 * which browsers never send to the server. An optional password adds a second key derived
 * in the browser; the file key is then wrapped with a key that needs both.
 */

/** Lighter than the vault's Argon2id so links open quickly on phones. */
export const SHARE_KDF_PARAMS = { iterations: 2, memorySize: 19456, parallelism: 1, hashLength: 32 };

export function generateLinkKey(): Uint8Array {
  return generateRandomBytes(32);
}

export function encodeLinkKey(key: Uint8Array): string {
  let binary = "";
  for (const b of key) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodeLinkKey(text: string): Uint8Array | null {
  try {
    const b64 = text.replace(/-/g, "+").replace(/_/g, "/");
    const binary = atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
    return bytes.length === 32 ? bytes : null;
  } catch {
    return null;
  }
}

/** From a link password: a wrapping key (stays in the browser) and a proof (its SHA-256 is stored on the server). */
export async function passwordLayer(password: string, saltHex: string, params = SHARE_KDF_PARAMS) {
  const derived = await argon2id({
    password,
    salt: hexToUint8Array(saltHex),
    iterations: params.iterations,
    memorySize: params.memorySize,
    parallelism: params.parallelism,
    hashLength: 32,
    outputType: "binary",
  });
  return {
    key: await hkdf(derived, "smartspace-share-wrap-v1"),
    proof: uint8ArrayToHex(await hkdf(derived, "smartspace-share-auth-v1")),
  };
}

/** The key that wraps the file key and name: the link key alone, or combined with the password key. */
export async function shareWrappingKey(linkKey: Uint8Array, passwordKey?: Uint8Array): Promise<Uint8Array> {
  if (!passwordKey) return linkKey;
  const both = new Uint8Array(linkKey.length + passwordKey.length);
  both.set(linkKey);
  both.set(passwordKey, linkKey.length);
  return hkdf(both, "smartspace-share-key-v1");
}

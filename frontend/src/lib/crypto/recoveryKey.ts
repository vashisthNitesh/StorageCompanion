import { hkdf, sha256Hex } from "./hkdf";
import { generateRandomBytes } from "./keys";
import { uint8ArrayToHex } from "./kdf";

/**
 * Recovery key: 160 random bits, shown once as 32 Crockford base32 characters in groups of four
 * (e.g. 7KQ4-M2XD-…). From it the browser derives a key that wraps the vault key, and a proof
 * whose SHA-256 the server stores so a password reset can show the key is known. The key itself
 * never leaves the browser.
 */
const ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
const KEY_BYTES = 20;
const KEY_CHARS = 32;

export class InvalidRecoveryKey extends Error {
  constructor() {
    super("That doesn't look like a recovery key. It has 32 letters and numbers.");
  }
}

function encode(bytes: Uint8Array): string {
  let bits = 0;
  let value = 0;
  let out = "";
  for (const b of bytes) {
    value = (value << 8) | b;
    bits += 8;
    while (bits >= 5) {
      out += ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  return out;
}

function decode(text: string): Uint8Array {
  let bits = 0;
  let value = 0;
  const out: number[] = [];
  for (const ch of text) {
    const idx = ALPHABET.indexOf(ch);
    if (idx < 0) throw new InvalidRecoveryKey();
    value = ((value << 5) | idx) & 0xffff;
    bits += 5;
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return new Uint8Array(out);
}

export function formatRecoveryKey(secret: Uint8Array): string {
  return encode(secret).match(/.{4}/g)!.join("-");
}

/** Accepts any case, spaces or dashes, and the usual look-alikes (O→0, I/L→1). */
export function parseRecoveryKey(input: string): Uint8Array {
  const clean = input
    .toUpperCase()
    .replace(/[\s-]/g, "")
    .replace(/O/g, "0")
    .replace(/[IL]/g, "1");
  if (clean.length !== KEY_CHARS) throw new InvalidRecoveryKey();
  return decode(clean);
}

export function generateRecoveryKey(): { secret: Uint8Array; display: string } {
  const secret = generateRandomBytes(KEY_BYTES);
  return { secret, display: formatRecoveryKey(secret) };
}

export function recoveryWrappingKey(secret: Uint8Array): Promise<Uint8Array> {
  return hkdf(secret, "smartspace-recovery-wrap-v1");
}

/** The proof sent when resetting a password with the recovery key. */
export async function recoveryProof(secret: Uint8Array): Promise<string> {
  return uint8ArrayToHex(await hkdf(secret, "smartspace-recovery-auth-v1"));
}

/** What the server stores to check the proof later. */
export async function recoveryProofHash(secret: Uint8Array): Promise<string> {
  return sha256Hex(await hkdf(secret, "smartspace-recovery-auth-v1"));
}

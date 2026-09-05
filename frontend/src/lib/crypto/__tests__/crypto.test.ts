import { describe, it, expect } from "vitest";
import {
  generateRandomSalt,
  deriveKEK,
  uint8ArrayToHex,
  hexToUint8Array,
} from "../kdf";
import {
  generateMasterKey,
  generateFileKey,
  wrapKey,
  unwrapKey,
} from "../keys";
import {
  deriveChunkNonce,
  encryptChunk,
  decryptChunk,
} from "../content";
import {
  encryptName,
  decryptName,
} from "../names";
import {
  generateRecoveryPhrase,
  deriveRecoveryKey,
} from "../recovery";

describe("Pure Crypto Module", () => {
  it("generates random salt and hex conversions round-trip", () => {
    const salt = generateRandomSalt(16);
    expect(salt).toHaveLength(32);
    const bytes = hexToUint8Array(salt);
    expect(bytes).toHaveLength(16);
    expect(uint8ArrayToHex(bytes)).toBe(salt);
  });

  it("derives KEK deterministically with Argon2id", async () => {
    const password = "TestPassword2026!";
    const saltHex = "00112233445566778899aabbccddeeff";
    const kek1 = await deriveKEK(password, saltHex, {
      iterations: 2,
      memorySize: 1024, // low memory for fast unit test
      parallelism: 1,
      hashLength: 32,
    });
    const kek2 = await deriveKEK(password, saltHex, {
      iterations: 2,
      memorySize: 1024,
      parallelism: 1,
      hashLength: 32,
    });
    expect(kek1).toHaveLength(32);
    expect(uint8ArrayToHex(kek1)).toBe(uint8ArrayToHex(kek2));
  });

  it("wraps and unwraps keys correctly", async () => {
    const masterKey = generateMasterKey();
    const fileKey = generateFileKey();

    const wrappedBlob = await wrapKey(masterKey, fileKey);
    expect(typeof wrappedBlob).toBe("string");

    const unwrappedKey = await unwrapKey(masterKey, wrappedBlob);
    expect(uint8ArrayToHex(unwrappedKey)).toBe(uint8ArrayToHex(fileKey));
  });

  it("encrypts and decrypts chunks with derived nonces", async () => {
    const fileKey = generateFileKey();
    const baseNonce = new Uint8Array(12);
    crypto.getRandomValues(baseNonce);

    const chunk1Data = new TextEncoder().encode("Hello World, SpeedCloud chunk 1!");
    const chunkNonce1 = deriveChunkNonce(baseNonce, 1);
    const chunkNonce2 = deriveChunkNonce(baseNonce, 2);

    expect(uint8ArrayToHex(chunkNonce1)).not.toBe(uint8ArrayToHex(chunkNonce2));

    const encryptedChunk = await encryptChunk(fileKey, chunk1Data, baseNonce, 1);
    const decryptedChunk = await decryptChunk(fileKey, encryptedChunk, baseNonce, 1);

    expect(new TextDecoder().decode(decryptedChunk)).toBe("Hello World, SpeedCloud chunk 1!");
  });

  it("encrypts and decrypts file and folder names", async () => {
    const masterKey = generateMasterKey();
    const originalName = "Tax_Declaration_2026_Final.pdf";

    const { ciphertextBase64, nonceHex } = await encryptName(masterKey, originalName);
    expect(ciphertextBase64).not.toBe(originalName);

    const decrypted = await decryptName(masterKey, ciphertextBase64, nonceHex);
    expect(decrypted).toBe(originalName);
  });

  it("generates 24-word recovery phrase and derives recovery key", async () => {
    const phrase = generateRecoveryPhrase();
    expect(phrase).toHaveLength(24);

    const key1 = await deriveRecoveryKey(phrase);
    const key2 = await deriveRecoveryKey(phrase.join(" "));
    expect(key1).toHaveLength(32);
    expect(uint8ArrayToHex(key1)).toBe(uint8ArrayToHex(key2));
  });
});

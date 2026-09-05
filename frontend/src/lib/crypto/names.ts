import {
  uint8ArrayToBase64,
  base64ToUint8Array,
  uint8ArrayToHex,
  hexToUint8Array,
} from "./kdf";
import { generateRandomBytes } from "./keys";

export async function encryptName(
  masterKeyBytes: Uint8Array,
  plaintextName: string
): Promise<{ ciphertextBase64: string; nonceHex: string }> {
  const nonce = generateRandomBytes(12);
  const encoder = new TextEncoder();
  const nameBytes = encoder.encode(plaintextName);

  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    masterKeyBytes,
    { name: "AES-GCM" },
    false,
    ["encrypt"]
  );

  const encryptedBuffer = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce },
    cryptoKey,
    nameBytes
  );

  return {
    ciphertextBase64: uint8ArrayToBase64(new Uint8Array(encryptedBuffer)),
    nonceHex: uint8ArrayToHex(nonce),
  };
}

export async function decryptName(
  masterKeyBytes: Uint8Array,
  ciphertextBase64: string,
  nonceHex: string
): Promise<string> {
  try {
    const nonce = hexToUint8Array(nonceHex);
    const ciphertext = base64ToUint8Array(ciphertextBase64);

    const cryptoKey = await crypto.subtle.importKey(
      "raw",
      masterKeyBytes,
      { name: "AES-GCM" },
      false,
      ["decrypt"]
    );

    const decryptedBuffer = await crypto.subtle.decrypt(
      { name: "AES-GCM", iv: nonce },
      cryptoKey,
      ciphertext
    );

    const decoder = new TextDecoder();
    return decoder.decode(decryptedBuffer);
  } catch (err) {
    return "[Encrypted File]";
  }
}

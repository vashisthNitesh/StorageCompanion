import { uint8ArrayToBase64, base64ToUint8Array } from "./kdf";

export function generateRandomBytes(length: number): Uint8Array {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return bytes;
}

export function generateMasterKey(): Uint8Array {
  return generateRandomBytes(32); // 256 bits
}

export function generateFileKey(): Uint8Array {
  return generateRandomBytes(32); // 256 bits
}

export function generateLinkKey(): Uint8Array {
  return generateRandomBytes(32); // 256 bits
}

/**
 * Wraps a target key using AES-256-GCM with a 12-byte random nonce.
 * Returns base64 containing: [12-byte IV] + [Ciphertext + Tag]
 */
export async function wrapKey(
  wrappingKeyBytes: Uint8Array,
  targetKeyBytes: Uint8Array
): Promise<string> {
  const iv = generateRandomBytes(12);
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    wrappingKeyBytes,
    { name: "AES-GCM" },
    false,
    ["encrypt"]
  );

  const encryptedBuffer = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    cryptoKey,
    targetKeyBytes
  );

  const encryptedBytes = new Uint8Array(encryptedBuffer);
  const combined = new Uint8Array(iv.length + encryptedBytes.length);
  combined.set(iv, 0);
  combined.set(encryptedBytes, iv.length);

  return uint8ArrayToBase64(combined);
}

/**
 * Unwraps an AES-256-GCM wrapped key blob.
 */
export async function unwrapKey(
  wrappingKeyBytes: Uint8Array,
  wrappedBase64: string
): Promise<Uint8Array> {
  const combined = base64ToUint8Array(wrappedBase64);
  if (combined.length < 12 + 16) {
    throw new Error("Invalid wrapped key payload size.");
  }

  const iv = combined.slice(0, 12);
  const ciphertext = combined.slice(12);

  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    wrappingKeyBytes,
    { name: "AES-GCM" },
    false,
    ["decrypt"]
  );

  const decryptedBuffer = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    cryptoKey,
    ciphertext
  );

  return new Uint8Array(decryptedBuffer);
}

/**
 * Generates an asymmetric keypair for user-to-user sharing.
 */
export async function generateUserKeypair(): Promise<{
  publicKeyBase64: string;
  privateKeyBytes: Uint8Array;
}> {
  // Use ECDH with P-256 (widely supported across all browser WebCrypto implementations)
  const keyPair = await crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveKey", "deriveBits"]
  );

  const spkiBuffer = await crypto.subtle.exportKey("spki", keyPair.publicKey);
  const pkcs8Buffer = await crypto.subtle.exportKey("pkcs8", keyPair.privateKey);

  return {
    publicKeyBase64: uint8ArrayToBase64(new Uint8Array(spkiBuffer)),
    privateKeyBytes: new Uint8Array(pkcs8Buffer),
  };
}

/**
 * Derives a shared wrapping key between recipient's public key and sender's private key.
 */
export async function deriveSharedSecret(
  privateKeyBytes: Uint8Array,
  peerPublicKeyBase64: string
): Promise<Uint8Array> {
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    privateKeyBytes,
    { name: "ECDH", namedCurve: "P-256" },
    false,
    ["deriveBits"]
  );

  const peerPublicKey = await crypto.subtle.importKey(
    "spki",
    base64ToUint8Array(peerPublicKeyBase64),
    { name: "ECDH", namedCurve: "P-256" },
    false,
    []
  );

  const sharedBits = await crypto.subtle.deriveBits(
    { name: "ECDH", public: peerPublicKey },
    privateKey,
    256
  );

  return new Uint8Array(sharedBits);
}

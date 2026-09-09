import { argon2id } from "hash-wasm";

export interface KDFParams {
  iterations: number;
  memorySize: number; // in KiB
  parallelism: number;
  hashLength: number;
}

export const DEFAULT_KDF_PARAMS: KDFParams = {
  iterations: 3,
  memorySize: 65536, // 64 MB
  parallelism: 4,
  hashLength: 32,    // 256 bits
};

export function generateRandomSalt(bytes: number = 16): string {
  const salt = new Uint8Array(bytes);
  crypto.getRandomValues(salt);
  return Array.from(salt).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function hexToUint8Array(hexString: string): Uint8Array {
  const matches = hexString.match(/.{1,2}/g) || [];
  return new Uint8Array(matches.map((byte) => parseInt(byte, 16)));
}

export function uint8ArrayToHex(bytes: Uint8Array): string {
  return Array.from(bytes).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = "";
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function base64ToUint8Array(base64: string): Uint8Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Derives a 256-bit Key Encryption Key (KEK) from password and salt using Argon2id WebAssembly.
 */
export async function deriveKEK(
  password: string,
  saltHex: string,
  params: any = DEFAULT_KDF_PARAMS
): Promise<Uint8Array> {
  const salt = hexToUint8Array(saltHex);
  const iterations = params?.iterations ?? params?.t ?? DEFAULT_KDF_PARAMS.iterations;
  const memorySize = params?.memorySize ?? params?.m ?? DEFAULT_KDF_PARAMS.memorySize;
  const parallelism = params?.parallelism ?? params?.p ?? DEFAULT_KDF_PARAMS.parallelism;
  const hashLength = params?.hashLength ?? DEFAULT_KDF_PARAMS.hashLength;
  const derivedBytes = await argon2id({
    password,
    salt,
    iterations,
    memorySize,
    parallelism,
    hashLength,
    outputType: "binary",
  });
  return derivedBytes;
}

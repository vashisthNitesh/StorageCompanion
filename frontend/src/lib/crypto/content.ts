export function deriveChunkNonce(baseNonce: Uint8Array, chunkIndex: number): Uint8Array {
  if (baseNonce.length !== 12) {
    throw new Error("Base nonce must be 12 bytes.");
  }
  const chunkNonce = new Uint8Array(baseNonce);
  // XOR the 32-bit chunkIndex into the last 4 bytes of the nonce
  const view = new DataView(chunkNonce.buffer, chunkNonce.byteOffset, chunkNonce.byteLength);
  const currentVal = view.getUint32(8, false); // big-endian
  view.setUint32(8, currentVal ^ chunkIndex, false);
  return chunkNonce;
}

export async function encryptChunk(
  fileKeyBytes: Uint8Array,
  chunkBytes: Uint8Array,
  baseNonce: Uint8Array,
  chunkIndex: number
): Promise<Uint8Array> {
  const nonce = deriveChunkNonce(baseNonce, chunkIndex);
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    fileKeyBytes,
    { name: "AES-GCM" },
    false,
    ["encrypt"]
  );

  const encryptedBuffer = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce },
    cryptoKey,
    chunkBytes
  );

  return new Uint8Array(encryptedBuffer);
}

export async function decryptChunk(
  fileKeyBytes: Uint8Array,
  encryptedChunkBytes: Uint8Array,
  baseNonce: Uint8Array,
  chunkIndex: number
): Promise<Uint8Array> {
  const nonce = deriveChunkNonce(baseNonce, chunkIndex);
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    fileKeyBytes,
    { name: "AES-GCM" },
    false,
    ["decrypt"]
  );

  const decryptedBuffer = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: nonce },
    cryptoKey,
    encryptedChunkBytes
  );

  return new Uint8Array(decryptedBuffer);
}

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

/**
 * Decrypts an entire file from encrypted bytes that may span one or more chunks.
 * Standard multipart chunk size is 8 MB (8,388,608 bytes) or 16 MB for files > 5 GB.
 * Each encrypted part has a 16-byte GCM authentication tag appended.
 */
export async function decryptFile(
  fileKeyBytes: Uint8Array,
  encryptedBytes: Uint8Array,
  baseNonce: Uint8Array,
  partSize: number = 8 * 1024 * 1024
): Promise<Uint8Array> {
  const encPartSize = partSize + 16;
  if (encryptedBytes.length <= encPartSize) {
    return await decryptChunk(fileKeyBytes, encryptedBytes, baseNonce, 1);
  }

  const totalParts = Math.ceil(encryptedBytes.length / encPartSize);
  const decryptedParts: Uint8Array[] = [];
  let totalDecryptedLength = 0;

  for (let partNumber = 1; partNumber <= totalParts; partNumber++) {
    const start = (partNumber - 1) * encPartSize;
    const end = Math.min(encryptedBytes.length, start + encPartSize);
    const chunkEncrypted = encryptedBytes.subarray(start, end);
    const decryptedChunk = await decryptChunk(
      fileKeyBytes,
      chunkEncrypted,
      baseNonce,
      partNumber
    );
    decryptedParts.push(decryptedChunk);
    totalDecryptedLength += decryptedChunk.length;
  }

  const combined = new Uint8Array(totalDecryptedLength);
  let offset = 0;
  for (const part of decryptedParts) {
    combined.set(part, offset);
    offset += part.length;
  }
  return combined;
}

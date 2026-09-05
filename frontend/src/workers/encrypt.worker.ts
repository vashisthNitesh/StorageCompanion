import { encryptChunk, decryptChunk } from "../lib/crypto/content";

self.onmessage = async (e: MessageEvent) => {
  const { id, action, fileKeyBytes, chunkBytes, baseNonce, chunkIndex } = e.data;

  try {
    if (action === "encrypt") {
      const encrypted = await encryptChunk(fileKeyBytes, chunkBytes, baseNonce, chunkIndex);
      (self as any).postMessage({ id, success: true, encryptedBytes: encrypted }, [encrypted.buffer]);
    } else if (action === "decrypt") {
      const decrypted = await decryptChunk(fileKeyBytes, chunkBytes, baseNonce, chunkIndex);
      (self as any).postMessage({ id, success: true, decryptedBytes: decrypted }, [decrypted.buffer]);
    }
  } catch (error: any) {
    (self as any).postMessage({ id, success: false, error: error.message });
  }
};

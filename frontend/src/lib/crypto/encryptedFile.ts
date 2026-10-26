// Random-access reader for an encrypted file. Files are encrypted in independent
// AES-GCM parts (part_size bytes of plaintext + a 16-byte tag), so any byte range
// can be served by fetching and decrypting only the parts that cover it.

import { apiFetchRetrying, apiRequest, errorFromResponse } from "../api";
import { unwrapKey } from "./keys";
import { deriveChunkNonce, importFileKey } from "./content";
import { hexToUint8Array } from "./kdf";

const GCM_TAG = 16;
const CACHED_PARTS = 6;
/** Without HTTP range support the whole file has to be fetched; only allowed up to this size. */
const MAX_WHOLE_FETCH = 256 * 1024 * 1024;

export class DecryptError extends Error {
  constructor() {
    super("decrypt_failed");
  }
}

/** Why the browser asked for the key: thumbnails aren't logged as activity, previews are. */
export type ReadPurpose = "preview" | "thumbnail";

interface DownloadInfo {
  download_url: string;
  wrapped_file_key: string;
  content_nonce: string;
  size_bytes: number;
  part_size: number;
}

export interface EncryptedFile {
  /** Plaintext size in bytes. */
  readonly size: number;
  /** Plaintext bytes [start, end). */
  read(start: number, end: number): Promise<Uint8Array>;
  /** The whole file, with progress from 0 to 1. */
  readAll(onProgress?: (fraction: number) => void): Promise<Blob>;
}

export async function openEncryptedFile(
  node: { id: string },
  masterKey: Uint8Array,
  purpose: ReadPurpose
): Promise<EncryptedFile> {
  const info = await apiRequest<DownloadInfo>(`/api/v1/nodes/${node.id}/download?purpose=${purpose}`);
  let key: CryptoKey;
  try {
    key = await importFileKey(await unwrapKey(masterKey, info.wrapped_file_key));
  } catch {
    throw new DecryptError();
  }
  // Thumbnails give up quickly (they're retried the next time they're shown) so one failing
  // file can't hold up the thumbnail queue; previews and downloads wait out a busy server.
  return encryptedFileFrom(info, key, { attempts: purpose === "thumbnail" ? 2 : 8 });
}

/**
 * Reader over encrypted content at `info.download_url`, decrypted with `key`. `headers` go with
 * every content request (a shared link sends its access grant this way).
 */
export function encryptedFileFrom(
  info: Omit<DownloadInfo, "wrapped_file_key">,
  key: CryptoKey,
  { attempts = 8, headers = {} as Record<string, string> } = {}
): EncryptedFile {
  const baseNonce = hexToUint8Array(info.content_nonce);
  const size = info.size_bytes;
  const partSize = info.part_size || 8 * 1024 * 1024;
  const encPart = partSize + GCM_TAG;
  const partCount = Math.max(1, Math.ceil(size / partSize));
  const plainLength = (n: number) => Math.min(partSize, size - (n - 1) * partSize);

  async function decryptPart(bytes: Uint8Array, n: number): Promise<Uint8Array> {
    try {
      return new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: deriveChunkNonce(baseNonce, n) }, key, bytes));
    } catch {
      throw new DecryptError();
    }
  }

  // Small LRU of decrypted parts; in-flight reads are shared.
  const cache = new Map<number, Promise<Uint8Array>>();
  let wholeFile: Promise<void> | null = null;

  function remember(n: number, p: Promise<Uint8Array>) {
    cache.set(n, p);
    p.catch(() => cache.delete(n));
    while (cache.size > CACHED_PARTS) cache.delete(cache.keys().next().value!);
  }

  async function fetchWhole() {
    if (size > MAX_WHOLE_FETCH) throw new Error("range_unsupported");
    const res = await apiFetchRetrying(info.download_url, { headers, timeoutMs: 60_000 }, attempts);
    if (!res.ok) throw await errorFromResponse(res);
    const all = new Uint8Array(await res.arrayBuffer());
    for (let n = 1; n <= partCount; n++) {
      const start = (n - 1) * encPart;
      remember(n, decryptPart(all.subarray(start, start + plainLength(n) + GCM_TAG), n));
    }
  }

  function part(n: number): Promise<Uint8Array> {
    const hit = cache.get(n);
    if (hit) {
      cache.delete(n);
      cache.set(n, hit);
      return hit;
    }
    if (wholeFile) return wholeFile.then(() => part(n));
    const p = (async () => {
      const start = (n - 1) * encPart;
      const end = start + plainLength(n) + GCM_TAG - 1;
      const res = await apiFetchRetrying(info.download_url, { headers: { ...headers, Range: `bytes=${start}-${end}` }, timeoutMs: 60_000 }, attempts);
      if (res.status === 200) {
        // Storage ignored the range and sent everything.
        await res.body?.cancel();
        wholeFile ??= fetchWhole();
        await wholeFile;
        return part(n);
      }
      if (!res.ok) throw await errorFromResponse(res);
      return decryptPart(new Uint8Array(await res.arrayBuffer()), n);
    })();
    remember(n, p);
    return p;
  }

  async function read(start: number, end: number): Promise<Uint8Array> {
    end = Math.min(end, size);
    if (start >= end) return new Uint8Array(0);
    const first = Math.floor(start / partSize) + 1;
    const last = Math.floor((end - 1) / partSize) + 1;
    // Read ahead one part so sequential playback doesn't wait at part boundaries.
    if (last < partCount && !cache.has(last + 1)) void part(last + 1).catch(() => {});
    const out = new Uint8Array(end - start);
    let offset = 0;
    for (let n = first; n <= last; n++) {
      const plain = await part(n);
      const partStart = (n - 1) * partSize;
      const from = Math.max(start, partStart) - partStart;
      const to = Math.min(end, partStart + plain.length) - partStart;
      out.set(plain.subarray(from, to), offset);
      offset += to - from;
    }
    return out;
  }

  async function readAll(onProgress?: (fraction: number) => void): Promise<Blob> {
    const res = await apiFetchRetrying(info.download_url, { headers, timeoutMs: 60_000 }, attempts);
    if (!res.ok) throw await errorFromResponse(res);
    if (!res.body) throw new DecryptError();
    const reader = res.body.getReader();
    const parts: Uint8Array[] = [];
    const total = size + partCount * GCM_TAG;
    let buffer = new Uint8Array(encPart * 2);
    let buffered = 0;
    let received = 0;
    let n = 1;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value?.length) continue;
      received += value.length;
      onProgress?.(Math.min(0.99, received / total));
      if (buffered + value.length > buffer.length) {
        const grown = new Uint8Array(Math.max(buffer.length * 2, buffered + value.length));
        grown.set(buffer.subarray(0, buffered));
        buffer = grown;
      }
      buffer.set(value, buffered);
      buffered += value.length;
      while (buffered >= encPart) {
        parts.push(await decryptPart(buffer.slice(0, encPart), n++));
        buffer.copyWithin(0, encPart, buffered);
        buffered -= encPart;
      }
    }
    if (buffered > 0) parts.push(await decryptPart(buffer.slice(0, buffered), n));
    onProgress?.(1);
    return new Blob(parts as BlobPart[]);
  }

  return { size, read, readAll };
}

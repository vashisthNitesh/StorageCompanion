import { apiFetch } from "./index";
import { decryptChunk } from "../crypto/content";

/**
 * Helpers for fetching encrypted file bytes with bounded waits.
 *
 * Previously preview/download awaited `fetch(direct_url)` and the body with no timeout, so a
 * hanging edge/presigned URL (or a stalled proxy stream) left the UI spinning forever.
 */

export interface EncryptedSource {
  download_url: string;
  direct_url?: string | null;
}

export interface OpenedStream {
  res: Response;
  source: "direct" | "proxy";
  controller: AbortController;
}

const isLocalHost = (h: string) =>
  h === "localhost" || h === "[::1]" || h.endsWith(".localhost") || /^127\./.test(h);

/** Only use a direct storage URL when the browser can plausibly reach it. */
export function isUsableDirectUrl(url?: string | null): boolean {
  if (!url || typeof window === "undefined") return false;
  let u: URL;
  try {
    u = new URL(url, window.location.href);
  } catch {
    return false;
  }
  if (u.protocol !== "https:" && u.protocol !== "http:") return false;
  // Never probe the visitor's own machine (e.g. an unconfigured S3 endpoint of http://localhost:9000)
  if (isLocalHost(u.hostname) && !isLocalHost(window.location.hostname)) return false;
  // Mixed content would be blocked anyway
  if (window.location.protocol === "https:" && u.protocol === "http:" && !isLocalHost(u.hostname)) return false;
  return true;
}

function linkedController(signal?: AbortSignal): AbortController {
  const controller = new AbortController();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  return controller;
}

async function errorMessageFrom(res: Response): Promise<string> {
  let msg = `Failed to fetch file from storage (${res.status})`;
  try {
    const body = await res.json();
    msg = body?.error?.message || body?.error || body?.detail || msg;
    if (typeof msg !== "string") msg = `Failed to fetch file from storage (${res.status})`;
  } catch {
    /* non-JSON error body */
  }
  return msg;
}

/**
 * Opens the encrypted byte stream: direct edge URL first (bounded by directTimeoutMs), then the
 * authenticated backend proxy (bounded by proxyTimeoutMs until response headers arrive).
 */
export async function openEncryptedStream(
  src: EncryptedSource,
  opts: {
    signal?: AbortSignal;
    directTimeoutMs?: number;
    proxyTimeoutMs?: number;
    skipDirect?: boolean;
    range?: string;
  } = {}
): Promise<OpenedStream> {
  const { signal, directTimeoutMs = 10_000, proxyTimeoutMs = 45_000, skipDirect = false, range } = opts;
  const rangeHeaders: Record<string, string> = range ? { Range: range } : {};

  if (!skipDirect && isUsableDirectUrl(src.direct_url)) {
    const controller = linkedController(signal);
    const timer = setTimeout(() => controller.abort(), directTimeoutMs);
    try {
      const res = await fetch(src.direct_url as string, {
        method: "GET",
        headers: rangeHeaders,
        signal: controller.signal,
      });
      clearTimeout(timer);
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      // An HTML/JSON body here is a login page or error document, not ciphertext
      if (res.ok && res.body && !ct.includes("text/html") && !ct.includes("application/json")) {
        return { res, source: "direct", controller };
      }
      controller.abort();
    } catch {
      clearTimeout(timer);
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      // CORS/network/timeout: fall back to the proxy
    }
  }

  const controller = linkedController(signal);
  const timer = setTimeout(() => controller.abort(), proxyTimeoutMs);
  let res: Response;
  try {
    res = await apiFetch(src.download_url, { headers: rangeHeaders, signal: controller.signal });
  } catch (err) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    if (controller.signal.aborted) throw new Error("Storage took too long to respond. Please try again.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) throw new Error(await errorMessageFrom(res));
  return { res, source: "proxy", controller };
}

/** reader.read() that aborts the request if no data arrives for stallMs. */
export async function readChunkWithStallTimeout(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  controller: AbortController,
  stallMs = 30_000
): Promise<ReadableStreamReadResult<Uint8Array>> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const stalled = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new Error("Download stalled: storage stopped sending data. Please try again."));
    }, stallMs);
  });
  try {
    return await Promise.race([reader.read(), stalled]);
  } finally {
    clearTimeout(timer);
  }
}

/** Reads a whole response body with a stall timeout. */
export async function readAllWithStallTimeout(
  res: Response,
  controller: AbortController,
  stallMs = 30_000
): Promise<Uint8Array> {
  if (!res.body) return new Uint8Array(await res.arrayBuffer());
  const reader = res.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await readChunkWithStallTimeout(reader, controller, stallMs);
    if (done) break;
    if (value?.length) {
      chunks.push(value);
      total += value.length;
    }
  }
  const out = new Uint8Array(total);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.length;
  }
  return out;
}

class FatalDownloadError extends Error {}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export interface RangedDecryptOptions {
  fileKey: Uint8Array;
  baseNonce: Uint8Array;
  partSize: number;
  /** Plaintext size from metadata; used until the server reports the real encrypted size. */
  plainSize: number;
  /** Receives decrypted parts in order. */
  onPart: (plain: Uint8Array) => Promise<void> | void;
  onProgress?: (encryptedBytesDone: number, encryptedTotal: number) => void;
  signal?: AbortSignal;
  /** Encrypted parts per HTTP request (default 8, i.e. ~64 MB). */
  partsPerRequest?: number;
  maxRetries?: number;
}

/**
 * Downloads and decrypts a chunked AES-GCM file using HTTP Range requests.
 *
 * Each request covers a bounded window of encrypted parts and decrypted parts are handed to
 * onPart as soon as they're complete, so memory stays bounded. A dropped connection (common on
 * multi-GB transfers through a proxy) resumes from the first part not yet decrypted instead of
 * failing the whole download. If the server ignores Range (200), the single stream is consumed.
 */
export async function downloadDecryptRanged(src: EncryptedSource, opts: RangedDecryptOptions): Promise<void> {
  const { fileKey, baseNonce, partSize, onPart, onProgress, signal } = opts;
  const partsPerRequest = opts.partsPerRequest ?? 8;
  const maxRetries = opts.maxRetries ?? 5;
  const encPartSize = partSize + 16;
  const plainParts = Math.max(1, Math.ceil(opts.plainSize / partSize));
  let encTotal = opts.plainSize + 16 * plainParts;
  let skipDirect = false;
  let nextPart = 1;
  let attempt = 0;

  const totalParts = () => Math.max(1, Math.ceil(encTotal / encPartSize));
  const partLen = (n: number) => (n < totalParts() ? encPartSize : encTotal - (totalParts() - 1) * encPartSize);

  while (true) {
    const start = (nextPart - 1) * encPartSize;
    if (start >= encTotal) return;
    const end = Math.min(start + partsPerRequest * encPartSize, encTotal) - 1;
    try {
      const opened = await openEncryptedStream(src, { signal, skipDirect, range: `bytes=${start}-${end}` });
      if (opened.source === "proxy") skipDirect = true;
      const { res, controller } = opened;
      if (res.status === 416) return; // nothing left
      const rangeless = res.status === 200;
      if (rangeless && start > 0) {
        throw new FatalDownloadError("Storage doesn't support resuming this download. Please try again.");
      }
      const cr = res.headers.get("content-range");
      const m = cr && /\/(\d+)\s*$/.exec(cr);
      if (m) encTotal = Number(m[1]);
      else if (rangeless) {
        const len = Number(res.headers.get("content-length"));
        if (len > 0) encTotal = len;
      }
      if (!res.body) throw new Error("Download stream response body is unavailable.");

      const reader = res.body.getReader();
      let buf = new Uint8Array(encPartSize * 2);
      let bufLen = 0;
      while (true) {
        const { done, value } = await readChunkWithStallTimeout(reader, controller);
        if (done) break;
        if (!value?.length) continue;
        if (bufLen + value.length > buf.length) {
          const grown = new Uint8Array(Math.max(buf.length * 2, bufLen + value.length));
          grown.set(buf.subarray(0, bufLen));
          buf = grown;
        }
        buf.set(value, bufLen);
        bufLen += value.length;
        while (nextPart <= totalParts() && bufLen >= partLen(nextPart)) {
          const len = partLen(nextPart);
          const plain = await decryptChunk(fileKey, buf.slice(0, len), baseNonce, nextPart);
          await onPart(plain);
          buf.copyWithin(0, len, bufLen);
          bufLen -= len;
          nextPart++;
          attempt = 0;
          onProgress?.(Math.min(encTotal, (nextPart - 1) * encPartSize), encTotal);
        }
      }
      if (bufLen > 0 && rangeless && nextPart <= totalParts()) {
        // Size metadata was off; the stream is authoritative, so treat the rest as the final part
        await onPart(await decryptChunk(fileKey, buf.slice(0, bufLen), baseNonce, nextPart));
        return;
      }
      if (rangeless) return;
      if ((nextPart - 1) * encPartSize <= end && nextPart <= totalParts()) {
        throw new Error("Connection closed before the requested data arrived.");
      }
    } catch (err: any) {
      if (signal?.aborted || err?.name === "AbortError" || err instanceof FatalDownloadError) throw err;
      if (err?.name === "OperationError") {
        throw new Error("Could not decrypt this file (the data or key is corrupted).");
      }
      if (/\(4\d\d\)|refused access|not found/i.test(err?.message || "") || ++attempt > maxRetries) throw err;
      await sleep(Math.min(15_000, 1000 * 2 ** (attempt - 1)));
    }
  }
}

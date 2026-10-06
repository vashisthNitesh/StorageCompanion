import { apiFetch } from "./index";

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
  opts: { signal?: AbortSignal; directTimeoutMs?: number; proxyTimeoutMs?: number; skipDirect?: boolean } = {}
): Promise<OpenedStream> {
  const { signal, directTimeoutMs = 10_000, proxyTimeoutMs = 45_000, skipDirect = false } = opts;

  if (!skipDirect && isUsableDirectUrl(src.direct_url)) {
    const controller = linkedController(signal);
    const timer = setTimeout(() => controller.abort(), directTimeoutMs);
    try {
      const res = await fetch(src.direct_url as string, { method: "GET", signal: controller.signal });
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
    res = await apiFetch(src.download_url, { signal: controller.signal });
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

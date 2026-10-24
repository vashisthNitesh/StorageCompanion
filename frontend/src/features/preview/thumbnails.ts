// Thumbnails for the file grid and list. Files are encrypted, so thumbnails are made
// in the browser: images are decoded and scaled, videos are streamed to a hidden
// player and a frame is captured, PDFs render their first page. Results are kept
// in memory and in IndexedDB, encrypted with a key derived from the vault key.

import { useAuthStore } from "../../stores/auth";
import { openEncryptedFile } from "../../lib/crypto/encryptedFile";
import { createStreamUrl, ensureStreamWorker } from "../../lib/mediaStream";
import { openPdf } from "../../lib/pdf";
import { likelyUnsupported, mimeOf, previewKindOf } from "./previewTypes";

export interface Thumbnail {
  url: string;
  /** Seconds, for videos. */
  duration?: number;
}

interface ThumbNode {
  id: string;
  type: string;
  name: string;
  size_bytes: number;
  updated_at: string;
}

const MAX_EDGE = 480;
const MAX_IMAGE_BYTES = 50 * 1024 * 1024;
const MAX_PDF_BYTES = 50 * 1024 * 1024;
const CONCURRENCY = 2;

export function canThumbnail(node: { type: string; name: string; size_bytes: number }): boolean {
  const kind = previewKindOf(node);
  if (kind === "image") return node.size_bytes <= MAX_IMAGE_BYTES && !likelyUnsupported(kind, node.name);
  if (kind === "video") return "serviceWorker" in navigator;
  if (kind === "pdf") return node.size_bytes <= MAX_PDF_BYTES;
  return false;
}

/* ---------- scheduling: a few at a time, most recently requested first ---------- */

let active = 0;
const waiting: (() => void)[] = [];
async function slot<T>(fn: () => Promise<T>): Promise<T> {
  if (active >= CONCURRENCY) await new Promise<void>((resolve) => waiting.push(resolve));
  active++;
  try {
    return await fn();
  } finally {
    active--;
    waiting.pop()?.();
  }
}

/* ---------- encrypted IndexedDB cache ---------- */

interface Stored {
  iv?: Uint8Array;
  data?: ArrayBuffer;
  type?: string;
  duration?: number;
  /** The file can't be thumbnailed (undecodable); don't retry. */
  none?: boolean;
}

let dbPromise: Promise<IDBDatabase | null> | null = null;
function db(): Promise<IDBDatabase | null> {
  dbPromise ??= new Promise((resolve) => {
    try {
      const req = indexedDB.open("sc-thumbnails", 1);
      req.onupgradeneeded = () => req.result.createObjectStore("thumbs");
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
  return dbPromise;
}

async function idb<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest): Promise<T | undefined> {
  const d = await db();
  if (!d) return undefined;
  return new Promise((resolve) => {
    try {
      const req = run(d.transaction("thumbs", mode).objectStore("thumbs"));
      req.onsuccess = () => resolve(req.result as T);
      req.onerror = () => resolve(undefined);
    } catch {
      resolve(undefined);
    }
  });
}

let cacheKey: { master: Uint8Array; key: Promise<CryptoKey> } | null = null;
function cacheCryptoKey(master: Uint8Array): Promise<CryptoKey> {
  if (cacheKey?.master !== master) {
    const key = crypto.subtle
      .importKey("raw", master, "HKDF", false, ["deriveKey"])
      .then((base) =>
        crypto.subtle.deriveKey(
          { name: "HKDF", hash: "SHA-256", salt: new Uint8Array(0), info: new TextEncoder().encode("smartspace/thumbnails/v1") },
          base,
          { name: "AES-GCM", length: 256 },
          false,
          ["encrypt", "decrypt"]
        )
      );
    cacheKey = { master, key };
  }
  return cacheKey.key;
}

/* ---------- generation ---------- */

/** The file decoded but couldn't be drawn: remember that, unlike network errors. */
class Undecodable extends Error {}

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return Promise.race([p, new Promise<T>((_, reject) => setTimeout(() => reject(new Undecodable("timeout")), ms))]);
}

function scaledCanvas(width: number, height: number) {
  const scale = Math.min(1, MAX_EDGE / Math.max(width, height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  return canvas;
}

function toBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Undecodable())), "image/webp", 0.82));
}

async function imageThumb(node: ThumbNode, master: Uint8Array): Promise<{ blob: Blob }> {
  const file = await openEncryptedFile(node, master, "thumbnail");
  const bytes = await file.read(0, file.size);
  const url = URL.createObjectURL(new Blob([bytes as BlobPart], { type: mimeOf(node.name) }));
  try {
    const img = new Image();
    img.src = url;
    await withTimeout(img.decode(), 20_000).catch(() => {
      throw new Undecodable();
    });
    const canvas = scaledCanvas(img.naturalWidth || MAX_EDGE, img.naturalHeight || MAX_EDGE);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    return { blob: await toBlob(canvas) };
  } finally {
    URL.revokeObjectURL(url);
  }
}

function once(el: HTMLMediaElement, event: string): Promise<void> {
  return new Promise((resolve, reject) => {
    el.addEventListener(event, () => resolve(), { once: true });
    el.addEventListener("error", () => reject(new Undecodable()), { once: true });
  });
}

async function videoThumb(node: ThumbNode, master: Uint8Array): Promise<{ blob: Blob; duration: number }> {
  if (!(await ensureStreamWorker())) throw new Error("no_stream_worker");
  const file = await openEncryptedFile(node, master, "thumbnail");
  const stream = createStreamUrl(file, mimeOf(node.name), node.name);
  const video = document.createElement("video");
  try {
    video.muted = true;
    video.playsInline = true;
    video.preload = "metadata";
    video.src = stream.url;
    await withTimeout(once(video, "loadedmetadata"), 30_000);
    const duration = Number.isFinite(video.duration) ? video.duration : 0;
    video.currentTime = duration ? Math.min(1, duration * 0.1) : 0;
    await withTimeout(once(video, "seeked"), 30_000);
    if (!video.videoWidth) throw new Undecodable();
    const canvas = scaledCanvas(video.videoWidth, video.videoHeight);
    canvas.getContext("2d")!.drawImage(video, 0, 0, canvas.width, canvas.height);
    return { blob: await toBlob(canvas), duration };
  } finally {
    video.removeAttribute("src");
    video.load();
    stream.release();
  }
}

async function pdfThumb(node: ThumbNode, master: Uint8Array): Promise<{ blob: Blob }> {
  const file = await openEncryptedFile(node, master, "thumbnail");
  const bytes = await file.read(0, file.size);
  const doc = await openPdf(bytes).catch(() => {
    throw new Undecodable();
  });
  try {
    const page = await doc.getPage(1);
    const base = page.getViewport({ scale: 1 });
    const canvas = scaledCanvas(base.width, base.height);
    const viewport = page.getViewport({ scale: canvas.width / base.width });
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    await page.render({ canvasContext: ctx, viewport }).promise;
    return { blob: await toBlob(canvas) };
  } finally {
    void doc.destroy();
  }
}

/* ---------- public API ---------- */

const memory = new Map<string, Promise<Thumbnail | null>>();

async function load(node: ThumbNode, master: Uint8Array, key: string): Promise<Thumbnail | null> {
  const aes = await cacheCryptoKey(master);
  const stored = await idb<Stored>("readonly", (s) => s.get(key));
  if (stored?.none) return null;
  if (stored?.iv && stored.data) {
    try {
      const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: stored.iv as BufferSource }, aes, stored.data);
      return { url: URL.createObjectURL(new Blob([plain], { type: stored.type })), duration: stored.duration };
    } catch {
      // Stale entry from another vault key; regenerate.
    }
  }

  return slot(async () => {
    const kind = previewKindOf(node);
    try {
      const made: { blob: Blob; duration?: number } =
        kind === "video" ? await videoThumb(node, master) : kind === "pdf" ? await pdfThumb(node, master) : await imageThumb(node, master);
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const data = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, aes, await made.blob.arrayBuffer());
      const duration = made.duration;
      void idb("readwrite", (s) => s.put({ iv, data, type: made.blob.type, duration } satisfies Stored, key));
      return { url: URL.createObjectURL(made.blob), duration };
    } catch (err) {
      if (err instanceof Undecodable) void idb("readwrite", (s) => s.put({ none: true } satisfies Stored, key));
      else memory.delete(key); // network, busy server, etc.: try again the next time it's shown
      return null;
    }
  });
}

/** Thumbnail for a file, or null when there isn't one. Never throws. */
export function getThumbnail(node: ThumbNode): Promise<Thumbnail | null> {
  const auth = useAuthStore();
  const master = auth.masterKey;
  if (!master || !canThumbnail(node)) return Promise.resolve(null);
  const key = `${auth.user?.id ?? ""}:${node.id}:${node.updated_at}`;
  let p = memory.get(key);
  if (!p) {
    p = load(node, master, key).catch(() => null);
    memory.set(key, p);
  }
  return p;
}

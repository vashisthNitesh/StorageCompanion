// Page side of public/preview-sw.js: registers decrypted streams and answers the
// worker's byte-range requests, so <video>/<audio> can play and seek encrypted files
// without downloading them first.

import type { EncryptedFile } from "./crypto/encryptedFile";

const streams = new Map<string, { file: EncryptedFile; type: string }>();
let ready: Promise<boolean> | null = null;

function onMessage(e: MessageEvent) {
  const port = e.ports[0];
  const msg = e.data;
  if (!port || typeof msg?.type !== "string" || !msg.type.startsWith("stream-")) return;
  const stream = streams.get(msg.id);
  if (!stream) return port.postMessage({ error: "unknown" });
  if (msg.type === "stream-meta") return port.postMessage({ size: stream.file.size, type: stream.type });
  stream.file.read(msg.start, msg.end).then(
    (bytes) => {
      const buffer = bytes.buffer.byteLength === bytes.byteLength ? bytes.buffer : bytes.slice().buffer;
      port.postMessage({ bytes: buffer }, [buffer as ArrayBuffer]);
    },
    () => port.postMessage({ error: "read" })
  );
}

/** Resolves true once the streaming worker controls this page. */
export function ensureStreamWorker(): Promise<boolean> {
  ready ??= (async () => {
    if (!("serviceWorker" in navigator) || !window.isSecureContext) return false;
    try {
      navigator.serviceWorker.addEventListener("message", onMessage);
      navigator.serviceWorker.startMessages();
      await navigator.serviceWorker.register("/preview-sw.js", { scope: "/" });
      await navigator.serviceWorker.ready;
      if (!navigator.serviceWorker.controller) {
        await new Promise<void>((resolve) => {
          const timer = setTimeout(resolve, 3000);
          navigator.serviceWorker.addEventListener("controllerchange", () => (clearTimeout(timer), resolve()), { once: true });
        });
      }
      return !!navigator.serviceWorker.controller;
    } catch {
      return false;
    }
  })();
  return ready;
}

/** A same-origin URL that streams `file`. Call release() when the player closes. */
export function createStreamUrl(file: EncryptedFile, type: string, name: string) {
  const id = crypto.randomUUID();
  streams.set(id, { file, type });
  return { url: `/__stream/${id}/${encodeURIComponent(name)}`, release: () => streams.delete(id) };
}

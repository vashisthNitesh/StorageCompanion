// Streams decrypted files to <video> and <audio> with seeking support.
//
// The worker holds no keys and does no crypto. A media element requests
// /__stream/<id>/<name>; the worker asks the page that registered <id> for the
// plaintext bytes of each range and pipes them back. Every other request is left
// untouched.

const PREFIX = "/__stream/";
const CHUNK = 2 * 1024 * 1024;
const TIMEOUT_MS = 60000;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(PREFIX)) return;
  event.respondWith(serve(event, url));
});

function ask(client, message) {
  return new Promise((resolve, reject) => {
    const channel = new MessageChannel();
    const timer = setTimeout(() => reject(new Error("timeout")), TIMEOUT_MS);
    channel.port1.onmessage = (e) => {
      clearTimeout(timer);
      if (e.data && e.data.error) reject(new Error(e.data.error));
      else resolve(e.data);
    };
    client.postMessage(message, [channel.port2]);
  });
}

async function owner(event, id) {
  const own = event.clientId ? await self.clients.get(event.clientId) : null;
  const candidates = own ? [own] : await self.clients.matchAll({ type: "window" });
  for (const client of candidates) {
    try {
      return { client, meta: await ask(client, { type: "stream-meta", id }) };
    } catch {
      // Not this window's stream.
    }
  }
  return null;
}

async function serve(event, url) {
  const id = url.pathname.slice(PREFIX.length).split("/")[0];
  const found = await owner(event, id);
  if (!found) return new Response(null, { status: 404 });
  const { client, meta } = found;
  const size = meta.size;
  const headers = { "Content-Type": meta.type || "application/octet-stream", "Accept-Ranges": "bytes", "Cache-Control": "no-store" };

  let start = 0;
  let end = size - 1;
  const range = event.request.headers.get("range");
  const match = range && /^bytes=(\d*)-(\d*)$/.exec(range.trim());
  if (match) {
    if (match[1] === "") start = Math.max(0, size - Number(match[2]));
    else {
      start = Number(match[1]);
      if (match[2] !== "") end = Math.min(Number(match[2]), size - 1);
    }
    if (start >= size || start > end) return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
  }
  if (size === 0) return new Response(new Uint8Array(0), { status: 200, headers: { ...headers, "Content-Length": "0" } });

  let pos = start;
  const body = new ReadableStream({
    async pull(controller) {
      const to = Math.min(end + 1, pos + CHUNK);
      try {
        const { bytes } = await ask(client, { type: "stream-read", id, start: pos, end: to });
        controller.enqueue(new Uint8Array(bytes));
        pos = to;
        if (pos > end) controller.close();
      } catch (err) {
        controller.error(err);
      }
    },
  });

  headers["Content-Length"] = String(end - start + 1);
  if (!match) return new Response(body, { status: 200, headers });
  headers["Content-Range"] = `bytes ${start}-${end}/${size}`;
  return new Response(body, { status: 206, headers });
}

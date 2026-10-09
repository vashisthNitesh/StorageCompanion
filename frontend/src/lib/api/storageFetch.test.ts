import { describe, it, expect, vi, beforeEach } from "vitest";

const apiFetchMock = vi.fn();
vi.mock("./index", () => ({ apiFetch: (...a: any[]) => apiFetchMock(...a) }));

import { downloadDecryptRanged } from "./storageFetch";
import { encryptChunk } from "../crypto/content";

const PART = 64; // tiny part size so the test is fast
const key = new Uint8Array(32).fill(7);
const nonce = new Uint8Array(12).fill(1);

async function makeFile(plain: Uint8Array) {
  const parts: Uint8Array[] = [];
  const n = Math.max(1, Math.ceil(plain.length / PART));
  for (let i = 0; i < n; i++) parts.push(await encryptChunk(key, plain.slice(i * PART, (i + 1) * PART), nonce, i + 1));
  const enc = new Uint8Array(parts.reduce((a, p) => a + p.length, 0));
  let o = 0;
  for (const p of parts) { enc.set(p, o); o += p.length; }
  return enc;
}

function streamOf(bytes: Uint8Array, failAfter?: number) {
  let sent = 0;
  return new ReadableStream<Uint8Array>({
    pull(ctrl) {
      if (failAfter !== undefined && sent >= failAfter) { ctrl.error(new TypeError("network error")); return; }
      const step = Math.min(50, bytes.length - sent, failAfter !== undefined ? failAfter - sent : Infinity);
      if (step <= 0) { ctrl.close(); return; }
      ctrl.enqueue(bytes.slice(sent, sent + step));
      sent += step;
    },
  });
}

function rangeServer(enc: Uint8Array, opts: { dropFirstAt?: number; ignoreRange?: boolean } = {}) {
  let dropped = false;
  return async (_url: string, init: any) => {
    const range = init?.headers?.Range as string | undefined;
    if (opts.ignoreRange || !range) {
      return new Response(streamOf(enc), { status: 200, headers: { "Content-Length": String(enc.length) } });
    }
    const [s, e] = range.replace("bytes=", "").split("-").map(Number);
    const slice = enc.slice(s, Math.min(e + 1, enc.length));
    const fail = !dropped && opts.dropFirstAt !== undefined ? opts.dropFirstAt : undefined;
    if (fail !== undefined) dropped = true;
    return new Response(streamOf(slice, fail), {
      status: 206,
      headers: { "Content-Range": `bytes ${s}-${s + slice.length - 1}/${enc.length}` },
    });
  };
}

async function run(plain: Uint8Array, server: any, plainSize = plain.length) {
  apiFetchMock.mockImplementation(server);
  const out: Uint8Array[] = [];
  await downloadDecryptRanged({ download_url: "/api/v1/nodes/x/content" }, {
    fileKey: key, baseNonce: nonce, partSize: PART, plainSize, partsPerRequest: 3,
    onPart: (p) => { out.push(p); }, maxRetries: 3,
  });
  return new Uint8Array(out.flatMap((p) => Array.from(p)));
}

describe("downloadDecryptRanged", () => {
  beforeEach(() => { apiFetchMock.mockReset(); vi.useRealTimers(); });
  const plain = new Uint8Array(64 * 10 + 17).map((_, i) => (i * 31) % 251);

  it("downloads in ranged windows and decrypts in order", async () => {
    const enc = await makeFile(plain);
    expect(await run(plain, rangeServer(enc))).toEqual(plain);
    const ranges = apiFetchMock.mock.calls.map((c) => c[1].headers.Range);
    expect(ranges[0]).toBe("bytes=0-239");
    expect(ranges.length).toBe(4); // 11 parts / 3 per request
  });

  it("resumes from the next undecrypted part after a dropped connection", async () => {
    const enc = await makeFile(plain);
    expect(await run(plain, rangeServer(enc, { dropFirstAt: 100 }))).toEqual(plain);
    const ranges = apiFetchMock.mock.calls.map((c) => c[1].headers.Range);
    expect(ranges[1]).toBe("bytes=80-319"); // part 1 (80 bytes) done, resumed at part 2
  });

  it("falls back to the single stream when Range is ignored", async () => {
    const enc = await makeFile(plain);
    expect(await run(plain, rangeServer(enc, { ignoreRange: true }))).toEqual(plain);
  });

  it("uses the server's Content-Range total when metadata size is wrong", async () => {
    const enc = await makeFile(plain);
    expect(await run(plain, rangeServer(enc), 5)).toEqual(plain);
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { generateMasterKey, generateFileKey, wrapKey, generateRandomBytes } from "../keys";
import { encryptChunk } from "../content";
import { uint8ArrayToHex } from "../kdf";

// Fake storage: the encrypted bytes, served with or without HTTP range support.
let encrypted = new Uint8Array(0);
let honourRanges = true;
const requested: string[] = [];
let info: Record<string, unknown> = {};

const fakeFetch = vi.fn(async (_url: string, init: RequestInit = {}) => {
    const range = new Headers(init.headers).get("Range");
    requested.push(range ?? "full");
    if (range && honourRanges) {
      const [, a, b] = /bytes=(\d+)-(\d+)/.exec(range)!;
      return new Response(encrypted.slice(+a, +b + 1), { status: 206 });
    }
    return new Response(encrypted, { status: 200 });
});

vi.mock("../../api", () => ({
  apiRequest: vi.fn(async () => info),
  apiFetch: fakeFetch,
  apiFetchRetrying: fakeFetch,
  errorFromResponse: vi.fn(),
}));

const { openEncryptedFile, DecryptError } = await import("../encryptedFile");

const PART = 1024;
async function setup(size: number) {
  const master = generateMasterKey();
  const fileKey = generateFileKey();
  const nonce = generateRandomBytes(12);
  const plain = generateRandomBytes(size);
  const parts: Uint8Array[] = [];
  for (let n = 1; n <= Math.max(1, Math.ceil(size / PART)); n++) {
    parts.push(await encryptChunk(fileKey, plain.subarray((n - 1) * PART, n * PART), nonce, n));
  }
  encrypted = new Uint8Array(parts.reduce((s, p) => s + p.length, 0));
  let o = 0;
  for (const p of parts) {
    encrypted.set(p, o);
    o += p.length;
  }
  info = {
    download_url: "/content",
    wrapped_file_key: await wrapKey(master, fileKey),
    content_nonce: uint8ArrayToHex(nonce),
    size_bytes: size,
    part_size: PART,
  };
  return { master, plain };
}

describe("openEncryptedFile", () => {
  beforeEach(() => {
    honourRanges = true;
    requested.length = 0;
  });

  it("reads byte ranges that span part boundaries, fetching only the parts needed", async () => {
    const { master, plain } = await setup(5000);
    const file = await openEncryptedFile({ id: "n1" }, master, "preview");
    expect(file.size).toBe(5000);
    expect(await file.read(1000, 2100)).toEqual(plain.slice(1000, 2100));
    // Parts 1–3 cover bytes 1000–2099; part 4 is read ahead. Part 5 is never fetched.
    expect(requested).toEqual(expect.arrayContaining(["bytes=0-1039", "bytes=1040-2079", "bytes=2080-3119"]));
    expect(requested).not.toContain("bytes=4160-4919");
    expect(await file.read(4990, 9999)).toEqual(plain.slice(4990));
  });

  it("falls back to fetching the whole file when storage ignores ranges", async () => {
    honourRanges = false;
    const { master, plain } = await setup(3000);
    const file = await openEncryptedFile({ id: "n2" }, master, "preview");
    expect(await file.read(0, 3000)).toEqual(plain);
  });

  it("decrypts the whole file with progress", async () => {
    const { master, plain } = await setup(2500);
    const file = await openEncryptedFile({ id: "n3" }, master, "preview");
    const seen: number[] = [];
    const blob = await file.readAll((f) => seen.push(f));
    expect(new Uint8Array(await blob.arrayBuffer())).toEqual(plain);
    expect(seen.at(-1)).toBe(1);
  });

  it("reports tampered data as a decrypt error", async () => {
    const { master } = await setup(2000);
    encrypted[10] ^= 1;
    const file = await openEncryptedFile({ id: "n4" }, master, "preview");
    await expect(file.read(0, 10)).rejects.toBeInstanceOf(DecryptError);
  });
});

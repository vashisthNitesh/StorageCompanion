import { describe, it, expect, vi, afterEach } from "vitest";
import { apiFetchRetrying } from "../api";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function respondWith(...replies: (Response | Error)[]) {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      calls.push(url);
      const next = replies.shift()!;
      if (next instanceof Error) throw next;
      return next;
    })
  );
  return calls;
}

describe("apiFetchRetrying", () => {
  it("waits for Retry-After while the server is busy, then succeeds", async () => {
    vi.useFakeTimers();
    const calls = respondWith(
      new Response("{}", { status: 503, headers: { "Retry-After": "3" } }),
      new Response("ok", { status: 200 })
    );
    const pending = apiFetchRetrying("/api/v1/nodes/x/content");
    await vi.advanceTimersByTimeAsync(2000);
    expect(calls).toHaveLength(1); // still honouring Retry-After (3 s ± 20%)
    await vi.advanceTimersByTimeAsync(2000);
    const res = await pending;
    expect(res.status).toBe(200);
    expect(calls).toHaveLength(2);
  });

  it("retries network failures", async () => {
    vi.useFakeTimers();
    respondWith(new TypeError("Failed to fetch"), new Response("ok", { status: 200 }));
    const pending = apiFetchRetrying("/api/v1/nodes/x/content");
    await vi.advanceTimersByTimeAsync(2000);
    expect((await pending).status).toBe(200);
  });

  it("returns definitive answers straight away and gives up after the last attempt", async () => {
    respondWith(new Response("{}", { status: 404 }));
    expect((await apiFetchRetrying("/a")).status).toBe(404);

    vi.useFakeTimers();
    const calls = respondWith(...Array.from({ length: 3 }, () => new Response("{}", { status: 503 })));
    const pending = apiFetchRetrying("/b", {}, 3);
    await vi.advanceTimersByTimeAsync(10_000);
    expect((await pending).status).toBe(503);
    expect(calls).toHaveLength(3);
  });
});

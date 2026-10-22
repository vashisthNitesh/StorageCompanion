import { describe, expect, it } from "vitest";
import { ApiError } from "../api";
import { COPY, normalizeApiError } from "../errors";

const http = (status: number, data: any = {}) => new ApiError(`HTTP ${status}`, status, data);

describe("normalizeApiError", () => {
  it("maps field errors and keeps a human form-level message", () => {
    const n = normalizeApiError(
      http(400, { success: false, error: "email: Enter a valid email address.", details: { email: ["Enter a valid email address."] } })
    );
    expect(n.kind).toBe("validation");
    expect(n.fieldErrors).toEqual({ email: "Enter a valid email address." });
    expect(n.message).not.toContain("email:");
  });

  it("uses curated 400 messages but never raw blobs", () => {
    expect(normalizeApiError(http(400, { error: "Invalid email or password." })).message).toBe("Invalid email or password.");
    expect(normalizeApiError(http(400, { error: "{'detail': 'x'}" })).message).toBe(COPY.validation);
    expect(normalizeApiError(http(400, { error: "<html>Bad Request</html>" })).message).toBe(COPY.validation);
  });

  it("reads DRF list-shaped errors", () => {
    const n = normalizeApiError(http(400, ["Could not start the payment. Please try again."]));
    expect(n.message).toBe("Could not start the payment. Please try again.");
    expect(n.fieldErrors).toEqual({});
  });

  it.each([
    [401, COPY.session],
    [403, COPY.forbidden],
    [404, COPY.notFound],
    [409, COPY.conflict],
    [429, COPY.rateLimited],
    [500, COPY.generic],
    [502, COPY.generic],
  ])("maps HTTP %s", (status, message) => {
    expect(normalizeApiError(http(status, { error: "Traceback (most recent call last)" })).message).toBe(message);
  });

  it("keeps our lockout wording but not DRF's throttle text", () => {
    expect(normalizeApiError(http(429, { error: "Too many failed sign-in attempts. Please wait 15 minutes and try again." })).message).toContain("15 minutes");
    expect(normalizeApiError(http(429, { error: "Request was throttled. Expected available in 42 seconds." })).message).toBe(COPY.rateLimited);
  });

  it("maps plan and size codes", () => {
    expect(normalizeApiError(http(402, { code: "SUBSCRIPTION_REQUIRED" })).kind).toBe("plan_required");
    expect(normalizeApiError(http(413, { code: "QUOTA_EXCEEDED" })).kind).toBe("quota");
    const big = normalizeApiError(http(413, { code: "FILE_TOO_LARGE", message: "This file is larger than your plan's 25 GB per-file limit." }));
    expect(big.kind).toBe("too_large");
    expect(big.message).toBe("This file is larger than your plan allows (max 25 GB per file).");
  });

  it("maps network failures and unknown errors to generic copy", () => {
    expect(normalizeApiError(new ApiError("network", 0, {}, "network")).message).toBe(COPY.network);
    expect(normalizeApiError(new ApiError("timeout", 0, {}, "timeout")).message).toBe(COPY.generic);
    expect(normalizeApiError(new TypeError("Cannot read properties of undefined")).message).toBe(COPY.generic);
  });
});

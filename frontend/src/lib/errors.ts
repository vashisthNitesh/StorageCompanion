import { ApiError } from "./api";

export type ErrorKind =
  | "validation"
  | "auth"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "too_large"
  | "quota"
  | "plan_required"
  | "rate_limited"
  | "unavailable"
  | "server"
  | "network"
  | "unknown";

export interface NormalizedError {
  kind: ErrorKind;
  status: number;
  code?: string;
  /** Human copy, safe to show as-is. */
  message: string;
  /** Field name → message, for inline errors under inputs. */
  fieldErrors: Record<string, string>;
  /** Whether offering "Retry" makes sense. */
  retryable: boolean;
  /** Plan per-file limit in GB, when the server told us. */
  maxFileSizeGb?: number;
}

export const COPY = {
  generic: "Something went wrong on our side. Please try again.",
  network: "We couldn't reach SmartSpace. Check your connection and try again.",
  session: "Your session expired. Please sign in again.",
  forbidden: "You don't have access to this.",
  notFound: "This item no longer exists.",
  conflict: "A file with this name already exists here.",
  staleConflict: "This changed since you opened it. Refresh and try again.",
  tooLarge: "This file is larger than your plan allows.",
  rateLimited: "Too many attempts. Try again in a minute.",
  validation: "Please check the highlighted fields and try again.",
  planRequired: "Choose a plan to start uploading files.",
  planEnded: "Your plan has ended. Renew it to upload new files.",
  quota: "You've run out of storage on your plan. Upgrade to upload more.",
  poolFull: "We're temporarily out of storage capacity. Please try again later.",
  unavailable: "This isn't available right now. Please try again later.",
} as const;

/** A server message is only shown if it reads like a sentence written for people. */
function isHumanText(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.length > 3 &&
    value.length < 220 &&
    !/[<>{}[\]]|Traceback|Exception|HTTP \d|^\w+_\w+$|object Object|undefined|null/i.test(value)
  );
}

function firstString(value: unknown): string | undefined {
  if (Array.isArray(value)) return firstString(value[0]);
  if (typeof value === "string") return value;
  return undefined;
}

function extractFieldErrors(data: any): Record<string, string> {
  if (Array.isArray(data)) return {};
  const details = data?.details && typeof data.details === "object" && !Array.isArray(data.details) ? data.details : data;
  const out: Record<string, string> = {};
  if (!details || typeof details !== "object") return out;
  for (const [key, value] of Object.entries(details)) {
    if (["error", "message", "detail", "code", "success", "status_code", "non_field_errors"].includes(key)) continue;
    const msg = firstString(value);
    if (msg && isHumanText(msg)) out[key] = msg;
  }
  return out;
}

export function normalizeApiError(err: unknown): NormalizedError {
  if (!(err instanceof ApiError)) {
    // Programming or browser errors (e.g. decryption failures) never surface their text.
    return { kind: "unknown", status: 0, message: COPY.generic, fieldErrors: {}, retryable: true };
  }

  const { status, data, reason } = err;
  // Not-found, conflict and too-large copy talks about files only where the request was about files.
  const aboutFiles = /\/api\/v1\/(nodes|uploads|files)\b/.test(err.path ?? "");
  const code: string | undefined = typeof data?.code === "string" ? data.code : undefined;
  const base = { status, code, fieldErrors: {} as Record<string, string> };

  if (status === 0) {
    return { ...base, kind: "network", message: reason === "timeout" ? COPY.generic : COPY.network, retryable: true };
  }
  if (code === "SUBSCRIPTION_REQUIRED") return { ...base, kind: "plan_required", message: COPY.planRequired, retryable: false };
  if (code === "ACCOUNT_IN_GRACE_PERIOD") return { ...base, kind: "plan_required", message: COPY.planEnded, retryable: false };
  if (code === "QUOTA_EXCEEDED") return { ...base, kind: "quota", message: COPY.quota, retryable: false };
  if (code === "STORAGE_POOL_LIMIT_EXCEEDED") return { ...base, kind: "unavailable", message: COPY.poolFull, retryable: true };
  if (code === "FILE_TOO_LARGE") {
    const gb = Number(String(data?.message ?? "").match(/(\d+)\s*GB/)?.[1]) || undefined;
    return {
      ...base,
      kind: "too_large",
      maxFileSizeGb: gb,
      message: gb ? `This file is larger than your plan allows (max ${gb} GB per file).` : COPY.tooLarge,
      retryable: false,
    };
  }

  switch (true) {
    case status === 400 || status === 422: {
      const fieldErrors = extractFieldErrors(data);
      // DRF sometimes returns a bare list of messages (e.g. raise ValidationError("…")).
      const top = Array.isArray(data)
        ? firstString(data)
        : data?.error ?? data?.message ?? firstString(data?.details?.non_field_errors) ?? data?.detail;
      // The backend also copies the first field error into `error` as "field: message";
      // when field errors exist that duplicate belongs under the field, not in a banner.
      const duplicatesField = typeof top === "string" && Object.values(fieldErrors).some((m) => top.includes(m));
      const message = Object.keys(fieldErrors).length
        ? isHumanText(top) && !duplicatesField
          ? top
          : COPY.validation
        : isHumanText(top)
          ? top
          : COPY.validation;
      return { ...base, kind: "validation", message, fieldErrors, retryable: false };
    }
    case status === 401:
      return { ...base, kind: "auth", message: COPY.session, retryable: false };
    case status === 402:
      return { ...base, kind: "plan_required", message: COPY.planRequired, retryable: false };
    case status === 403:
      return { ...base, kind: "forbidden", message: COPY.forbidden, retryable: false };
    case status === 404:
      return { ...base, kind: "not_found", message: aboutFiles ? COPY.notFound : COPY.unavailable, retryable: !aboutFiles };
    case status === 409:
      return { ...base, kind: "conflict", message: aboutFiles ? COPY.conflict : COPY.staleConflict, retryable: false };
    case status === 413:
      return { ...base, kind: "too_large", message: aboutFiles ? COPY.tooLarge : COPY.generic, retryable: false };
    case status === 429: {
      // Our lockout message says how long to wait; DRF's generic "Request was throttled…" doesn't read well.
      const server = data?.error ?? data?.detail;
      const message = isHumanText(server) && !/throttled/i.test(server) ? server : COPY.rateLimited;
      return { ...base, kind: "rate_limited", message, retryable: true };
    }
    case status === 503:
      return { ...base, kind: "unavailable", message: COPY.unavailable, retryable: true };
    case status >= 500:
      return { ...base, kind: "server", message: COPY.generic, retryable: true };
    default:
      return { ...base, kind: "unknown", message: COPY.generic, retryable: true };
  }
}

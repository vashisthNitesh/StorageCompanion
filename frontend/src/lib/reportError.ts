import { normalizeApiError, type NormalizedError } from "./errors";
import { toast } from "./toast";
import { emitAppEvent } from "./events";

/**
 * Shows an error the designed way: plan/quota problems open the plan picker, 404s ask the
 * caller to refresh, everything else becomes a toast (with Retry when it makes sense).
 */
export function reportError(err: unknown, opts: { retry?: () => void; context?: string } = {}): NormalizedError {
  const n = normalizeApiError(err);
  if (n.kind === "auth") return n; // the API client already redirects to sign-in
  if (n.kind === "plan_required" || n.kind === "quota") {
    emitAppEvent("plan-picker", { reason: n.message });
    return n;
  }
  if (n.kind === "too_large") {
    toast.error(n.message, { action: { label: "Upgrade", onClick: () => emitAppEvent("plan-picker", { reason: n.message }) } });
    return n;
  }
  const message = opts.context ? `${opts.context} ${n.message}` : n.message;
  toast.error(message, { retry: n.retryable ? opts.retry : undefined });
  return n;
}

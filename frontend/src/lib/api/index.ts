// API client: attaches the access token, refreshes it once on 401, and gives every
// request a timeout so the UI never waits on a spinner forever.

const ACCESS_TOKEN_STORAGE_KEY = "sc_access_token";
const DEFAULT_TIMEOUT_MS = 30_000;

export type ApiFailureReason = "http" | "network" | "timeout";

export class ApiError extends Error {
  status: number;
  data: any;
  reason: ApiFailureReason;
  /** API path that failed (e.g. "/api/v1/nodes/…"), so error copy can fit the context. */
  path: string;
  constructor(message: string, status: number, data: any = {}, reason: ApiFailureReason = "http", path = "") {
    super(message);
    this.status = status;
    this.data = data;
    this.reason = reason;
    this.path = path;
  }
}

let accessToken: string | null =
  typeof window !== "undefined" && window.sessionStorage
    ? sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
    : null;

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (typeof window !== "undefined" && window.sessionStorage) {
    if (token) {
      sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
    } else {
      sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    }
  }
}

export function getAccessToken(): string | null {
  if (!accessToken && typeof window !== "undefined" && window.sessionStorage) {
    accessToken = sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  }
  return accessToken;
}

/** Called when the session can no longer be refreshed (signed out elsewhere, revoked, expired). */
let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

let refreshPromise: Promise<{ access_token: string; user?: any } | null> | null = null;

export async function refreshAccessToken(): Promise<{ access_token: string; user?: any } | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await fetchWithTimeout("/api/v1/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setAccessToken(data.access_token);
        return data;
      }
      setAccessToken(null);
      return null;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * fetch() with a timeout on receiving the response headers. The body of a long
 * download is not limited, only the wait for the server to start answering.
 */
async function fetchWithTimeout(input: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  if (!timeoutMs) return fetch(input, init);
  const controller = new AbortController();
  const outerSignal = init.signal;
  if (outerSignal) {
    if (outerSignal.aborted) controller.abort();
    else outerSignal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  const timer = setTimeout(() => controller.abort(new DOMException("timeout", "TimeoutError")), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (err: any) {
    if (controller.signal.aborted && !outerSignal?.aborted) {
      throw new ApiError("timeout", 0, {}, "timeout");
    }
    if (err?.name === "AbortError") throw err;
    throw new ApiError("network", 0, {}, "network");
  } finally {
    clearTimeout(timer);
  }
}

export interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number;
}

export async function apiFetch(endpoint: string, options: ApiFetchOptions = {}): Promise<Response> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...init } = options;
  const headers = new Headers(init.headers || {});
  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const config: RequestInit = { ...init, headers, credentials: "include" };
  let response = await fetchWithTimeout(endpoint, config, timeoutMs);

  if (response.status === 401 && !endpoint.includes("/auth/refresh") && !endpoint.includes("/auth/login")) {
    const refreshed = await refreshAccessToken();
    if (refreshed?.access_token) {
      headers.set("Authorization", `Bearer ${refreshed.access_token}`);
      response = await fetchWithTimeout(endpoint, { ...config, headers }, timeoutMs);
      // Even a freshly issued token was rejected: the session is no longer usable.
      if (response.status === 401) onSessionExpired?.();
    } else if (token) {
      onSessionExpired?.();
    }
  }

  return response;
}

/** Builds an ApiError from a failed response. Its message is NOT user copy; use normalizeApiError(). */
export async function errorFromResponse(response: Response): Promise<ApiError> {
  let data: any = {};
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  let path = "";
  try {
    path = new URL(response.url).pathname;
  } catch {
    // Synthetic responses have no URL.
  }
  return new ApiError(`HTTP ${response.status}`, response.status, data, "http", path);
}

export async function apiRequest<T = any>(endpoint: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await apiFetch(endpoint, { ...options, headers });
  if (!response.ok) throw await errorFromResponse(response);
  if (response.status === 204) return {} as T;
  return (await response.json()) as T;
}

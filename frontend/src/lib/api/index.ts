// API client with automated credential handling and refresh token retry
export interface ApiResponse<T = any> {
  data: T;
  status: number;
}

const ACCESS_TOKEN_STORAGE_KEY = "sc_access_token";

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

let refreshPromise: Promise<{ access_token: string; user?: any } | null> | null = null;

export async function refreshAccessToken(): Promise<{ access_token: string; user?: any } | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const refreshRes = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      let res = refreshRes;
      if (res.status === 401) {
        // Another tab may have just rotated the refresh cookie (rotation blacklists the old one);
        // retry once with whatever cookie the browser now holds.
        await new Promise((r) => setTimeout(r, 400));
        res = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
        });
      }
      if (res.ok) {
        const refreshData = await res.json();
        setAccessToken(refreshData.access_token);
        return refreshData;
      }
      if (res.status === 401 || res.status === 403) {
        setAccessToken(null);
      }
      return null;
    } catch {
      // Network blip: keep the current access token (it may still be valid) instead of
      // wiping it, which made every following upload part fail with 401.
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/** Seconds until the current access token expires (null if unknown). */
export function accessTokenSecondsLeft(): number | null {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp - Date.now() / 1000 : null;
  } catch {
    return null;
  }
}

/** Proactively refresh the access token when it expires within `marginSeconds`. */
export async function ensureFreshAccessToken(marginSeconds = 120): Promise<void> {
  const left = accessTokenSecondsLeft();
  if (left === null || left < marginSeconds) {
    await refreshAccessToken();
  }
}

export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(options.headers || {});
  const currentToken = getAccessToken();

  const isSameOrigin =
    endpoint.startsWith("/") ||
    (typeof window !== "undefined" && endpoint.startsWith(window.location.origin));

  // Attach Bearer token only for relative endpoints or same-origin API routes
  if (currentToken && isSameOrigin) {
    if (!headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${currentToken}`);
    }
  }

  const config: RequestInit = {
    ...options,
    headers,
    ...(isSameOrigin ? { credentials: "include" } : {}), // send httpOnly refresh cookie only to same origin
  };

  let response = await fetch(endpoint, config);

  // If 401 Unauthorized on internal endpoint and not already refreshing, attempt token refresh
  if (
    isSameOrigin &&
    response.status === 401 &&
    !endpoint.includes("/auth/refresh") &&
    !endpoint.includes("/auth/login") &&
    !endpoint.includes("/auth/register")
  ) {
    const refreshData = await refreshAccessToken();
    if (refreshData?.access_token) {
      headers.set("Authorization", `Bearer ${refreshData.access_token}`);
      // Retry original request
      response = await fetch(endpoint, { ...config, headers });
    }
  }

  return response;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await apiFetch(endpoint, { ...options, headers });

  if (!response.ok) {
    let errorData: any = {};
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText || `HTTP ${response.status}` };
    }
    const fallbackMessage =
      response.status === 502
        ? "Server temporary gateway error (502). Storage stream may be busy, please retry."
        : response.status === 504
        ? "Server gateway timeout (504). Transfer took too long."
        : `Request failed (${response.status})`;

    const pick = (v: any): string | null =>
      typeof v === "string" && v ? v : v && typeof v === "object" && typeof v.message === "string" ? v.message : null;
    const err: any = new Error(
      pick(errorData.error) || pick(errorData.message) || pick(errorData.detail) || fallbackMessage
    );
    err.status = response.status;
    err.data = errorData;
    throw err;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return await response.json();
}

/**
 * Fetches every page of a cursor-paginated DRF list (PAGE_SIZE is 50). Callers previously read
 * only `results` of the first page, so folders with more than 50 items silently lost the rest.
 * `next` links are absolute and may carry the wrong scheme/host behind the proxy, so they are
 * converted back to same-origin relative URLs.
 */
export async function apiRequestAllPages<T = any>(endpoint: string, maxPages = 200): Promise<T[]> {
  const all: T[] = [];
  let url: string | null = endpoint;
  for (let page = 0; url && page < maxPages; page++) {
    const res: any = await apiRequest<any>(url);
    if (Array.isArray(res)) return res as T[];
    all.push(...((res?.results as T[]) || []));
    if (!res?.next) break;
    try {
      const u = new URL(res.next, typeof window !== "undefined" ? window.location.origin : "http://localhost");
      url = u.pathname + u.search;
    } catch {
      url = null;
    }
  }
  return all;
}

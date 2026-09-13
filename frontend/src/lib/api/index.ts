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

      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        setAccessToken(refreshData.access_token);
        return refreshData;
      } else {
        setAccessToken(null);
        return null;
      }
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(options.headers || {});
  const currentToken = getAccessToken();

  // Attach Bearer token for relative endpoints or same-origin API routes
  if (currentToken && (endpoint.startsWith("/") || endpoint.includes("/api/"))) {
    if (!headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${currentToken}`);
    }
  }

  const config: RequestInit = {
    ...options,
    headers,
    credentials: "include", // send httpOnly refresh cookie
  };

  let response = await fetch(endpoint, config);

  // If 401 Unauthorized and not already refreshing, attempt token refresh
  if (response.status === 401 && !endpoint.includes("/auth/refresh") && !endpoint.includes("/auth/login")) {
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
      errorData = { detail: response.statusText };
    }
    const err: any = new Error(errorData.error || errorData.message || errorData.detail || "Request failed");
    err.status = response.status;
    err.data = errorData;
    throw err;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return await response.json();
}

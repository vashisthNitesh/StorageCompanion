// API client with automated credential handling and refresh token retry
export interface ApiResponse<T = any> {
  data: T;
  status: number;
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const config: RequestInit = {
    ...options,
    headers,
    credentials: "include", // send httpOnly refresh cookie
  };

  let response = await fetch(endpoint, config);

  // If 401 Unauthorized and not already refreshing, attempt token refresh
  if (response.status === 401 && !endpoint.includes("/auth/refresh") && !endpoint.includes("/auth/login")) {
    try {
      const refreshRes = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });

      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        setAccessToken(refreshData.access_token);
        headers.set("Authorization", `Bearer ${refreshData.access_token}`);
        // Retry original request
        response = await fetch(endpoint, { ...config, headers });
      } else {
        setAccessToken(null);
      }
    } catch {
      setAccessToken(null);
    }
  }

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

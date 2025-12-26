/**
 * Django API Client
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("auth_token", token);
    } else {
      localStorage.removeItem("auth_token");
    }
  }

  getToken(): string | null {
    if (typeof window !== "undefined" && !this.token) {
      this.token = localStorage.getItem("auth_token");
    }
    return this.token;
  }

  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          url.searchParams.append(key, String(value));
        }
      });
    }
    return url.toString();
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, headers = {}, params } = options;

    const url = this.buildUrl(endpoint, params);

    const requestHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      ...headers,
    };

    const token = this.getToken();
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    }

    // Debug logging
    console.log(`[API] ${method} ${endpoint}`, { hasToken: !!token, tokenPrefix: token?.substring(0, 20) });

    const response = await fetch(url, {
      method,
      headers: requestHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`[API] Error ${response.status}:`, endpoint, errorData);
      // 401エラーの場合、トークンをクリアしてログイン画面にリダイレクト
      if (response.status === 401 && typeof window !== "undefined") {
        console.error('[API] 401 Unauthorized - clearing token and redirecting to login');
        this.setToken(null);
        window.location.href = "/login";
        // リダイレクト中はPromiseを永久にpendingにしてコンポーネントのクラッシュを防ぐ
        return new Promise(() => {}) as T;
      }
      throw new ApiError(response.status, errorData.detail || response.statusText, errorData);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Convenience methods
  get<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    return this.request<T>(endpoint, { method: "GET", params });
  }

  post<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: "POST", body });
  }

  put<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: "PUT", body });
  }

  patch<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: "PATCH", body });
  }

  delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  async postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = this.buildUrl(endpoint);

    const requestHeaders: Record<string, string> = {};

    const token = this.getToken();
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: "POST",
      headers: requestHeaders,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(response.status, errorData.detail || response.statusText, errorData);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Alias for postFormData for file uploads
  upload<T>(endpoint: string, formData: FormData): Promise<T> {
    return this.postFormData<T>(endpoint, formData);
  }

  async getBlob(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<Blob> {
    const url = this.buildUrl(endpoint, params);

    const requestHeaders: Record<string, string> = {};

    const token = this.getToken();
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    }

    console.log(`[API] GET Blob ${endpoint}`, { hasToken: !!token });

    const response = await fetch(url, {
      method: "GET",
      headers: requestHeaders,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`[API] Error ${response.status}:`, endpoint, errorData);
      // 401エラーの場合、トークンをクリアしてログイン画面にリダイレクト
      if (response.status === 401 && typeof window !== "undefined") {
        console.error('[API] 401 Unauthorized - clearing token and redirecting to login');
        this.setToken(null);
        window.location.href = "/login";
        // リダイレクト中はPromiseを永久にpendingにしてクラッシュを防ぐ
        return new Promise<Blob>(() => {});
      }
      throw new ApiError(response.status, errorData.detail || response.statusText, errorData);
    }

    return response.blob();
  }
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export const apiClient = new ApiClient(API_URL);

// Helper function to get access token (for file uploads etc.)
export function getAccessToken(): string | null {
  return apiClient.getToken();
}

export default apiClient;

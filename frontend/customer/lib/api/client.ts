/**
 * Django REST API Client
 * JWT認証 + テナント対応 APIクライアント
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// トークン管理
const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const TENANT_ID_KEY = 'tenant_id';

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface ApiError {
  message: string;
  status: number;
  errors?: Record<string, string[]>;
}

// ============================================
// トークン管理
// ============================================

export const getAccessToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const getRefreshToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

export const getTenantId = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TENANT_ID_KEY);
};

export const setTokens = (tokens: TokenPair): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, tokens.access);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
};

export const setTenantId = (tenantId: string): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TENANT_ID_KEY, tenantId);
};

export const clearTokens = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};

export const clearAll = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(TENANT_ID_KEY);
};

// ============================================
// トークンリフレッシュ
// ============================================

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

export const refreshAccessToken = async (): Promise<string | null> => {
  // 同時に複数のリフレッシュリクエストを防ぐ
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) {
        clearTokens();
        return null;
      }

      const data = await response.json();
      localStorage.setItem(TOKEN_KEY, data.access);
      return data.access;
    } catch {
      clearTokens();
      return null;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};

// ============================================
// JWT デコード（有効期限チェック用）
// ============================================

const isTokenExpired = (token: string, bufferSeconds = 60): boolean => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000;
    return Date.now() >= exp - bufferSeconds * 1000;
  } catch {
    return true;
  }
};

// ============================================
// API リクエスト
// ============================================

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  skipAuth?: boolean;
  tenantId?: string;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, skipAuth = false, tenantId, ...fetchOptions } = options;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers || {}),
  };

  // テナントID を追加
  const tenant = tenantId || getTenantId();
  if (tenant) {
    (headers as Record<string, string>)['X-Tenant-ID'] = tenant;
  }

  // 認証トークンを追加
  if (!skipAuth) {
    let token = getAccessToken();

    // トークンが期限切れの場合はリフレッシュを試みる
    if (token && isTokenExpired(token)) {
      token = await refreshAccessToken();
    }

    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // 401エラーの場合、トークンリフレッシュを試みて再リクエスト
  if (response.status === 401 && !skipAuth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;
      const retryResponse = await fetch(url, {
        ...fetchOptions,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!retryResponse.ok) {
        throw await createApiError(retryResponse);
      }

      if (retryResponse.status === 204) {
        return {} as T;
      }

      const retryData = await retryResponse.json();

      // バックエンドが success: false を返した場合はエラーとして扱う
      if (retryData && typeof retryData === 'object' && 'success' in retryData && retryData.success === false) {
        const error = retryData.error || {};
        throw {
          message: error.message || 'APIエラーが発生しました',
          status: retryResponse.status,
          errors: error.details,
          code: error.code,
        } as ApiError & { code?: string };
      }

      // バックエンドが error オブジェクトを直接返した場合もエラーとして扱う
      if (retryData && typeof retryData === 'object' && 'error' in retryData && typeof retryData.error === 'object' && retryData.error !== null) {
        const error = retryData.error;
        throw {
          message: error.message || 'APIエラーが発生しました',
          status: retryResponse.status,
          errors: error.details,
          code: error.code,
        } as ApiError & { code?: string };
      }

      return retryData as T;
    } else {
      // リフレッシュ失敗 - ログアウト状態
      clearTokens();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw { message: '認証の有効期限が切れました', status: 401 } as ApiError;
    }
  }

  if (!response.ok) {
    throw await createApiError(response);
  }

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json();

  // バックエンドが success: false を返した場合はエラーとして扱う
  if (data && typeof data === 'object' && 'success' in data && data.success === false) {
    const error = data.error || {};
    throw {
      message: error.message || 'APIエラーが発生しました',
      status: response.status,
      errors: error.details,
      code: error.code,
    } as ApiError & { code?: string };
  }

  // バックエンドが error オブジェクトを直接返した場合もエラーとして扱う
  if (data && typeof data === 'object' && 'error' in data && typeof data.error === 'object' && data.error !== null) {
    const error = data.error;
    throw {
      message: error.message || 'APIエラーが発生しました',
      status: response.status,
      errors: error.details,
      code: error.code,
    } as ApiError & { code?: string };
  }

  return data as T;
}

async function createApiError(response: Response): Promise<ApiError> {
  let message = 'APIエラーが発生しました';
  let errors: Record<string, string[]> | undefined;

  try {
    const data = await response.json();
    // バックエンドの統一エラーフォーマット {success: false, error: {code, message, details}} を処理
    if (data.error && typeof data.error === 'object') {
      message = data.error.message || message;
      errors = data.error.details;
    } else if (data.detail) {
      message = data.detail;
    } else if (typeof data.error === 'string') {
      message = data.error;
    } else if (data.message) {
      message = data.message;
    }
    // errorsがオブジェクトでない場合は設定しない
    if (!errors || typeof errors !== 'object') {
      errors = data.errors;
    }
  } catch {
    message = response.statusText || message;
  }

  return {
    message,
    status: response.status,
    errors,
  };
}

// ============================================
// HTTP メソッドのショートカット
// ============================================

export const api = {
  get: <T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method'>) =>
    apiRequest<T>(endpoint, { ...options, method: 'POST', body }),

  put: <T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method'>) =>
    apiRequest<T>(endpoint, { ...options, method: 'PUT', body }),

  patch: <T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method'>) =>
    apiRequest<T>(endpoint, { ...options, method: 'PATCH', body }),

  delete: <T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),

  /**
   * FormDataをPOSTリクエスト（ファイルアップロード用）
   */
  postFormData: async <T>(endpoint: string, formData: FormData, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> => {
    const { skipAuth = false, tenantId, ...fetchOptions } = options || {};

    const headers: HeadersInit = {
      // Content-Typeは設定しない（ブラウザが自動的にmultipart/form-dataとboundaryを設定）
      ...(fetchOptions.headers || {}),
    };

    // テナントID を追加
    const tenant = tenantId || getTenantId();
    if (tenant) {
      (headers as Record<string, string>)['X-Tenant-ID'] = tenant;
    }

    // 認証トークンを追加
    if (!skipAuth) {
      let token = getAccessToken();

      // トークンが期限切れの場合はリフレッシュを試みる
      if (token && isTokenExpired(token)) {
        token = await refreshAccessToken();
      }

      if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
      }
    }

    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

    const response = await fetch(url, {
      ...fetchOptions,
      method: 'POST',
      headers,
      body: formData, // FormDataをそのまま送信
    });

    if (!response.ok) {
      throw await createApiError(response);
    }

    if (response.status === 204) {
      return {} as T;
    }

    const data = await response.json();

    // バックエンドが success: false を返した場合はエラーとして扱う
    if (data && typeof data === 'object' && 'success' in data && data.success === false) {
      const error = data.error || {};
      throw {
        message: error.message || 'APIエラーが発生しました',
        status: response.status,
        errors: error.details,
        code: error.code,
      } as ApiError & { code?: string };
    }

    return data as T;
  },

  /**
   * BlobとしてGETリクエスト（ファイルダウンロード用）
   */
  getBlob: async (endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<Blob> => {
    const { skipAuth = false, tenantId, ...fetchOptions } = options || {};

    const headers: HeadersInit = {
      ...(fetchOptions.headers || {}),
    };

    // テナントID を追加
    const tenant = tenantId || getTenantId();
    if (tenant) {
      (headers as Record<string, string>)['X-Tenant-ID'] = tenant;
    }

    // 認証トークンを追加
    if (!skipAuth) {
      let token = getAccessToken();

      // トークンが期限切れの場合はリフレッシュを試みる
      if (token && isTokenExpired(token)) {
        token = await refreshAccessToken();
      }

      if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
      }
    }

    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

    const response = await fetch(url, {
      ...fetchOptions,
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      // エラーレスポンスを取得
      let errorMessage = 'ファイルのダウンロードに失敗しました';
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.message || errorMessage;
      } catch {
        // JSONでない場合はデフォルトメッセージを使用
      }
      throw { message: errorMessage, status: response.status } as ApiError;
    }

    return response.blob();
  },
};

// Helper function to get backend base URL (for media files)
export function getBackendBaseUrl(): string {
  const apiUrl = API_BASE_URL;
  // Remove /api/v1 from the end to get base URL
  return apiUrl.replace(/\/api\/v1\/?$/, '');
}

// Helper function to normalize media URLs (handles both relative and absolute URLs)
export function getMediaUrl(url: string | undefined | null): string {
  if (!url) return '';
  // If already a full URL, return as-is
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  // If relative URL (starts with /), prepend backend base URL
  if (url.startsWith('/')) {
    return `${getBackendBaseUrl()}${url}`;
  }
  // Otherwise, assume it's a relative path and add /
  return `${getBackendBaseUrl()}/${url}`;
}

export default api;

/**
 * Authentication API
 * 認証関連のAPI関数（社員向け）
 */

import api, { setTokens, clearTokens, getRefreshToken, setTenantId } from './client';

// ============================================
// 型定義
// ============================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: string;
    email: string;
    fullName: string;
    userType: 'ADMIN' | 'STAFF' | 'GUARDIAN';
    role: string;
    tenantId: string | null;
    primarySchoolId: string | null;
  };
}

export interface Profile {
  id: string;
  email: string;
  fullName: string;
  firstName: string;
  lastName: string;
  userType: string;
  role: string;
  tenantId: string | null;
  primarySchoolId: string | null;
  phone?: string;
  avatarUrl?: string;
}

export interface ApiSuccessMessage {
  message: string;
}

// ============================================
// 認証API
// ============================================

/**
 * ログイン（メールアドレス + パスワード）
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>('/auth/login/', credentials, {
    skipAuth: true,
  });
  setTokens({ access: response.access, refresh: response.refresh });

  // テナントIDを保存
  if (response.user.tenantId) {
    setTenantId(response.user.tenantId);
  }

  return response;
}

/**
 * ログアウト
 */
export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();

  try {
    if (refreshToken) {
      await api.post('/auth/logout/', { refresh: refreshToken });
    }
  } catch {
    // ログアウトAPIが失敗してもトークンはクリア
  }

  clearTokens();
}

/**
 * 現在のユーザー情報を取得
 */
export async function getMe(): Promise<Profile> {
  return api.get<Profile>('/auth/me/');
}

/**
 * プロフィール更新
 */
export async function updateProfile(data: Partial<Profile>): Promise<Profile> {
  return api.patch<Profile>('/auth/me/', data);
}

/**
 * パスワード変更
 */
export interface PasswordChangeRequest {
  currentPassword: string;
  newPassword: string;
  newPasswordConfirm: string;
}

export async function changePassword(data: PasswordChangeRequest): Promise<ApiSuccessMessage> {
  return api.post<ApiSuccessMessage>('/auth/password/change/', {
    current_password: data.currentPassword,
    new_password: data.newPassword,
    new_password_confirm: data.newPasswordConfirm,
  });
}

/**
 * ユーザーがログイン済みかチェック
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  const token = localStorage.getItem('staff_access_token');
  return !!token;
}

/**
 * JWTからユーザー情報を取得
 */
export function getUserFromToken(): LoginResponse['user'] | null {
  if (typeof window === 'undefined') return null;
  const token = localStorage.getItem('staff_access_token');
  if (!token) return null;

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return {
      id: payload.user_id,
      email: payload.email,
      fullName: payload.full_name || '',
      userType: payload.user_type,
      role: payload.role,
      tenantId: payload.tenant_id || null,
      primarySchoolId: null,
    };
  } catch {
    return null;
  }
}

// ============================================
// QRコードAPI
// ============================================

export interface MyQRCodeResponse {
  qr_code: string;
  user_no: string;
  user_name: string;
  user_type: string;
}

/**
 * 自分のQRコード情報を取得
 */
export async function getMyQRCode(): Promise<MyQRCodeResponse> {
  return api.get<MyQRCodeResponse>('/users/my-qr/');
}

/**
 * QRコードを再発行
 */
export async function regenerateMyQRCode(): Promise<MyQRCodeResponse & { message: string }> {
  return api.post<MyQRCodeResponse & { message: string }>('/users/regenerate-qr/');
}

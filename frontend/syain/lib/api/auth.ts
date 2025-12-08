/**
 * Authentication API
 * 認証関連のAPI関数
 */

import api, { setTokens, clearTokens } from './client';
import type {
  LoginRequest,
  LoginResponse,
  PasswordChangeRequest,
  Profile,
  ApiSuccessMessage,
} from './types';

/**
 * ログイン
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>('/auth/login/', credentials, {
    skipAuth: true,
  });
  setTokens({ access: response.access, refresh: response.refresh });
  return response;
}

/**
 * ログアウト
 */
export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout/');
  } catch {
    // ログアウトAPIが失敗してもトークンはクリア
  }
  clearTokens();
}

/**
 * パスワード変更（ログイン済みユーザー）
 */
export async function changePassword(data: PasswordChangeRequest): Promise<ApiSuccessMessage> {
  return api.post<ApiSuccessMessage>('/users/profile/', data);
}

/**
 * 現在のユーザープロフィール取得
 */
export async function getProfile(): Promise<Profile> {
  return api.get<Profile>('/users/profile/');
}

/**
 * プロフィール更新
 */
export async function updateProfile(data: Partial<Profile>): Promise<Profile> {
  return api.patch<Profile>('/users/profile/', data);
}

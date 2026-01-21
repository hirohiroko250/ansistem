/**
 * Authentication API
 * 認証関連のAPI関数（保護者・顧客向け）
 */

import api, { setTokens, clearTokens, getRefreshToken, setTenantId } from './client';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  Profile,
  ApiSuccessMessage,
  PasswordChangeRequest,
  PasswordChangeResponse,
} from './types';

/**
 * メールアドレス重複チェック
 * @param email - チェックするメールアドレス
 * @returns 利用可能かどうかとメッセージ
 */
export async function checkEmail(email: string): Promise<{ available: boolean; message: string }> {
  return api.post<{ available: boolean; message: string }>('/auth/check-email/', { email }, {
    skipAuth: true,
  });
}

/**
 * 電話番号重複チェック
 * @param phone - チェックする電話番号
 * @returns 利用可能かどうかとメッセージ
 */
export async function checkPhone(phone: string): Promise<{ available: boolean; message: string }> {
  return api.post<{ available: boolean; message: string }>('/auth/check-phone/', { phone }, {
    skipAuth: true,
  });
}

/**
 * ログイン
 * @param credentials - メールアドレスとパスワード
 * @returns ログインレスポンス（トークン + ユーザー情報）
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
 * 新規登録（Onboarding API使用）
 * @param data - 登録情報（メール、パスワード、氏名）
 * @returns 登録レスポンス（トークン + ユーザー・保護者情報）
 */
export async function register(data: RegisterRequest): Promise<RegisterResponse> {
  // camelCase → snake_case 変換
  const payload = {
    email: data.email,
    password: data.password,
    full_name: data.fullName,
    full_name_kana: data.fullNameKana,
    phone: data.phone,
    postal_code: data.postalCode,
    prefecture: data.prefecture,
    city: data.city,
    address1: data.address1,
    address2: data.address2,
    nearest_school_id: data.nearestSchoolId,
    interested_brands: data.interestedBrands,
    referral_source: data.referralSource,
    expectations: data.expectations,
  };

  const response = await api.post<RegisterResponse>('/onboarding/register/', payload, {
    skipAuth: true,
  });
  setTokens({ access: response.tokens.access, refresh: response.tokens.refresh });

  return response;
}

/**
 * ログアウト
 * サーバーにリフレッシュトークンの無効化を通知し、ローカルのトークンをクリア
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
 * @returns ユーザープロフィール
 */
export async function getMe(): Promise<Profile> {
  return api.get<Profile>('/auth/me/');
}

/**
 * プロフィール更新
 * @param data - 更新するプロフィール情報
 * @returns 更新後のプロフィール
 */
export async function updateProfile(data: Partial<Profile>): Promise<Profile> {
  return api.patch<Profile>('/auth/me/', data);
}

/**
 * パスワード変更（初回ログイン時の強制変更含む）
 * @param data - 現在のパスワードと新しいパスワード
 * @returns 成功メッセージと新しいトークン
 */
export async function changePassword(data: PasswordChangeRequest): Promise<PasswordChangeResponse> {
  const response = await api.post<PasswordChangeResponse>('/auth/password-change/', {
    current_password: data.currentPassword,
    new_password: data.newPassword,
    new_password_confirm: data.newPasswordConfirm,
  });

  // 新しいトークンを保存
  if (response.access && response.refresh) {
    setTokens({ access: response.access, refresh: response.refresh });
  }

  return response;
}

/**
 * パスワードリセットリクエスト
 * @param email - パスワードリセット用のメールアドレス
 * @returns 成功メッセージ
 */
export async function requestPasswordReset(email: string): Promise<ApiSuccessMessage> {
  return api.post<ApiSuccessMessage>('/auth/password-reset/', { email }, {
    skipAuth: true,
  });
}

/**
 * パスワードリセット確認
 * @param data - トークンと新しいパスワード
 * @returns 成功メッセージ
 */
export interface PasswordResetConfirmRequest {
  token: string;
  newPassword: string;
  newPasswordConfirm: string;
}

export async function confirmPasswordReset(data: PasswordResetConfirmRequest): Promise<ApiSuccessMessage> {
  return api.post<ApiSuccessMessage>('/auth/password-reset/confirm/', {
    token: data.token,
    new_password: data.newPassword,
    new_password_confirm: data.newPasswordConfirm,
  }, {
    skipAuth: true,
  });
}

/**
 * メールアドレス確認
 * @param token - メール確認トークン
 * @returns 成功メッセージ
 */
export async function verifyEmail(token: string): Promise<ApiSuccessMessage> {
  return api.post<ApiSuccessMessage>('/auth/email/verify/', { token }, {
    skipAuth: true,
  });
}

/**
 * 確認メール再送信
 * @returns 成功メッセージ
 */
export async function resendVerificationEmail(): Promise<ApiSuccessMessage> {
  return api.post<ApiSuccessMessage>('/auth/email/resend/');
}

/**
 * ユーザーがログイン済みかチェック
 * @returns ログイン状態
 */
export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  const token = localStorage.getItem('access_token');
  return !!token;
}

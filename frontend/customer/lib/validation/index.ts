/**
 * Validation Utilities
 *
 * フロントエンドのバリデーション責務:
 * - 入力形式チェック（正規表現、HTML5）
 * - 必須チェック（空文字）
 * - パスワード一致チェック
 *
 * バックエンドの責務:
 * - 重複チェック（メール、電話番号）
 * - ビジネスルールチェック
 */

import { api } from '@/lib/api/client';

// =============================================================================
// 型定義
// =============================================================================

export interface ValidationResult {
  available: boolean;
  message: string;
}

export interface ValidationCheckRequest {
  email?: string;
  phone?: string;
  guardian_no?: string;
  student_no?: string;
}

export interface ValidationCheckResponse {
  [key: string]: ValidationResult;
}

export interface FormValidationErrors {
  [field: string]: string | undefined;
}

// =============================================================================
// クライアントサイドバリデーション（フォーマットチェック）
// =============================================================================

/**
 * メールアドレス形式チェック
 */
export function validateEmailFormat(email: string): string | undefined {
  if (!email) return undefined; // 必須チェックは別途行う

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return 'メールアドレスの形式が正しくありません';
  }
  return undefined;
}

/**
 * 電話番号形式チェック（日本の電話番号）
 */
export function validatePhoneFormat(phone: string): string | undefined {
  if (!phone) return undefined;

  // ハイフンや空白を除去して数字のみでチェック
  const digitsOnly = phone.replace(/[-\s　]/g, '');

  // 10桁または11桁の数字
  if (!/^\d{10,11}$/.test(digitsOnly)) {
    return '電話番号は10桁または11桁の数字で入力してください';
  }
  return undefined;
}

/**
 * 郵便番号形式チェック
 */
export function validatePostalCodeFormat(postalCode: string): string | undefined {
  if (!postalCode) return undefined;

  // ハイフンありなし両対応
  const digitsOnly = postalCode.replace(/-/g, '');
  if (!/^\d{7}$/.test(digitsOnly)) {
    return '郵便番号は7桁の数字で入力してください';
  }
  return undefined;
}

/**
 * パスワード強度チェック
 */
export function validatePasswordStrength(password: string): string | undefined {
  if (!password) return undefined;

  if (password.length < 8) {
    return 'パスワードは8文字以上で入力してください';
  }
  return undefined;
}

/**
 * パスワード一致チェック
 */
export function validatePasswordMatch(
  password: string,
  confirmPassword: string
): string | undefined {
  if (!confirmPassword) return undefined;

  if (password !== confirmPassword) {
    return 'パスワードが一致しません';
  }
  return undefined;
}

/**
 * 必須チェック
 */
export function validateRequired(
  value: string | undefined | null,
  fieldName: string
): string | undefined {
  if (!value || value.trim() === '') {
    return `${fieldName}は必須です`;
  }
  return undefined;
}

/**
 * 全角カナチェック
 */
export function validateKatakana(value: string): string | undefined {
  if (!value) return undefined;

  // 全角カタカナ、全角スペース、長音記号のみ許可
  if (!/^[ァ-ヶー　\s]+$/.test(value)) {
    return '全角カタカナで入力してください';
  }
  return undefined;
}

// =============================================================================
// サーバーサイドバリデーション（重複チェック等）
// =============================================================================

/**
 * バックエンドの一括バリデーションAPIを呼び出し
 *
 * @example
 * const result = await checkValidation({ email: 'test@example.com', phone: '09012345678' });
 * if (!result.email.available) {
 *   setEmailError(result.email.message);
 * }
 */
export async function checkValidation(
  fields: ValidationCheckRequest
): Promise<ValidationCheckResponse> {
  try {
    const response = await api.post<ValidationCheckResponse>(
      '/auth/validation/check/',
      fields,
      { skipAuth: true }
    );
    return response;
  } catch {
    // APIエラー時は全フィールドを利用可能として返す（フォーム送信時に再チェック）
    const result: ValidationCheckResponse = {};
    for (const key of Object.keys(fields)) {
      result[key] = { available: true, message: '' };
    }
    return result;
  }
}

/**
 * メールアドレスの重複チェック
 */
export async function checkEmailAvailability(
  email: string
): Promise<ValidationResult> {
  const result = await checkValidation({ email });
  return result.email || { available: true, message: '' };
}

/**
 * 電話番号の重複チェック
 */
export async function checkPhoneAvailability(
  phone: string
): Promise<ValidationResult> {
  const result = await checkValidation({ phone });
  return result.phone || { available: true, message: '' };
}

// =============================================================================
// デバウンス付きバリデーション
// =============================================================================

/**
 * デバウンス付きの非同期バリデーション実行
 *
 * @example
 * const debouncedEmailCheck = createDebouncedValidator(
 *   async (email) => {
 *     const result = await checkEmailAvailability(email);
 *     return result.available ? undefined : result.message;
 *   },
 *   500
 * );
 *
 * // 入力時に呼び出し
 * onChange={(e) => {
 *   setEmail(e.target.value);
 *   debouncedEmailCheck(e.target.value).then(setEmailError);
 * }}
 */
export function createDebouncedValidator<T>(
  validator: (value: T) => Promise<string | undefined>,
  delay: number = 500
): (value: T) => Promise<string | undefined> {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let currentPromise: Promise<string | undefined> | null = null;

  return (value: T): Promise<string | undefined> => {
    // 前のタイマーをキャンセル
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    currentPromise = new Promise((resolve) => {
      timeoutId = setTimeout(async () => {
        const result = await validator(value);
        resolve(result);
      }, delay);
    });

    return currentPromise;
  };
}

// =============================================================================
// フォームバリデーション統合
// =============================================================================

export interface RegistrationFormData {
  email: string;
  phone?: string;
  password: string;
  passwordConfirm: string;
  fullName: string;
  fullNameKana?: string;
  postalCode?: string;
}

/**
 * 登録フォームのクライアントサイドバリデーション
 */
export function validateRegistrationForm(
  data: RegistrationFormData
): FormValidationErrors {
  const errors: FormValidationErrors = {};

  // 必須フィールド
  errors.email = validateRequired(data.email, 'メールアドレス');
  errors.password = validateRequired(data.password, 'パスワード');
  errors.passwordConfirm = validateRequired(data.passwordConfirm, 'パスワード（確認）');
  errors.fullName = validateRequired(data.fullName, '氏名');

  // フォーマットチェック（必須エラーがない場合のみ）
  if (!errors.email) {
    errors.email = validateEmailFormat(data.email);
  }
  if (!errors.password) {
    errors.password = validatePasswordStrength(data.password);
  }
  if (!errors.passwordConfirm) {
    errors.passwordConfirm = validatePasswordMatch(data.password, data.passwordConfirm);
  }

  // オプションフィールドのフォーマットチェック
  if (data.phone) {
    errors.phone = validatePhoneFormat(data.phone);
  }
  if (data.fullNameKana) {
    errors.fullNameKana = validateKatakana(data.fullNameKana);
  }
  if (data.postalCode) {
    errors.postalCode = validatePostalCodeFormat(data.postalCode);
  }

  // undefinedのエラーを削除
  const cleanErrors: FormValidationErrors = {};
  for (const [key, value] of Object.entries(errors)) {
    if (value !== undefined) {
      cleanErrors[key] = value;
    }
  }

  return cleanErrors;
}

/**
 * 登録フォームのサーバーサイドバリデーション（重複チェック）
 */
export async function validateRegistrationFormAsync(
  data: Pick<RegistrationFormData, 'email' | 'phone'>
): Promise<FormValidationErrors> {
  const errors: FormValidationErrors = {};

  const fieldsToCheck: ValidationCheckRequest = {};
  if (data.email) fieldsToCheck.email = data.email;
  if (data.phone) fieldsToCheck.phone = data.phone;

  if (Object.keys(fieldsToCheck).length === 0) {
    return errors;
  }

  const result = await checkValidation(fieldsToCheck);

  if (result.email && !result.email.available) {
    errors.email = result.email.message;
  }
  if (result.phone && !result.phone.available) {
    errors.phone = result.phone.message;
  }

  return errors;
}

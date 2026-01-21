/**
 * Error Handler - 共通エラーハンドリングユーティリティ
 *
 * バックエンドの統一エラーレスポンス形式に対応:
 * {
 *   "success": false,
 *   "error": {
 *     "code": "ERROR_CODE",
 *     "message": "ユーザー向けメッセージ",
 *     "details": { "field": ["エラー詳細"] }
 *   }
 * }
 */

import { toast } from '@/hooks/use-toast';
import { clearAll } from './client';

// =============================================================================
// エラーコード定義（バックエンドと同期）
// =============================================================================

export const ErrorCode = {
  // 認証・認可
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  ACCOUNT_LOCKED: 'ACCOUNT_LOCKED',

  // バリデーション
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_FORMAT: 'INVALID_FORMAT',
  REQUIRED_FIELD: 'REQUIRED_FIELD',
  DUPLICATE_VALUE: 'DUPLICATE_VALUE',

  // リソース
  NOT_FOUND: 'NOT_FOUND',
  RESOURCE_NOT_FOUND: 'RESOURCE_NOT_FOUND',
  TENANT_NOT_FOUND: 'TENANT_NOT_FOUND',
  STUDENT_NOT_FOUND: 'STUDENT_NOT_FOUND',
  GUARDIAN_NOT_FOUND: 'GUARDIAN_NOT_FOUND',
  SCHOOL_NOT_FOUND: 'SCHOOL_NOT_FOUND',

  // ビジネスロジック
  BUSINESS_RULE_VIOLATION: 'BUSINESS_RULE_VIOLATION',
  INVALID_OPERATION: 'INVALID_OPERATION',
  INSUFFICIENT_BALANCE: 'INSUFFICIENT_BALANCE',
  CAPACITY_EXCEEDED: 'CAPACITY_EXCEEDED',
  ALREADY_EXISTS: 'ALREADY_EXISTS',
  ALREADY_BOOKED: 'ALREADY_BOOKED',
  BOOKING_FULL: 'BOOKING_FULL',
  CLOSED_DAY: 'CLOSED_DAY',

  // サーバーエラー
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
} as const;

export type ErrorCodeType = (typeof ErrorCode)[keyof typeof ErrorCode];

// =============================================================================
// エラー型定義
// =============================================================================

/**
 * API エラー型（拡張版）
 */
export interface ApiErrorWithCode {
  message: string;
  status: number;
  code?: ErrorCodeType | string;
  errors?: Record<string, string[]>;
}

/**
 * フォームエラー型
 */
export interface FormErrors {
  [field: string]: string | string[];
}

// =============================================================================
// エラー判定ユーティリティ
// =============================================================================

/**
 * ApiErrorWithCode型かどうかを判定
 */
export function isApiError(error: unknown): error is ApiErrorWithCode {
  return (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    'status' in error
  );
}

/**
 * 認証エラーかどうかを判定
 */
export function isAuthError(error: unknown): boolean {
  if (!isApiError(error)) return false;
  return (
    error.status === 401 ||
    error.code === ErrorCode.UNAUTHORIZED ||
    error.code === ErrorCode.TOKEN_EXPIRED ||
    error.code === ErrorCode.INVALID_CREDENTIALS
  );
}

/**
 * 権限エラーかどうかを判定
 */
export function isForbiddenError(error: unknown): boolean {
  if (!isApiError(error)) return false;
  return error.status === 403 || error.code === ErrorCode.FORBIDDEN;
}

/**
 * バリデーションエラーかどうかを判定
 */
export function isValidationError(error: unknown): boolean {
  if (!isApiError(error)) return false;
  return (
    error.status === 400 ||
    error.code === ErrorCode.VALIDATION_ERROR ||
    error.code === ErrorCode.INVALID_FORMAT ||
    error.code === ErrorCode.REQUIRED_FIELD ||
    error.code === ErrorCode.DUPLICATE_VALUE
  );
}

/**
 * リソース未検出エラーかどうかを判定
 */
export function isNotFoundError(error: unknown): boolean {
  if (!isApiError(error)) return false;
  return (
    error.status === 404 ||
    error.code === ErrorCode.NOT_FOUND ||
    error.code === ErrorCode.RESOURCE_NOT_FOUND ||
    error.code === ErrorCode.STUDENT_NOT_FOUND ||
    error.code === ErrorCode.GUARDIAN_NOT_FOUND ||
    error.code === ErrorCode.SCHOOL_NOT_FOUND
  );
}

/**
 * ビジネスルールエラーかどうかを判定
 */
export function isBusinessError(error: unknown): boolean {
  if (!isApiError(error)) return false;
  return (
    error.code === ErrorCode.BUSINESS_RULE_VIOLATION ||
    error.code === ErrorCode.INVALID_OPERATION ||
    error.code === ErrorCode.ALREADY_EXISTS ||
    error.code === ErrorCode.ALREADY_BOOKED ||
    error.code === ErrorCode.BOOKING_FULL ||
    error.code === ErrorCode.CLOSED_DAY
  );
}

/**
 * サーバーエラーかどうかを判定
 */
export function isServerError(error: unknown): boolean {
  if (!isApiError(error)) return false;
  return (
    error.status >= 500 ||
    error.code === ErrorCode.INTERNAL_ERROR ||
    error.code === ErrorCode.SERVICE_UNAVAILABLE
  );
}

// =============================================================================
// エラーメッセージ取得
// =============================================================================

/**
 * エラーからユーザー向けメッセージを取得
 */
export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message || 'エラーが発生しました';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'エラーが発生しました';
}

/**
 * エラーコードに対応するデフォルトメッセージを取得
 */
export function getDefaultMessageForCode(code: string): string {
  const messages: Record<string, string> = {
    [ErrorCode.UNAUTHORIZED]: '認証が必要です',
    [ErrorCode.FORBIDDEN]: 'アクセス権限がありません',
    [ErrorCode.TOKEN_EXPIRED]: 'セッションの有効期限が切れました',
    [ErrorCode.INVALID_CREDENTIALS]: 'メールアドレスまたはパスワードが正しくありません',
    [ErrorCode.ACCOUNT_LOCKED]: 'アカウントがロックされています',
    [ErrorCode.VALIDATION_ERROR]: '入力内容に問題があります',
    [ErrorCode.INVALID_FORMAT]: '入力形式が正しくありません',
    [ErrorCode.REQUIRED_FIELD]: '必須項目が入力されていません',
    [ErrorCode.DUPLICATE_VALUE]: '既に登録されている値です',
    [ErrorCode.NOT_FOUND]: '指定されたデータが見つかりません',
    [ErrorCode.STUDENT_NOT_FOUND]: '生徒が見つかりません',
    [ErrorCode.GUARDIAN_NOT_FOUND]: '保護者が見つかりません',
    [ErrorCode.SCHOOL_NOT_FOUND]: '校舎が見つかりません',
    [ErrorCode.BUSINESS_RULE_VIOLATION]: '処理を実行できません',
    [ErrorCode.INVALID_OPERATION]: 'この操作は許可されていません',
    [ErrorCode.ALREADY_EXISTS]: '既に登録されています',
    [ErrorCode.ALREADY_BOOKED]: 'この日時は既に予約済みです',
    [ErrorCode.BOOKING_FULL]: 'この日時は満席です',
    [ErrorCode.CLOSED_DAY]: '休講日のため予約できません',
    [ErrorCode.INTERNAL_ERROR]: 'サーバーエラーが発生しました',
    [ErrorCode.SERVICE_UNAVAILABLE]: 'サービスが一時的に利用できません',
  };
  return messages[code] || 'エラーが発生しました';
}

// =============================================================================
// フォームエラー処理
// =============================================================================

/**
 * APIエラーからフォームエラーに変換
 */
export function extractFormErrors(error: unknown): FormErrors {
  if (!isApiError(error) || !error.errors) {
    return {};
  }

  const formErrors: FormErrors = {};
  for (const [field, messages] of Object.entries(error.errors)) {
    // キャメルケースに変換（snake_case -> camelCase）
    const camelField = field.replace(/_([a-z])/g, (_, letter) =>
      letter.toUpperCase()
    );
    formErrors[camelField] = Array.isArray(messages) ? messages : [messages];
  }
  return formErrors;
}

/**
 * フォームエラーの最初のメッセージを取得
 */
export function getFirstFormError(errors: FormErrors): string | null {
  const fields = Object.keys(errors);
  if (fields.length === 0) return null;

  const firstError = errors[fields[0]];
  return Array.isArray(firstError) ? firstError[0] : firstError;
}

// =============================================================================
// エラーハンドリングオプション
// =============================================================================

export interface HandleErrorOptions {
  /** トースト通知を表示するか */
  showToast?: boolean;
  /** 認証エラー時にログインページへリダイレクトするか */
  redirectOnAuth?: boolean;
  /** カスタムエラーメッセージ */
  customMessage?: string;
  /** フォームエラーを処理するコールバック */
  onValidationError?: (errors: FormErrors) => void;
  /** 認証エラー時のコールバック */
  onAuthError?: () => void;
  /** エラー発生時の汎用コールバック */
  onError?: (error: ApiErrorWithCode) => void;
}

// =============================================================================
// メインエラーハンドラー
// =============================================================================

/**
 * 統一エラーハンドラー
 *
 * @example
 * try {
 *   await api.post('/users', data);
 * } catch (error) {
 *   handleApiError(error, {
 *     showToast: true,
 *     onValidationError: (errors) => setFormErrors(errors),
 *   });
 * }
 */
export function handleApiError(
  error: unknown,
  options: HandleErrorOptions = {}
): void {
  const {
    showToast = true,
    redirectOnAuth = true,
    customMessage,
    onValidationError,
    onAuthError,
    onError,
  } = options;

  // APIエラー型に正規化
  const apiError: ApiErrorWithCode = isApiError(error)
    ? error
    : {
        message: error instanceof Error ? error.message : 'エラーが発生しました',
        status: 500,
      };

  // エラータイプ別の処理
  if (isAuthError(apiError)) {
    // 認証エラー
    if (onAuthError) {
      onAuthError();
    }
    if (redirectOnAuth && typeof window !== 'undefined') {
      clearAll();
      window.location.href = '/login';
      return;
    }
  }

  if (isValidationError(apiError) && onValidationError) {
    // バリデーションエラー
    const formErrors = extractFormErrors(apiError);
    onValidationError(formErrors);
  }

  if (onError) {
    onError(apiError);
  }

  // トースト通知
  if (showToast) {
    const message = customMessage || getErrorMessage(apiError);
    const variant = isServerError(apiError) ? 'destructive' : 'destructive';

    toast({
      title: getToastTitle(apiError),
      description: message,
      variant,
    });
  }
}

/**
 * エラータイプに応じたトーストタイトルを取得
 */
function getToastTitle(error: ApiErrorWithCode): string {
  if (isAuthError(error)) return '認証エラー';
  if (isForbiddenError(error)) return 'アクセス拒否';
  if (isValidationError(error)) return '入力エラー';
  if (isNotFoundError(error)) return 'データが見つかりません';
  if (isBusinessError(error)) return '処理できません';
  if (isServerError(error)) return 'サーバーエラー';
  return 'エラー';
}

// =============================================================================
// 便利なラッパー関数
// =============================================================================

/**
 * トースト通知のみを表示するシンプルなエラーハンドラー
 */
export function showErrorToast(error: unknown, customMessage?: string): void {
  handleApiError(error, {
    showToast: true,
    redirectOnAuth: false,
    customMessage,
  });
}

/**
 * フォームエラー処理用のエラーハンドラー
 */
export function handleFormError(
  error: unknown,
  setErrors: (errors: FormErrors) => void
): void {
  handleApiError(error, {
    showToast: true,
    redirectOnAuth: true,
    onValidationError: setErrors,
  });
}

/**
 * Promise を安全に実行し、エラーをハンドリング
 *
 * @example
 * const result = await safeApiCall(
 *   () => api.get('/users'),
 *   { showToast: true }
 * );
 * if (result.success) {
 *   console.log(result.data);
 * }
 */
export async function safeApiCall<T>(
  fn: () => Promise<T>,
  options: HandleErrorOptions = {}
): Promise<{ success: true; data: T } | { success: false; error: ApiErrorWithCode }> {
  try {
    const data = await fn();
    return { success: true, data };
  } catch (error) {
    const apiError: ApiErrorWithCode = isApiError(error)
      ? error
      : {
          message: error instanceof Error ? error.message : 'エラーが発生しました',
          status: 500,
        };
    handleApiError(error, options);
    return { success: false, error: apiError };
  }
}

'use client';

/**
 * useFieldValidation - フィールドバリデーション用フック
 *
 * フィールドのblur時に非同期バリデーション（重複チェック等）を実行するフック。
 * キーストロークごとのAPIコールを避け、blur時のみ実行。
 */

import { useState, useCallback, useRef } from 'react';
import {
  checkEmailAvailability,
  checkPhoneAvailability,
  validateEmailFormat,
  validatePhoneFormat,
  ValidationResult,
} from '@/lib/validation';

export interface UseFieldValidationOptions {
  /** 遅延時間（ms）- blur後にこの時間待ってからバリデーション実行 */
  delay?: number;
  /** クライアントサイドバリデーションをスキップ */
  skipClientValidation?: boolean;
}

export interface FieldValidationState {
  error: string | undefined;
  isValidating: boolean;
  isValid: boolean | undefined;
}

export interface UseFieldValidationReturn extends FieldValidationState {
  /** blur時に呼び出すハンドラー */
  onBlur: () => void;
  /** 値変更時に呼び出すハンドラー（エラーをクリア） */
  onChange: () => void;
  /** エラーを手動でセット */
  setError: (error: string | undefined) => void;
  /** 状態をリセット */
  reset: () => void;
}

/**
 * メールアドレスバリデーション用フック
 */
export function useEmailValidation(
  getValue: () => string,
  options: UseFieldValidationOptions = {}
): UseFieldValidationReturn {
  const { delay = 300, skipClientValidation = false } = options;
  const [state, setState] = useState<FieldValidationState>({
    error: undefined,
    isValidating: false,
    isValid: undefined,
  });
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const validate = useCallback(async () => {
    const value = getValue();

    // 空の場合はスキップ（必須チェックは別で行う）
    if (!value) {
      setState({ error: undefined, isValidating: false, isValid: undefined });
      return;
    }

    // クライアントサイドバリデーション
    if (!skipClientValidation) {
      const formatError = validateEmailFormat(value);
      if (formatError) {
        setState({ error: formatError, isValidating: false, isValid: false });
        return;
      }
    }

    // サーバーサイドバリデーション
    setState((prev) => ({ ...prev, isValidating: true }));

    try {
      const result: ValidationResult = await checkEmailAvailability(value);
      setState({
        error: result.available ? undefined : result.message,
        isValidating: false,
        isValid: result.available,
      });
    } catch {
      // エラー時は通過させる（フォーム送信時に再チェック）
      setState({ error: undefined, isValidating: false, isValid: undefined });
    }
  }, [getValue, skipClientValidation]);

  const onBlur = useCallback(() => {
    // 前のタイマーをキャンセル
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // 遅延後にバリデーション実行
    timeoutRef.current = setTimeout(validate, delay);
  }, [validate, delay]);

  const onChange = useCallback(() => {
    // タイマーをキャンセル
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    // エラーをクリア（入力中はエラー非表示）
    setState((prev) => ({ ...prev, error: undefined, isValid: undefined }));
  }, []);

  const setError = useCallback((error: string | undefined) => {
    setState((prev) => ({
      ...prev,
      error,
      isValid: error ? false : prev.isValid,
    }));
  }, []);

  const reset = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setState({ error: undefined, isValidating: false, isValid: undefined });
  }, []);

  return {
    ...state,
    onBlur,
    onChange,
    setError,
    reset,
  };
}

/**
 * 電話番号バリデーション用フック
 */
export function usePhoneValidation(
  getValue: () => string,
  options: UseFieldValidationOptions = {}
): UseFieldValidationReturn {
  const { delay = 300, skipClientValidation = false } = options;
  const [state, setState] = useState<FieldValidationState>({
    error: undefined,
    isValidating: false,
    isValid: undefined,
  });
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const validate = useCallback(async () => {
    const value = getValue();

    // 空の場合はスキップ
    if (!value) {
      setState({ error: undefined, isValidating: false, isValid: undefined });
      return;
    }

    // クライアントサイドバリデーション
    if (!skipClientValidation) {
      const formatError = validatePhoneFormat(value);
      if (formatError) {
        setState({ error: formatError, isValidating: false, isValid: false });
        return;
      }
    }

    // サーバーサイドバリデーション
    setState((prev) => ({ ...prev, isValidating: true }));

    try {
      const result: ValidationResult = await checkPhoneAvailability(value);
      setState({
        error: result.available ? undefined : result.message,
        isValidating: false,
        isValid: result.available,
      });
    } catch {
      setState({ error: undefined, isValidating: false, isValid: undefined });
    }
  }, [getValue, skipClientValidation]);

  const onBlur = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(validate, delay);
  }, [validate, delay]);

  const onChange = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setState((prev) => ({ ...prev, error: undefined, isValid: undefined }));
  }, []);

  const setError = useCallback((error: string | undefined) => {
    setState((prev) => ({
      ...prev,
      error,
      isValid: error ? false : prev.isValid,
    }));
  }, []);

  const reset = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setState({ error: undefined, isValidating: false, isValid: undefined });
  }, []);

  return {
    ...state,
    onBlur,
    onChange,
    setError,
    reset,
  };
}

/**
 * 汎用バリデーション用フック
 *
 * @example
 * const nameValidation = useFieldValidation(
 *   () => name,
 *   (value) => value ? undefined : '名前は必須です'
 * );
 */
export function useFieldValidation(
  getValue: () => string,
  validator: (value: string) => string | undefined
): UseFieldValidationReturn {
  const [state, setState] = useState<FieldValidationState>({
    error: undefined,
    isValidating: false,
    isValid: undefined,
  });

  const validate = useCallback(() => {
    const value = getValue();
    const error = validator(value);
    setState({
      error,
      isValidating: false,
      isValid: !error,
    });
  }, [getValue, validator]);

  const onBlur = useCallback(() => {
    validate();
  }, [validate]);

  const onChange = useCallback(() => {
    setState((prev) => ({ ...prev, error: undefined, isValid: undefined }));
  }, []);

  const setError = useCallback((error: string | undefined) => {
    setState((prev) => ({
      ...prev,
      error,
      isValid: error ? false : prev.isValid,
    }));
  }, []);

  const reset = useCallback(() => {
    setState({ error: undefined, isValidating: false, isValid: undefined });
  }, []);

  return {
    ...state,
    onBlur,
    onChange,
    setError,
    reset,
  };
}

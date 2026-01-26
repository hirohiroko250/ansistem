/**
 * useBiometricAuth - 生体認証（Face ID / Touch ID）フック
 *
 * WebAuthn API を使用してデバイスの生体認証を実行
 * iOS: Face ID / Touch ID
 * Android: 指紋認証 / 顔認証
 */
'use client';

import { useState, useCallback, useEffect } from 'react';

// 生体認証が利用可能かどうか
export function isBiometricAvailable(): boolean {
  if (typeof window === 'undefined') return false;

  // WebAuthn API が利用可能か
  return (
    !!window.PublicKeyCredential &&
    typeof window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable === 'function'
  );
}

// 生体認証の登録データを localStorage に保存するキー
const CREDENTIAL_ID_KEY = 'biometric_credential_id';
const BIOMETRIC_ENABLED_KEY = 'biometric_enabled';
const BIOMETRIC_USER_KEY = 'biometric_user_email';

interface BiometricAuthResult {
  success: boolean;
  error?: string;
  credentialId?: string;
}

interface UseBiometricAuthReturn {
  /** 生体認証が利用可能か */
  isAvailable: boolean;
  /** 生体認証が有効化されているか */
  isEnabled: boolean;
  /** 生体認証をサポートしているか */
  isSupported: boolean;
  /** 処理中かどうか */
  isLoading: boolean;
  /** エラーメッセージ */
  error: string | null;
  /** 生体認証を有効化（登録） */
  enableBiometric: (email: string) => Promise<BiometricAuthResult>;
  /** 生体認証を無効化 */
  disableBiometric: () => void;
  /** 生体認証で認証 */
  authenticate: () => Promise<BiometricAuthResult>;
  /** 登録済みのメールアドレスを取得 */
  getRegisteredEmail: () => string | null;
}

export function useBiometricAuth(): UseBiometricAuthReturn {
  const [isAvailable, setIsAvailable] = useState(false);
  const [isEnabled, setIsEnabled] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 初期化: 生体認証の利用可能性をチェック
  useEffect(() => {
    const checkAvailability = async () => {
      if (!isBiometricAvailable()) {
        setIsSupported(false);
        setIsAvailable(false);
        return;
      }

      setIsSupported(true);

      try {
        const available =
          await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        setIsAvailable(available);

        // 既に有効化されているかチェック
        const enabled = localStorage.getItem(BIOMETRIC_ENABLED_KEY) === 'true';
        setIsEnabled(enabled && available);
      } catch {
        setIsAvailable(false);
      }
    };

    checkAvailability();
  }, []);

  // 登録済みのメールアドレスを取得
  const getRegisteredEmail = useCallback((): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(BIOMETRIC_USER_KEY);
  }, []);

  // 生体認証を有効化（登録）
  const enableBiometric = useCallback(
    async (email: string): Promise<BiometricAuthResult> => {
      if (!isAvailable) {
        return { success: false, error: '生体認証がこのデバイスでは利用できません' };
      }

      setIsLoading(true);
      setError(null);

      try {
        // チャレンジを生成（本番環境ではサーバーから取得）
        const challenge = new Uint8Array(32);
        crypto.getRandomValues(challenge);

        // ユーザーIDを生成
        const userId = new Uint8Array(16);
        crypto.getRandomValues(userId);

        // 登録オプション
        const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
          challenge,
          rp: {
            name: 'OZA',
            id: window.location.hostname,
          },
          user: {
            id: userId,
            name: email,
            displayName: email.split('@')[0],
          },
          pubKeyCredParams: [
            { alg: -7, type: 'public-key' }, // ES256
            { alg: -257, type: 'public-key' }, // RS256
          ],
          authenticatorSelection: {
            authenticatorAttachment: 'platform', // デバイス内蔵の認証器
            userVerification: 'required', // 生体認証必須
            residentKey: 'preferred',
          },
          timeout: 60000,
          attestation: 'none',
        };

        // 認証情報を作成
        const credential = (await navigator.credentials.create({
          publicKey: publicKeyCredentialCreationOptions,
        })) as PublicKeyCredential;

        if (!credential) {
          throw new Error('認証情報の作成に失敗しました');
        }

        // 認証情報IDを保存
        const credentialId = btoa(
          String.fromCharCode.apply(null, Array.from(new Uint8Array(credential.rawId)))
        );
        localStorage.setItem(CREDENTIAL_ID_KEY, credentialId);
        localStorage.setItem(BIOMETRIC_ENABLED_KEY, 'true');
        localStorage.setItem(BIOMETRIC_USER_KEY, email);

        setIsEnabled(true);
        setIsLoading(false);

        return { success: true, credentialId };
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : '生体認証の登録に失敗しました';
        setError(errorMessage);
        setIsLoading(false);
        return { success: false, error: errorMessage };
      }
    },
    [isAvailable]
  );

  // 生体認証を無効化
  const disableBiometric = useCallback(() => {
    localStorage.removeItem(CREDENTIAL_ID_KEY);
    localStorage.removeItem(BIOMETRIC_ENABLED_KEY);
    localStorage.removeItem(BIOMETRIC_USER_KEY);
    setIsEnabled(false);
  }, []);

  // 生体認証で認証
  const authenticate = useCallback(async (): Promise<BiometricAuthResult> => {
    if (!isAvailable || !isEnabled) {
      return { success: false, error: '生体認証が有効になっていません' };
    }

    setIsLoading(true);
    setError(null);

    try {
      // 保存されている認証情報IDを取得
      const storedCredentialId = localStorage.getItem(CREDENTIAL_ID_KEY);
      if (!storedCredentialId) {
        throw new Error('生体認証が登録されていません');
      }

      // Base64デコード
      const credentialIdBytes = Uint8Array.from(atob(storedCredentialId), (c) =>
        c.charCodeAt(0)
      );

      // チャレンジを生成
      const challenge = new Uint8Array(32);
      crypto.getRandomValues(challenge);

      // 認証オプション
      const publicKeyCredentialRequestOptions: PublicKeyCredentialRequestOptions = {
        challenge,
        allowCredentials: [
          {
            id: credentialIdBytes,
            type: 'public-key',
            transports: ['internal'],
          },
        ],
        userVerification: 'required',
        timeout: 60000,
        rpId: window.location.hostname,
      };

      // 認証を実行
      const assertion = (await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions,
      })) as PublicKeyCredential;

      if (!assertion) {
        throw new Error('認証に失敗しました');
      }

      setIsLoading(false);
      return { success: true, credentialId: storedCredentialId };
    } catch (err) {
      let errorMessage = '生体認証に失敗しました';

      if (err instanceof DOMException) {
        switch (err.name) {
          case 'NotAllowedError':
            errorMessage = '生体認証がキャンセルされました';
            break;
          case 'SecurityError':
            errorMessage = 'セキュリティエラーが発生しました';
            break;
          case 'AbortError':
            errorMessage = '認証がタイムアウトしました';
            break;
        }
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }

      setError(errorMessage);
      setIsLoading(false);
      return { success: false, error: errorMessage };
    }
  }, [isAvailable, isEnabled]);

  return {
    isAvailable,
    isEnabled,
    isSupported,
    isLoading,
    error,
    enableBiometric,
    disableBiometric,
    authenticate,
    getRegisteredEmail,
  };
}

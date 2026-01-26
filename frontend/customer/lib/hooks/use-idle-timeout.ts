/**
 * useIdleTimeout - アイドルタイムアウト管理フック
 *
 * 指定時間操作がない場合に自動ログアウトを実行
 */
'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { logout } from '@/lib/api/auth';
import { useToast } from '@/hooks/use-toast';

// デフォルトタイムアウト: 30分
const DEFAULT_TIMEOUT_MS = 30 * 60 * 1000;

// 警告表示: タイムアウト1分前
const WARNING_BEFORE_MS = 60 * 1000;

// 監視するイベント
const ACTIVITY_EVENTS = [
  'mousedown',
  'mousemove',
  'keydown',
  'scroll',
  'touchstart',
  'click',
  'wheel',
];

interface UseIdleTimeoutOptions {
  /** タイムアウト時間（ミリ秒） */
  timeout?: number;
  /** 警告を表示するかどうか */
  showWarning?: boolean;
  /** タイムアウト時のコールバック */
  onTimeout?: () => void;
  /** 警告時のコールバック */
  onWarning?: () => void;
  /** 無効にするかどうか */
  disabled?: boolean;
}

export function useIdleTimeout(options: UseIdleTimeoutOptions = {}) {
  const {
    timeout = DEFAULT_TIMEOUT_MS,
    showWarning = true,
    onTimeout,
    onWarning,
    disabled = false,
  } = options;

  const router = useRouter();
  const { toast } = useToast();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const warningShownRef = useRef<boolean>(false);

  // タイマーをクリア
  const clearTimers = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (warningRef.current) {
      clearTimeout(warningRef.current);
      warningRef.current = null;
    }
  }, []);

  // ログアウト処理
  const handleTimeout = useCallback(async () => {
    clearTimers();

    try {
      await logout();
    } catch {
      // ログアウトAPIが失敗してもリダイレクト
    }

    // カスタムコールバック
    if (onTimeout) {
      onTimeout();
    }

    // トースト表示
    toast({
      title: 'セッションタイムアウト',
      description: '30分間操作がなかったため、自動的にログアウトしました。',
      variant: 'destructive',
    });

    // ログインページにリダイレクト
    router.push('/login');
  }, [clearTimers, onTimeout, router, toast]);

  // 警告表示
  const handleWarning = useCallback(() => {
    if (warningShownRef.current) return;
    warningShownRef.current = true;

    // カスタムコールバック
    if (onWarning) {
      onWarning();
    }

    // 警告トースト
    toast({
      title: 'セッションタイムアウト警告',
      description: 'まもなくセッションがタイムアウトします。操作を続けてください。',
      duration: 10000,
    });
  }, [onWarning, toast]);

  // タイマーをリセット
  const resetTimer = useCallback(() => {
    if (disabled) return;

    lastActivityRef.current = Date.now();
    warningShownRef.current = false;
    clearTimers();

    // 警告タイマー
    if (showWarning && timeout > WARNING_BEFORE_MS) {
      warningRef.current = setTimeout(handleWarning, timeout - WARNING_BEFORE_MS);
    }

    // タイムアウトタイマー
    timeoutRef.current = setTimeout(handleTimeout, timeout);
  }, [disabled, clearTimers, showWarning, timeout, handleWarning, handleTimeout]);

  // アクティビティ検出
  const handleActivity = useCallback(() => {
    // 最後のアクティビティからの経過時間をチェック
    const now = Date.now();
    const elapsed = now - lastActivityRef.current;

    // スロットリング: 1秒以内の連続イベントは無視
    if (elapsed < 1000) return;

    resetTimer();
  }, [resetTimer]);

  // イベントリスナーの設定
  useEffect(() => {
    if (disabled) {
      clearTimers();
      return;
    }

    // 認証状態をチェック
    const token = localStorage.getItem('access_token');
    if (!token) {
      clearTimers();
      return;
    }

    // 初期タイマー設定
    resetTimer();

    // イベントリスナー登録
    ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    // Visibility Change (タブがアクティブになった時)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // タブがアクティブになった時、経過時間をチェック
        const elapsed = Date.now() - lastActivityRef.current;
        if (elapsed >= timeout) {
          handleTimeout();
        } else {
          resetTimer();
        }
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // クリーンアップ
    return () => {
      clearTimers();
      ACTIVITY_EVENTS.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [disabled, clearTimers, resetTimer, handleActivity, handleTimeout, timeout]);

  return {
    /** 残り時間を取得 */
    getRemainingTime: () => {
      const elapsed = Date.now() - lastActivityRef.current;
      return Math.max(0, timeout - elapsed);
    },
    /** 手動でタイマーをリセット */
    resetTimer,
    /** 手動でログアウト */
    forceLogout: handleTimeout,
  };
}

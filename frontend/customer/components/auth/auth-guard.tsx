'use client';

/**
 * AuthGuard - 認証保護コンポーネント
 *
 * 認証が必要なページをラップして、未認証ユーザーをログインページへリダイレクト
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAccessToken } from '@/lib/api/client';
import { Loader2 } from 'lucide-react';

interface AuthGuardProps {
  children: React.ReactNode;
  /** 未認証時のリダイレクト先（デフォルト: /login） */
  redirectTo?: string;
  /** ローディング中に表示するコンポーネント */
  fallback?: React.ReactNode;
}

/**
 * 認証が必要なページをラップするコンポーネント
 *
 * @example
 * export default function ProtectedPage() {
 *   return (
 *     <AuthGuard>
 *       <MyContent />
 *     </AuthGuard>
 *   );
 * }
 */
export function AuthGuard({
  children,
  redirectTo = '/login',
  fallback,
}: AuthGuardProps) {
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);

  useEffect(() => {
    const token = getAccessToken();

    if (!token) {
      // 未認証の場合はリダイレクト
      router.replace(redirectTo);
    } else {
      setIsAuthorized(true);
    }
  }, [router, redirectTo]);

  // 認証チェック中
  if (isAuthorized === null) {
    return fallback || <DefaultLoadingFallback />;
  }

  // 未認証（リダイレクト中）
  if (!isAuthorized) {
    return fallback || <DefaultLoadingFallback />;
  }

  return <>{children}</>;
}

/**
 * デフォルトのローディング表示
 */
function DefaultLoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto" />
        <p className="mt-2 text-sm text-gray-600">読み込み中...</p>
      </div>
    </div>
  );
}

/**
 * 認証済みユーザーを別ページへリダイレクト（ログインページ等で使用）
 *
 * @example
 * export default function LoginPage() {
 *   return (
 *     <GuestGuard>
 *       <LoginForm />
 *     </GuestGuard>
 *   );
 * }
 */
export function GuestGuard({
  children,
  redirectTo = '/feed',
}: Omit<AuthGuardProps, 'fallback'>) {
  const router = useRouter();
  const [isGuest, setIsGuest] = useState<boolean | null>(null);

  useEffect(() => {
    const token = getAccessToken();

    if (token) {
      // 認証済みの場合はリダイレクト
      router.replace(redirectTo);
    } else {
      setIsGuest(true);
    }
  }, [router, redirectTo]);

  // チェック中
  if (isGuest === null) {
    return <DefaultLoadingFallback />;
  }

  // 認証済み（リダイレクト中）
  if (!isGuest) {
    return <DefaultLoadingFallback />;
  }

  return <>{children}</>;
}

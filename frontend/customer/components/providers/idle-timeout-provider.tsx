/**
 * IdleTimeoutProvider - アイドルタイムアウト管理プロバイダー
 *
 * アプリケーション全体で30分のアイドルタイムアウトを管理
 */
'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { useIdleTimeout } from '@/lib/hooks/use-idle-timeout';

// タイムアウトを適用しないパス
const EXCLUDED_PATHS = [
  '/login',
  '/signup',
  '/password-reset',
  '/trial',
  '/map',
];

interface IdleTimeoutProviderProps {
  children: React.ReactNode;
}

export function IdleTimeoutProvider({ children }: IdleTimeoutProviderProps) {
  const pathname = usePathname();
  const [isClient, setIsClient] = useState(false);

  // クライアントサイドでのみ実行
  useEffect(() => {
    setIsClient(true);
  }, []);

  // 現在のパスがタイムアウト対象外かどうか
  const isExcluded = EXCLUDED_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );

  // タイムアウトフック（30分）
  useIdleTimeout({
    timeout: 30 * 60 * 1000, // 30分
    showWarning: true,
    disabled: !isClient || isExcluded,
  });

  return <>{children}</>;
}

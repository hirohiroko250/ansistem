'use client';

/**
 * App Providers - アプリケーション全体のプロバイダー
 *
 * React Query, Toast, Theme などのプロバイダーをまとめて提供
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Toaster } from '@/components/ui/toaster';

// デフォルトのクエリクライアント設定
const defaultQueryClientOptions = {
  queries: {
    // データが古くなるまでの時間（5分）
    staleTime: 5 * 60 * 1000,
    // キャッシュを保持する時間（30分）
    gcTime: 30 * 60 * 1000,
    // リトライ回数
    retry: 1,
    // ウィンドウフォーカス時の再取得を無効化
    refetchOnWindowFocus: false,
    // マウント時の再取得
    refetchOnMount: true,
  },
  mutations: {
    // ミューテーションのリトライは無効
    retry: false,
  },
};

export function Providers({ children }: { children: React.ReactNode }) {
  // クライアントコンポーネントでQueryClientを作成
  // useStateを使用して、サーバー/クライアント間で同じインスタンスを維持
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: defaultQueryClientOptions })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster />
    </QueryClientProvider>
  );
}

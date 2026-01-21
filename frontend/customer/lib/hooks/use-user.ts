'use client';

/**
 * useUser - ユーザー情報取得フック
 *
 * 現在ログイン中のユーザー情報を取得・管理するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, getAccessToken } from '@/lib/api/client';
import type { Profile } from '@/lib/api/types';

// クエリキー
export const userKeys = {
  all: ['user'] as const,
  me: () => [...userKeys.all, 'me'] as const,
  profile: () => [...userKeys.all, 'profile'] as const,
};

/**
 * 現在のユーザー情報を取得
 */
export function useUser() {
  return useQuery({
    queryKey: userKeys.me(),
    queryFn: async () => {
      const response = await api.get<Profile>('/auth/me/');
      return response;
    },
    // トークンがある場合のみ有効
    enabled: !!getAccessToken(),
    // ユーザー情報は頻繁に変わらないのでキャッシュを長めに
    staleTime: 10 * 60 * 1000, // 10分
    gcTime: 60 * 60 * 1000, // 1時間
  });
}

/**
 * ユーザープロフィール更新
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<Profile>) => {
      const response = await api.patch<Profile>('/auth/me/', data);
      return response;
    },
    onSuccess: (data: Profile) => {
      // キャッシュを更新
      queryClient.setQueryData(userKeys.me(), data);
    },
  });
}

/**
 * ログイン状態を確認
 */
export function useIsLoggedIn(): boolean {
  const { data, isLoading } = useUser();
  if (isLoading) return false;
  return !!data?.id;
}

/**
 * ユーザーキャッシュを無効化（ログアウト時等に使用）
 */
export function useInvalidateUser() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.removeQueries({ queryKey: userKeys.all });
  };
}

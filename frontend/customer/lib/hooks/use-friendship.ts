'use client';

/**
 * useFriendship - 友達紹介フック
 *
 * 友達紹介コード、友達リスト、割引情報を管理するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getMyReferralCode,
  getFriendsList,
  getFSDiscounts,
  registerFriend,
  acceptFriendRequest,
  rejectFriendRequest,
  type MyCodeResponse,
  type FriendsListResponse,
  type DiscountsResponse,
} from '@/lib/api/friendship';

// クエリキー
export const friendshipKeys = {
  all: ['friendship'] as const,
  referralCode: () => [...friendshipKeys.all, 'referralCode'] as const,
  friendsList: () => [...friendshipKeys.all, 'friendsList'] as const,
  discounts: () => [...friendshipKeys.all, 'discounts'] as const,
};

/**
 * 自分の紹介コードを取得
 */
export function useMyReferralCode() {
  return useQuery({
    queryKey: friendshipKeys.referralCode(),
    queryFn: async () => {
      return getMyReferralCode();
    },
    enabled: !!getAccessToken(),
    staleTime: 30 * 60 * 1000, // 30分
  });
}

/**
 * 友達リストを取得
 */
export function useFriendsList() {
  return useQuery({
    queryKey: friendshipKeys.friendsList(),
    queryFn: async () => {
      return getFriendsList();
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 友達割引情報を取得
 */
export function useFSDiscounts() {
  return useQuery({
    queryKey: friendshipKeys.discounts(),
    queryFn: async () => {
      return getFSDiscounts();
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 友達登録
 */
export function useRegisterFriend() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (referralCode: string) => {
      return registerFriend(referralCode);
    },
    onSuccess: () => {
      // 友達リストを再取得
      queryClient.invalidateQueries({ queryKey: friendshipKeys.friendsList() });
    },
  });
}

/**
 * 友達リクエスト承認
 */
export function useAcceptFriendRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (friendshipId: string) => {
      return acceptFriendRequest(friendshipId);
    },
    onSuccess: () => {
      // 友達リストと割引情報を再取得
      queryClient.invalidateQueries({ queryKey: friendshipKeys.friendsList() });
      queryClient.invalidateQueries({ queryKey: friendshipKeys.discounts() });
    },
  });
}

/**
 * 友達リクエスト拒否
 */
export function useRejectFriendRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (friendshipId: string) => {
      return rejectFriendRequest(friendshipId);
    },
    onSuccess: () => {
      // 友達リストを再取得
      queryClient.invalidateQueries({ queryKey: friendshipKeys.friendsList() });
    },
  });
}

/**
 * 友達関連キャッシュを無効化
 */
export function useInvalidateFriendship() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: friendshipKeys.all });
  };
}

// 型を再エクスポート
export type {
  MyCodeResponse,
  FriendsListResponse,
  DiscountsResponse,
} from '@/lib/api/friendship';

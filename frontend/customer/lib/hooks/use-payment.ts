'use client';

/**
 * usePayment - 支払い情報フック
 *
 * 支払い情報・通帳データを取得するReact Queryフック
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getMyPayment,
  getMyPassbook,
  type PaymentInfo,
  type PassbookData,
} from '@/lib/api/payment';

// クエリキー
export const paymentKeys = {
  all: ['payment'] as const,
  info: () => [...paymentKeys.all, 'info'] as const,
  passbook: () => [...paymentKeys.all, 'passbook'] as const,
};

/**
 * 支払い情報を取得
 */
export function usePaymentInfo() {
  return useQuery({
    queryKey: paymentKeys.info(),
    queryFn: async () => {
      return getMyPayment();
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 通帳データを取得
 */
export function usePassbookData(enabled: boolean = true) {
  return useQuery({
    queryKey: paymentKeys.passbook(),
    queryFn: async () => {
      return getMyPassbook();
    },
    enabled: enabled && !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * 支払い情報キャッシュを無効化
 */
export function useInvalidatePayment() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: paymentKeys.all });
  };
}

// 型を再エクスポート
export type { PaymentInfo, PassbookData } from '@/lib/api/payment';

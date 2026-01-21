'use client';

/**
 * usePayment - 支払い情報フック
 *
 * 支払い情報・通帳データ・銀行口座管理を行うReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getMyPayment,
  getMyPassbook,
  getMyBankAccounts,
  getMyBankAccountRequests,
  createBankAccountRequest,
  cancelBankAccountRequest,
  type PaymentInfo,
  type PassbookData,
  type BankAccount,
  type BankAccountRequest,
  type BankAccountRequestData,
} from '@/lib/api/payment';

// クエリキー
export const paymentKeys = {
  all: ['payment'] as const,
  info: () => [...paymentKeys.all, 'info'] as const,
  passbook: () => [...paymentKeys.all, 'passbook'] as const,
  bankAccounts: () => [...paymentKeys.all, 'bankAccounts'] as const,
  bankAccountRequests: () => [...paymentKeys.all, 'bankAccountRequests'] as const,
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
 * 銀行口座一覧を取得
 */
export function useMyBankAccounts(enabled: boolean = true) {
  return useQuery({
    queryKey: paymentKeys.bankAccounts(),
    queryFn: async () => {
      return getMyBankAccounts();
    },
    enabled: enabled && !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 銀行口座変更申請一覧を取得
 */
export function useMyBankAccountRequests(enabled: boolean = true) {
  return useQuery({
    queryKey: paymentKeys.bankAccountRequests(),
    queryFn: async () => {
      return getMyBankAccountRequests();
    },
    enabled: enabled && !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * 銀行口座変更申請を作成
 */
export function useCreateBankAccountRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: BankAccountRequestData) => {
      return createBankAccountRequest(data);
    },
    onSuccess: () => {
      // 関連データを再取得
      queryClient.invalidateQueries({ queryKey: paymentKeys.bankAccounts() });
      queryClient.invalidateQueries({ queryKey: paymentKeys.bankAccountRequests() });
      queryClient.invalidateQueries({ queryKey: paymentKeys.info() });
    },
  });
}

/**
 * 銀行口座変更申請をキャンセル
 */
export function useCancelBankAccountRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return cancelBankAccountRequest(id);
    },
    onSuccess: () => {
      // 申請一覧を再取得
      queryClient.invalidateQueries({ queryKey: paymentKeys.bankAccountRequests() });
    },
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
export type {
  PaymentInfo,
  PassbookData,
  BankAccount,
  BankAccountRequest,
  BankAccountRequestData,
} from '@/lib/api/payment';

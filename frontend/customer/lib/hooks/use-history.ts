'use client';

/**
 * useHistory - 履歴取得フック
 *
 * 欠席チケット、購入履歴などの履歴取得React Queryフック
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getAbsenceTickets,
  type AbsenceTicket,
} from '@/lib/api/lessons';
import {
  getAllStudentItems,
  type AllStudentItemsResponse,
} from '@/lib/api/students';

// クエリキー
export const historyKeys = {
  all: ['history'] as const,
  absenceTickets: () => [...historyKeys.all, 'absenceTickets'] as const,
  absenceTicketsByStatus: (status?: 'issued' | 'used' | 'expired') =>
    [...historyKeys.absenceTickets(), status] as const,
  purchaseHistory: () => [...historyKeys.all, 'purchases'] as const,
  purchaseHistoryByMonth: (billingMonth?: string) =>
    [...historyKeys.purchaseHistory(), billingMonth] as const,
};

/**
 * 欠席チケット一覧を取得
 */
export function useAbsenceTickets(status?: 'issued' | 'used' | 'expired') {
  return useQuery({
    queryKey: historyKeys.absenceTicketsByStatus(status),
    queryFn: async () => {
      return getAbsenceTickets(status);
    },
    enabled: !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * 購入履歴（全子ども）を取得
 */
export function usePurchaseHistory(billingMonth?: string) {
  return useQuery({
    queryKey: historyKeys.purchaseHistoryByMonth(billingMonth),
    queryFn: async () => {
      return getAllStudentItems(billingMonth);
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

// 履歴アイテム型（統合用）
export type HistoryItem = {
  id: string;
  type: 'absence' | 'makeup' | 'ticket_purchase' | 'event' | 'withdrawal' | 'suspension';
  title: string;
  description: string;
  date: string;
  status?: string;
  childName?: string;
};

/**
 * 統合履歴データを取得
 * 欠席チケットと購入履歴を統合して返す
 */
export function useCombinedHistory() {
  const absenceTicketsQuery = useAbsenceTickets();
  const purchaseHistoryQuery = usePurchaseHistory();

  return useQuery({
    queryKey: [...historyKeys.all, 'combined'],
    queryFn: async () => {
      const items: HistoryItem[] = [];

      // 欠席チケットからの履歴
      const absenceTickets = absenceTicketsQuery.data || [];
      absenceTickets.forEach((ticket: AbsenceTicket) => {
        // 欠席履歴
        if (ticket.absenceDate) {
          items.push({
            id: `absence-${ticket.id}`,
            type: 'absence',
            title: '欠席登録',
            description: ticket.originalTicketName || ticket.brandName || '授業',
            date: ticket.absenceDate,
            status: ticket.status === 'issued' ? '振替チケット発行済' :
                    ticket.status === 'used' ? '振替済' :
                    ticket.status === 'expired' ? '期限切れ' : '',
            childName: ticket.studentName,
          });
        }

        // 振替履歴
        if (ticket.status === 'used' && ticket.usedDate) {
          items.push({
            id: `makeup-${ticket.id}`,
            type: 'makeup',
            title: '振替受講',
            description: ticket.originalTicketName || ticket.brandName || '授業',
            date: ticket.usedDate,
            childName: ticket.studentName,
          });
        }
      });

      // 購入履歴
      const purchaseData = purchaseHistoryQuery.data;
      if (purchaseData?.items) {
        purchaseData.items.forEach((item) => {
          if (item.productType === 'ticket' || item.productName.includes('チケット')) {
            items.push({
              id: `purchase-${item.id}`,
              type: 'ticket_purchase',
              title: 'チケット購入',
              description: item.productName,
              date: item.billingMonth + '-01',
              childName: item.studentName,
            });
          }
        });
      }

      // 日付で降順ソート
      items.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateB.getTime() - dateA.getTime();
      });

      return items;
    },
    enabled: !!getAccessToken() && !absenceTicketsQuery.isLoading && !purchaseHistoryQuery.isLoading,
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * 履歴キャッシュを無効化
 */
export function useInvalidateHistory() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: historyKeys.all });
  };
}

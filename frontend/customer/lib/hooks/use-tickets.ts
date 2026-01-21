'use client';

/**
 * useTickets - チケット情報取得フック
 *
 * チケット残高・履歴を取得するReact Queryフック
 */

import { useQuery } from '@tanstack/react-query';
import { api, getAccessToken } from '@/lib/api/client';
import type { TicketBalance, TicketLog } from '@/lib/api/types';

// クエリキー
export const ticketKeys = {
  all: ['tickets'] as const,
  balances: () => [...ticketKeys.all, 'balances'] as const,
  balance: (studentId: string) => [...ticketKeys.balances(), studentId] as const,
  logs: (studentId: string) => [...ticketKeys.all, 'logs', studentId] as const,
};

interface TicketBalanceResponse {
  balance: TicketBalance;
}

interface TicketLogsResponse {
  logs: TicketLog[];
  count?: number;
}

/**
 * 生徒のチケット残高を取得
 */
export function useTicketBalance(studentId: string | undefined) {
  return useQuery({
    queryKey: ticketKeys.balance(studentId || ''),
    queryFn: async () => {
      if (!studentId) throw new Error('Student ID is required');
      const response = await api.get<TicketBalanceResponse>(
        `/students/children/${studentId}/tickets/`
      );
      return response.balance;
    },
    enabled: !!studentId && !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分（チケットは頻繁に更新される可能性がある）
  });
}

/**
 * 生徒のチケット履歴を取得
 */
export function useTicketLogs(studentId: string | undefined) {
  return useQuery({
    queryKey: ticketKeys.logs(studentId || ''),
    queryFn: async () => {
      if (!studentId) throw new Error('Student ID is required');
      const response = await api.get<TicketLogsResponse>(
        `/students/children/${studentId}/tickets/logs/`
      );
      return response.logs || [];
    },
    enabled: !!studentId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 全生徒のチケット残高一覧を取得
 */
export function useAllTicketBalances() {
  return useQuery({
    queryKey: ticketKeys.balances(),
    queryFn: async () => {
      const response = await api.get<{ balances: TicketBalance[] }>(
        '/students/children/tickets/'
      );
      return response.balances || [];
    },
    enabled: !!getAccessToken(),
    staleTime: 2 * 60 * 1000,
  });
}

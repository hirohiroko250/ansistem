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

// ==============================================
// 保有チケット一覧（チケットページ用）
// ==============================================

import { useQueryClient } from '@tanstack/react-query';
import {
  getAllStudentItems,
  type PurchasedItem,
} from '@/lib/api/students';
import {
  getAbsenceTickets,
  type AbsenceTicket,
} from '@/lib/api/lessons';

// チケット種別
export type OwnedTicketType = {
  id: string;
  type: 'course' | 'transfer' | 'event';
  school: string;
  brand: string;
  count: number;
  expiryDate: string;
  status: 'active' | 'expiring';
  studentName?: string;
  productName?: string;
  billingMonth?: string;
  absenceDate?: string;
  consumptionSymbol?: string;
  originalTicketName?: string;
  brandId?: string;
  schoolId?: string;
};

// ヘルパー関数
function isTicketType(productType: string): boolean {
  return productType === 'tuition';
}

function calculateExpiryDate(billingMonth: string): string {
  const [year, month] = billingMonth.split('-').map(Number);
  const expiry = new Date(year, month + 2, 0);
  return expiry.toISOString().split('T')[0];
}

function isExpiringSoon(expiryDate: string): boolean {
  const expiry = new Date(expiryDate);
  const now = new Date();
  const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  return diffDays <= 30 && diffDays > 0;
}

/**
 * 保有チケット一覧を取得（コース + 振替チケット統合）
 */
export function useOwnedTickets() {
  return useQuery({
    queryKey: [...ticketKeys.all, 'owned'],
    queryFn: async () => {
      // コースチケットと振替チケットを並行取得
      const [itemsResponse, absenceTickets] = await Promise.all([
        getAllStudentItems(),
        getAbsenceTickets('issued').catch(() => [] as AbsenceTicket[]),
      ]);

      // 授業料のみをチケットとして表示
      const ticketItems = itemsResponse.items.filter((item: PurchasedItem) => isTicketType(item.productType));

      // PurchasedItemをOwnedTicketTypeに変換
      const courseTickets: OwnedTicketType[] = ticketItems.map((item: PurchasedItem) => {
        const expiryDate = calculateExpiryDate(item.billingMonth);
        return {
          id: item.id,
          type: 'course' as const,
          school: item.schoolName || '未指定',
          brand: item.brandName || item.productName,
          count: item.quantity,
          expiryDate,
          status: isExpiringSoon(expiryDate) ? 'expiring' : 'active',
          studentName: item.studentName,
          productName: item.productName,
          billingMonth: item.billingMonth,
        };
      });

      // AbsenceTicketをOwnedTicketTypeに変換
      const transferTickets: OwnedTicketType[] = absenceTickets.map((ticket: AbsenceTicket) => ({
        id: ticket.id,
        type: 'transfer' as const,
        school: ticket.schoolName || '未指定',
        brand: ticket.brandName || '振替チケット',
        count: 1,
        expiryDate: ticket.validUntil || '',
        status: ticket.validUntil && isExpiringSoon(ticket.validUntil) ? 'expiring' : 'active',
        studentName: ticket.studentName,
        productName: ticket.originalTicketName || '振替チケット',
        absenceDate: ticket.absenceDate || undefined,
        consumptionSymbol: ticket.consumptionSymbol,
        originalTicketName: ticket.originalTicketName,
        brandId: ticket.brandId || undefined,
        schoolId: ticket.schoolId || undefined,
      }));

      return [...courseTickets, ...transferTickets];
    },
    enabled: !!getAccessToken(),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * 保有チケットキャッシュを無効化
 */
export function useInvalidateOwnedTickets() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: [...ticketKeys.all, 'owned'] });
  };
}

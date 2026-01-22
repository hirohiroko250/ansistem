'use client';

/**
 * useClassManagement - クラス管理フック
 *
 * クラス変更、校舎変更、休会・退会申請、振替予約を管理するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getMyContracts,
  changeClass,
  changeSchool,
  requestSuspension,
  requestCancellation,
  type MyContract,
  type MyStudent,
  type ChangeClassRequest,
  type ChangeSchoolRequest,
  type RequestSuspensionRequest,
  type RequestCancellationRequest,
} from '@/lib/api/contracts';
import {
  getClassSchedules,
  getSchoolsByTicket,
  type ClassScheduleResponse,
  type BrandSchool,
} from '@/lib/api/schools';
import {
  getAbsenceTickets,
  getTransferAvailableClasses,
  consumeAbsenceTicket,
  type AbsenceTicket,
  type TransferAvailableClass,
  type UseAbsenceTicketRequest,
} from '@/lib/api/lessons';

// クエリキー
export const classManagementKeys = {
  all: ['classManagement'] as const,
  contracts: () => [...classManagementKeys.all, 'contracts'] as const,
  classSchedules: (schoolId: string, brandId: string, ticketId?: string) =>
    [...classManagementKeys.all, 'classSchedules', schoolId, brandId, ticketId] as const,
  schoolsByTicket: (ticketCode: string, brandId?: string) =>
    [...classManagementKeys.all, 'schoolsByTicket', ticketCode, brandId] as const,
  absenceTickets: (status?: string) =>
    [...classManagementKeys.all, 'absenceTickets', status] as const,
  transferAvailableClasses: (ticketId: string) =>
    [...classManagementKeys.all, 'transferAvailableClasses', ticketId] as const,
};

/**
 * 契約情報を取得
 */
export function useMyContracts() {
  return useQuery({
    queryKey: classManagementKeys.contracts(),
    queryFn: async () => {
      return getMyContracts();
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 開講時間割を取得
 */
export function useClassSchedules(
  schoolId: string | undefined,
  brandId: string | undefined,
  brandCategoryId?: string,
  ticketId?: string
) {
  return useQuery({
    queryKey: classManagementKeys.classSchedules(schoolId || '', brandId || '', ticketId),
    queryFn: async () => {
      if (!schoolId || !brandId) throw new Error('School ID and Brand ID are required');
      return getClassSchedules(schoolId, brandId, brandCategoryId, ticketId);
    },
    enabled: !!schoolId && !!brandId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * チケットで開講校舎を取得
 */
export function useSchoolsByTicket(ticketCode: string | undefined, brandId?: string) {
  return useQuery({
    queryKey: classManagementKeys.schoolsByTicket(ticketCode || '', brandId),
    queryFn: async () => {
      if (!ticketCode) throw new Error('Ticket code is required');
      return getSchoolsByTicket(ticketCode, brandId);
    },
    enabled: !!ticketCode && !!getAccessToken(),
    staleTime: 10 * 60 * 1000, // 10分
  });
}

/**
 * 欠席チケット一覧を取得
 */
export function useAbsenceTicketsQuery(
  status?: 'issued' | 'used' | 'expired',
  enabled: boolean = true
) {
  return useQuery({
    queryKey: classManagementKeys.absenceTickets(status),
    queryFn: async () => {
      return getAbsenceTickets(status);
    },
    enabled: enabled && !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * 振替可能クラスを取得
 */
export function useTransferAvailableClasses(ticketId: string | undefined, enabled: boolean = true) {
  return useQuery({
    queryKey: classManagementKeys.transferAvailableClasses(ticketId || ''),
    queryFn: async () => {
      if (!ticketId) throw new Error('Ticket ID is required');
      return getTransferAvailableClasses(ticketId);
    },
    enabled: enabled && !!ticketId && !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * クラス変更
 */
export function useChangeClass() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ contractId, data }: { contractId: string; data: ChangeClassRequest }) => {
      return changeClass(contractId, data);
    },
    onSuccess: () => {
      // 契約情報を再取得
      queryClient.invalidateQueries({ queryKey: classManagementKeys.contracts() });
    },
  });
}

/**
 * 校舎変更
 */
export function useChangeSchool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ contractId, data }: { contractId: string; data: ChangeSchoolRequest }) => {
      return changeSchool(contractId, data);
    },
    onSuccess: () => {
      // 契約情報を再取得
      queryClient.invalidateQueries({ queryKey: classManagementKeys.contracts() });
    },
  });
}

/**
 * 休会申請
 */
export function useRequestSuspension() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ contractId, data }: { contractId: string; data: RequestSuspensionRequest }) => {
      return requestSuspension(contractId, data);
    },
    onSuccess: () => {
      // 契約情報を再取得
      queryClient.invalidateQueries({ queryKey: classManagementKeys.contracts() });
    },
  });
}

/**
 * 退会申請
 */
export function useRequestCancellation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ contractId, data }: { contractId: string; data: RequestCancellationRequest }) => {
      return requestCancellation(contractId, data);
    },
    onSuccess: () => {
      // 契約情報を再取得
      queryClient.invalidateQueries({ queryKey: classManagementKeys.contracts() });
    },
  });
}

/**
 * 欠席チケット使用（振替予約）
 */
export function useConsumeAbsenceTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UseAbsenceTicketRequest) => {
      return consumeAbsenceTicket(data);
    },
    onSuccess: () => {
      // 欠席チケット一覧を再取得
      queryClient.invalidateQueries({ queryKey: classManagementKeys.absenceTickets() });
    },
  });
}

/**
 * クラス管理関連キャッシュを無効化
 */
export function useInvalidateClassManagement() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: classManagementKeys.all });
  };
}

// 型を再エクスポート
export type {
  MyContract,
  MyStudent,
  ChangeClassRequest,
  ChangeSchoolRequest,
  RequestSuspensionRequest,
  RequestCancellationRequest,
} from '@/lib/api/contracts';
export type { ClassScheduleResponse, BrandSchool } from '@/lib/api/schools';
export type { AbsenceTicket, TransferAvailableClass, UseAbsenceTicketRequest } from '@/lib/api/lessons';

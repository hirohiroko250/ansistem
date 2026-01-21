'use client';

/**
 * useStaffStudents - 生徒管理フック（スタッフ向け）
 *
 * スタッフ向け生徒管理のReact Queryフック
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getStudents,
  getStudentDetail,
  getStudentTicketBalance,
  getStudentGuardians,
  type StaffStudent,
  type StudentSearchParams,
  type Guardian,
} from '@/lib/api/students';
import type { TicketBalance } from '@/lib/api/types';

// クエリキー
export const staffStudentKeys = {
  all: ['staff-students'] as const,
  lists: () => [...staffStudentKeys.all, 'list'] as const,
  list: (filters?: StudentSearchParams) =>
    [...staffStudentKeys.lists(), filters] as const,
  details: () => [...staffStudentKeys.all, 'detail'] as const,
  detail: (id: string) => [...staffStudentKeys.details(), id] as const,
  tickets: (id: string) => [...staffStudentKeys.all, 'tickets', id] as const,
  guardians: (id: string) => [...staffStudentKeys.all, 'guardians', id] as const,
};

/**
 * 生徒一覧を取得（スタッフ向け）
 */
export function useStaffStudents(params?: StudentSearchParams) {
  return useQuery({
    queryKey: staffStudentKeys.list(params),
    queryFn: async () => {
      const response = await getStudents(params);
      return {
        students: response.results || [],
        count: response.count || 0,
        hasNext: !!response.next,
        hasPrev: !!response.previous,
      };
    },
    enabled: !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * 生徒詳細を取得（スタッフ向け）
 */
export function useStaffStudent(studentId: string | undefined) {
  return useQuery({
    queryKey: staffStudentKeys.detail(studentId || ''),
    queryFn: async () => {
      if (!studentId) throw new Error('Student ID is required');
      return getStudentDetail(studentId);
    },
    enabled: !!studentId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 生徒のチケット残高を取得（スタッフ向け）
 */
export function useStaffStudentTickets(studentId: string | undefined) {
  return useQuery({
    queryKey: staffStudentKeys.tickets(studentId || ''),
    queryFn: async () => {
      if (!studentId) throw new Error('Student ID is required');
      return getStudentTicketBalance(studentId);
    },
    enabled: !!studentId && !!getAccessToken(),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * 生徒の保護者一覧を取得
 */
export function useStudentGuardians(studentId: string | undefined) {
  return useQuery({
    queryKey: staffStudentKeys.guardians(studentId || ''),
    queryFn: async () => {
      if (!studentId) throw new Error('Student ID is required');
      return getStudentGuardians(studentId);
    },
    enabled: !!studentId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * 生徒キャッシュを無効化（スタッフ向け）
 */
export function useInvalidateStaffStudents() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: staffStudentKeys.all });
  };
}

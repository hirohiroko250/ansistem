'use client';

/**
 * useStudents - 生徒（子ども）情報取得フック
 *
 * 保護者の子ども一覧を取得・管理するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, getAccessToken } from '@/lib/api/client';
import type { Child, ChildDetail } from '@/lib/api/types';

// クエリキー
export const studentKeys = {
  all: ['students'] as const,
  lists: () => [...studentKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) =>
    [...studentKeys.lists(), filters] as const,
  details: () => [...studentKeys.all, 'detail'] as const,
  detail: (id: string) => [...studentKeys.details(), id] as const,
};

interface StudentsResponse {
  students: Child[];
  count?: number;
}

/**
 * 生徒一覧を取得
 */
export function useStudents() {
  return useQuery({
    queryKey: studentKeys.lists(),
    queryFn: async () => {
      const response = await api.get<StudentsResponse>('/students/children/');
      return response.students || [];
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 特定の生徒の詳細を取得
 */
export function useStudent(studentId: string | undefined) {
  return useQuery({
    queryKey: studentKeys.detail(studentId || ''),
    queryFn: async () => {
      if (!studentId) throw new Error('Student ID is required');
      const response = await api.get<ChildDetail>(`/students/children/${studentId}/`);
      return response;
    },
    enabled: !!studentId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

interface AddStudentData {
  lastName: string;
  firstName: string;
  lastNameKana?: string;
  firstNameKana?: string;
  birthDate?: string;
  gender?: string;
  gradeId?: string;
  gradeText?: string;
  schoolId?: string;
  brandId?: string;
}

/**
 * 生徒を追加
 */
export function useAddStudent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AddStudentData) => {
      // snake_case に変換
      const payload = {
        last_name: data.lastName,
        first_name: data.firstName,
        last_name_kana: data.lastNameKana,
        first_name_kana: data.firstNameKana,
        birth_date: data.birthDate,
        gender: data.gender,
        grade_id: data.gradeId,
        grade_text: data.gradeText,
        school_id: data.schoolId,
        brand_id: data.brandId,
      };
      const response = await api.post<{ student: Child }>('/onboarding/add-student/', payload);
      return response.student;
    },
    onSuccess: () => {
      // 生徒一覧のキャッシュを無効化
      queryClient.invalidateQueries({ queryKey: studentKeys.lists() });
    },
  });
}

/**
 * 生徒情報を更新
 */
export function useUpdateStudent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<AddStudentData> }) => {
      const payload = {
        last_name: data.lastName,
        first_name: data.firstName,
        last_name_kana: data.lastNameKana,
        first_name_kana: data.firstNameKana,
        birth_date: data.birthDate,
        gender: data.gender,
        grade_id: data.gradeId,
        grade_text: data.gradeText,
      };
      const response = await api.patch<Child>(`/students/children/${id}/`, payload);
      return response;
    },
    onSuccess: (data: Child, variables: { id: string; data: Partial<AddStudentData> }) => {
      // 詳細キャッシュを更新
      queryClient.setQueryData(studentKeys.detail(variables.id), data);
      // 一覧キャッシュを無効化
      queryClient.invalidateQueries({ queryKey: studentKeys.lists() });
    },
  });
}

/**
 * 生徒キャッシュを無効化
 */
export function useInvalidateStudents() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: studentKeys.all });
  };
}

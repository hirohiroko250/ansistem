'use client';

/**
 * useClasses - クラス詳細・出欠管理フック（講師向け）
 *
 * クラス詳細情報、生徒一覧、出欠更新、日報送信を管理するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getClassDetail,
  getClassStudents,
  getClassDailyReport,
  updateClassAttendance,
  submitClassDailyReport,
  type ClassDetail,
  type ClassStudent,
  type DailyReport,
  type UpdateClassAttendanceRequest,
} from '@/lib/api/lessons';

// クエリキー
export const classKeys = {
  all: ['classes'] as const,
  detail: (id: string) => [...classKeys.all, 'detail', id] as const,
  students: (id: string) => [...classKeys.all, 'students', id] as const,
  report: (id: string) => [...classKeys.all, 'report', id] as const,
};

/**
 * クラス詳細を取得
 */
export function useClassDetail(classId: string | undefined) {
  return useQuery({
    queryKey: classKeys.detail(classId || ''),
    queryFn: async () => {
      if (!classId) throw new Error('Class ID is required');
      return getClassDetail(classId);
    },
    enabled: !!classId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * クラスの生徒一覧を取得
 */
export function useClassStudents(classId: string | undefined) {
  return useQuery({
    queryKey: classKeys.students(classId || ''),
    queryFn: async () => {
      if (!classId) throw new Error('Class ID is required');
      return getClassStudents(classId);
    },
    enabled: !!classId && !!getAccessToken(),
    staleTime: 2 * 60 * 1000, // 2分
  });
}

/**
 * クラスの日報を取得
 */
export function useClassDailyReport(classId: string | undefined) {
  return useQuery({
    queryKey: classKeys.report(classId || ''),
    queryFn: async () => {
      if (!classId) throw new Error('Class ID is required');
      return getClassDailyReport(classId);
    },
    enabled: !!classId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * クラスの出欠を更新（楽観的更新付き）
 */
export function useUpdateAttendance(classId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: UpdateClassAttendanceRequest) => {
      return updateClassAttendance(classId, data);
    },
    onMutate: async (newData) => {
      // キャンセル中のクエリを待つ
      await queryClient.cancelQueries({ queryKey: classKeys.students(classId) });

      // 以前のデータをスナップショット
      const previousStudents = queryClient.getQueryData<ClassStudent[]>(
        classKeys.students(classId)
      );

      // 楽観的更新
      if (previousStudents) {
        queryClient.setQueryData<ClassStudent[]>(
          classKeys.students(classId),
          previousStudents.map((s) =>
            s.id === newData.studentId
              ? { ...s, attendanceStatus: newData.status }
              : s
          )
        );
      }

      return { previousStudents };
    },
    onError: (_err, _newData, context) => {
      // エラー時は元に戻す
      if (context?.previousStudents) {
        queryClient.setQueryData(
          classKeys.students(classId),
          context.previousStudents
        );
      }
    },
    onSettled: () => {
      // 成功・失敗に関わらずキャッシュを再検証
      queryClient.invalidateQueries({ queryKey: classKeys.students(classId) });
    },
  });
}

/**
 * 日報を送信
 */
export function useSubmitDailyReport(classId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (reportContent: string) => {
      return submitClassDailyReport(classId, reportContent);
    },
    onSuccess: (data) => {
      // キャッシュを更新
      queryClient.setQueryData<DailyReport | null>(
        classKeys.report(classId),
        data
      );
    },
  });
}

/**
 * クラス関連キャッシュを無効化
 */
export function useInvalidateClass() {
  const queryClient = useQueryClient();

  return (classId?: string) => {
    if (classId) {
      queryClient.invalidateQueries({ queryKey: classKeys.detail(classId) });
      queryClient.invalidateQueries({ queryKey: classKeys.students(classId) });
      queryClient.invalidateQueries({ queryKey: classKeys.report(classId) });
    } else {
      queryClient.invalidateQueries({ queryKey: classKeys.all });
    }
  };
}

// 型を再エクスポート
export type { ClassDetail, ClassStudent, DailyReport } from '@/lib/api/lessons';

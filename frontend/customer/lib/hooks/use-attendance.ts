'use client';

/**
 * useAttendance - 勤怠管理フック（講師・スタッフ向け）
 *
 * 出退勤打刻、勤怠記録、QRコードを管理するReact Queryフック
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getTodayAttendance,
  getMyMonthlyAttendances,
  getMyQRCode,
  clockIn,
  clockOut,
  type AttendanceRecord,
  type StaffQRCodeInfo,
  type ClockInRequest,
  type ClockOutRequest,
  type ClockResponse,
} from '@/lib/api/hr';
import { getTodayLessons, type StaffLessonSchedule } from '@/lib/api/lessons';

// クエリキー
export const attendanceKeys = {
  all: ['attendance'] as const,
  today: () => [...attendanceKeys.all, 'today'] as const,
  monthly: (year?: number, month?: number) =>
    [...attendanceKeys.all, 'monthly', year, month] as const,
  qrCode: () => [...attendanceKeys.all, 'qrCode'] as const,
  todayLessons: () => [...attendanceKeys.all, 'todayLessons'] as const,
};

/**
 * 今日の勤怠記録を取得
 */
export function useTodayAttendance() {
  return useQuery({
    queryKey: attendanceKeys.today(),
    queryFn: async () => {
      return getTodayAttendance();
    },
    enabled: !!getAccessToken(),
    staleTime: 30 * 1000, // 30秒
    refetchInterval: 60 * 1000, // 1分ごとに再取得
  });
}

/**
 * 月別勤怠記録を取得
 */
export function useMonthlyAttendances(year?: number, month?: number) {
  return useQuery({
    queryKey: attendanceKeys.monthly(year, month),
    queryFn: async () => {
      return getMyMonthlyAttendances(year, month);
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 自分のQRコードを取得
 */
export function useMyQRCode() {
  return useQuery({
    queryKey: attendanceKeys.qrCode(),
    queryFn: async () => {
      return getMyQRCode();
    },
    enabled: !!getAccessToken(),
    staleTime: 30 * 60 * 1000, // 30分
  });
}

/**
 * 今日の授業一覧を取得
 */
export function useTodayLessons() {
  return useQuery({
    queryKey: attendanceKeys.todayLessons(),
    queryFn: async () => {
      return getTodayLessons();
    },
    enabled: !!getAccessToken(),
    staleTime: 5 * 60 * 1000, // 5分
  });
}

/**
 * 出勤打刻
 */
export function useClockIn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data?: ClockInRequest) => {
      return clockIn(data);
    },
    onSuccess: () => {
      // 今日の勤怠と月別勤怠を再取得
      queryClient.invalidateQueries({ queryKey: attendanceKeys.today() });
      queryClient.invalidateQueries({ queryKey: attendanceKeys.monthly() });
    },
  });
}

/**
 * 退勤打刻
 */
export function useClockOut() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data?: ClockOutRequest) => {
      return clockOut(data);
    },
    onSuccess: () => {
      // 今日の勤怠と月別勤怠を再取得
      queryClient.invalidateQueries({ queryKey: attendanceKeys.today() });
      queryClient.invalidateQueries({ queryKey: attendanceKeys.monthly() });
    },
  });
}

/**
 * 勤怠関連キャッシュを無効化
 */
export function useInvalidateAttendance() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
  };
}

// 型を再エクスポート
export type {
  AttendanceRecord,
  StaffQRCodeInfo,
  ClockInRequest,
  ClockOutRequest,
  ClockResponse,
} from '@/lib/api/hr';
export type { StaffLessonSchedule } from '@/lib/api/lessons';

'use client';

/**
 * useSchedules - 授業スケジュール取得フック
 *
 * スタッフ向け授業スケジュール管理のReact Queryフック
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/api/client';
import {
  getStaffLessonSchedules,
  getStaffLessonScheduleDetail,
  getStaffCalendarSchedules,
  getTodayLessons,
  getWeekLessons,
  type StaffLessonSchedule,
  type StaffCalendarEvent,
  type StaffScheduleSearchParams,
} from '@/lib/api/lessons';

// クエリキー
export const scheduleKeys = {
  all: ['schedules'] as const,
  lists: () => [...scheduleKeys.all, 'list'] as const,
  list: (filters?: StaffScheduleSearchParams) =>
    [...scheduleKeys.lists(), filters] as const,
  details: () => [...scheduleKeys.all, 'detail'] as const,
  detail: (id: string) => [...scheduleKeys.details(), id] as const,
  calendar: (params: { year: number; month: number; instructorId?: string; schoolId?: string; courseId?: string }) =>
    [...scheduleKeys.all, 'calendar', params] as const,
  today: () => [...scheduleKeys.all, 'today'] as const,
  week: () => [...scheduleKeys.all, 'week'] as const,
};

/**
 * 授業スケジュール一覧を取得（スタッフ向け）
 */
export function useStaffSchedules(params?: StaffScheduleSearchParams) {
  return useQuery({
    queryKey: scheduleKeys.list(params),
    queryFn: async () => {
      const response = await getStaffLessonSchedules(params);
      return {
        schedules: response.results || [],
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
 * 授業スケジュール詳細を取得
 */
export function useStaffSchedule(scheduleId: string | undefined) {
  return useQuery({
    queryKey: scheduleKeys.detail(scheduleId || ''),
    queryFn: async () => {
      if (!scheduleId) throw new Error('Schedule ID is required');
      return getStaffLessonScheduleDetail(scheduleId);
    },
    enabled: !!scheduleId && !!getAccessToken(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * カレンダー形式でスケジュールを取得
 */
export function useStaffCalendar(params: {
  year: number;
  month: number;
  instructorId?: string;
  schoolId?: string;
  courseId?: string;
}) {
  return useQuery({
    queryKey: scheduleKeys.calendar(params),
    queryFn: async () => {
      return getStaffCalendarSchedules(params);
    },
    enabled: !!getAccessToken(),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * 今日の授業一覧を取得
 */
export function useTodayLessons() {
  return useQuery({
    queryKey: scheduleKeys.today(),
    queryFn: async () => {
      return getTodayLessons();
    },
    enabled: !!getAccessToken(),
    staleTime: 1 * 60 * 1000, // 1分（今日のデータは頻繁に更新される可能性）
  });
}

/**
 * 今週の授業一覧を取得
 */
export function useWeekLessons() {
  return useQuery({
    queryKey: scheduleKeys.week(),
    queryFn: async () => {
      return getWeekLessons();
    },
    enabled: !!getAccessToken(),
    staleTime: 2 * 60 * 1000,
  });
}

/**
 * スケジュールキャッシュを無効化
 */
export function useInvalidateSchedules() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries({ queryKey: scheduleKeys.all });
  };
}

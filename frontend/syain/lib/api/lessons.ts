/**
 * Lessons API
 * 授業・スケジュール関連のAPI関数
 */

import api from './client';
import type { PaginatedResponse } from './types';

// 授業ステータス型
export type LessonStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

// 予約ステータス型
export type ReservationStatus = 'pending' | 'confirmed' | 'attended' | 'absent' | 'cancelled';

// 授業スケジュール型
export interface LessonSchedule {
  id: string;
  courseId: string;
  course: {
    id: string;
    name: string;
    shortName?: string;
    category: string;
    ticketCost: number;
    durationMinutes?: number;
  };
  instructorId?: string;
  instructor?: {
    id: string;
    fullName: string;
    profileImageUrl?: string;
  };
  schoolId: string;
  school: {
    id: string;
    name: string;
    shortName?: string;
  };
  scheduledDate: string;
  startTime: string;
  endTime: string;
  capacity?: number;
  currentEnrollment: number;
  status: LessonStatus;
  notes?: string;
  createdAt: string;
}

// 予約型
export interface Reservation {
  id: string;
  studentId: string;
  student: {
    id: string;
    user: {
      id: string;
      fullName: string;
    };
    grade?: string;
  };
  lessonScheduleId: string;
  lessonSchedule?: LessonSchedule;
  bookedById: string;
  bookedBy: {
    id: string;
    fullName: string;
  };
  status: ReservationStatus;
  ticketUsed?: string;
  checkInAt?: string;
  checkOutAt?: string;
  notes?: string;
  createdAt: string;
}

// カレンダーイベント型
export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  status: LessonStatus;
  courseName: string;
  instructorName?: string;
  schoolName: string;
  currentEnrollment: number;
  capacity?: number;
  color?: string;
}

// スケジュール検索パラメータ型
export interface ScheduleSearchParams {
  page?: number;
  pageSize?: number;
  startDate?: string;
  endDate?: string;
  instructorId?: string;
  schoolId?: string;
  courseId?: string;
  status?: string;
}

// カレンダー検索パラメータ型
export interface CalendarSearchParams {
  year: number;
  month: number;
  instructorId?: string;
  schoolId?: string;
  courseId?: string;
}

/**
 * 授業スケジュール一覧取得
 */
export async function getLessonSchedules(
  params?: ScheduleSearchParams
): Promise<PaginatedResponse<LessonSchedule>> {
  const queryParams = new URLSearchParams();

  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params?.startDate) queryParams.append('start_date', params.startDate);
  if (params?.endDate) queryParams.append('end_date', params.endDate);
  if (params?.instructorId) queryParams.append('instructor_id', params.instructorId);
  if (params?.schoolId) queryParams.append('school_id', params.schoolId);
  if (params?.courseId) queryParams.append('course_id', params.courseId);
  if (params?.status) queryParams.append('status', params.status);

  const query = queryParams.toString();
  const endpoint = `/lessons/schedules/${query ? `?${query}` : ''}`;

  return api.get<PaginatedResponse<LessonSchedule>>(endpoint);
}

/**
 * 授業スケジュール詳細取得
 */
export async function getLessonSchedule(id: string): Promise<LessonSchedule> {
  return api.get<LessonSchedule>(`/lessons/schedules/${id}/`);
}

/**
 * カレンダー形式でスケジュール取得
 */
export async function getCalendarSchedules(
  params: CalendarSearchParams
): Promise<CalendarEvent[]> {
  const queryParams = new URLSearchParams();

  queryParams.append('year', params.year.toString());
  queryParams.append('month', params.month.toString());
  if (params.instructorId) queryParams.append('instructor_id', params.instructorId);
  if (params.schoolId) queryParams.append('school_id', params.schoolId);
  if (params.courseId) queryParams.append('course_id', params.courseId);

  const query = queryParams.toString();
  return api.get<CalendarEvent[]>(`/lessons/schedules/calendar/?${query}`);
}

/**
 * 授業の予約一覧取得
 */
export async function getLessonReservations(
  lessonId: string
): Promise<Reservation[]> {
  return api.get<Reservation[]>(`/lessons/schedules/${lessonId}/reservations/`);
}

/**
 * 予約作成
 */
export interface CreateReservationRequest {
  studentId: string;
  lessonScheduleId: string;
  notes?: string;
}

export async function createReservation(
  data: CreateReservationRequest
): Promise<Reservation> {
  return api.post<Reservation>('/lessons/reservations/', data);
}

/**
 * 予約キャンセル
 */
export interface CancelReservationRequest {
  reason?: string;
}

export async function cancelReservation(
  reservationId: string,
  data?: CancelReservationRequest
): Promise<Reservation> {
  return api.post<Reservation>(`/lessons/reservations/${reservationId}/cancel/`, data);
}

/**
 * 出席記録
 */
export interface AttendanceRequest {
  status: 'present' | 'absent' | 'late' | 'excused';
  notes?: string;
}

export async function recordAttendance(
  reservationId: string,
  data: AttendanceRequest
): Promise<Reservation> {
  return api.post<Reservation>(`/lessons/reservations/${reservationId}/attendance/`, data);
}

/**
 * 今日の授業一覧取得（講師用）
 */
export async function getTodayLessons(): Promise<LessonSchedule[]> {
  const today = new Date().toISOString().split('T')[0];
  const response = await getLessonSchedules({
    startDate: today,
    endDate: today,
    pageSize: 100,
  });
  return response.results;
}

/**
 * 今週の授業一覧取得
 */
export async function getWeekLessons(): Promise<LessonSchedule[]> {
  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay());
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);

  const response = await getLessonSchedules({
    startDate: startOfWeek.toISOString().split('T')[0],
    endDate: endOfWeek.toISOString().split('T')[0],
    pageSize: 100,
  });
  return response.results;
}

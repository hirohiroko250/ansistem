/**
 * HR (Human Resources) API
 * 勤怠・人事関連のAPI関数
 */

import api from './client';
import type { PaginatedResponse } from './types';

// 勤怠ステータス型
export type AttendanceStatus = 'working' | 'completed' | 'absent' | 'leave' | 'holiday';

// 勤怠記録型
export interface AttendanceRecord {
  id: string;
  userId: string;
  user?: {
    id: string;
    fullName: string;
    email?: string;
  };
  date: string;
  clockInTime?: string;
  clockOutTime?: string;
  breakMinutes?: number;
  workMinutes?: number;
  overtimeMinutes?: number;
  status: AttendanceStatus;
  schoolId?: string;
  school?: {
    id: string;
    name: string;
    shortName?: string;
  };
  dailyReport?: string;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

// 勤怠サマリー型
export interface AttendanceSummary {
  userId: string;
  year: number;
  month: number;
  totalWorkDays: number;
  totalWorkMinutes: number;
  totalOvertimeMinutes: number;
  totalBreakMinutes: number;
  absentDays: number;
  leaveDays: number;
  averageWorkMinutes: number;
}

// 打刻レスポンス型
export interface ClockResponse {
  id: string;
  clockInTime?: string;
  clockOutTime?: string;
  status: AttendanceStatus;
  message: string;
}

// 検索パラメータ型
export interface AttendanceSearchParams {
  page?: number;
  pageSize?: number;
  userId?: string;
  startDate?: string;
  endDate?: string;
  status?: string;
  schoolId?: string;
}

/**
 * 勤怠一覧取得
 */
export async function getAttendances(
  params?: AttendanceSearchParams
): Promise<PaginatedResponse<AttendanceRecord>> {
  const queryParams = new URLSearchParams();

  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params?.userId) queryParams.append('user_id', params.userId);
  if (params?.startDate) queryParams.append('start_date', params.startDate);
  if (params?.endDate) queryParams.append('end_date', params.endDate);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.schoolId) queryParams.append('school_id', params.schoolId);

  const query = queryParams.toString();
  const endpoint = `/hr/attendances/${query ? `?${query}` : ''}`;

  return api.get<PaginatedResponse<AttendanceRecord>>(endpoint);
}

/**
 * 勤怠詳細取得
 */
export async function getAttendance(id: string): Promise<AttendanceRecord> {
  return api.get<AttendanceRecord>(`/hr/attendances/${id}/`);
}

/**
 * 今日の勤怠状況取得
 */
export async function getTodayAttendance(): Promise<AttendanceRecord | null> {
  try {
    return await api.get<AttendanceRecord>('/hr/attendances/today/');
  } catch (err: any) {
    if (err.status === 404) {
      return null;
    }
    throw err;
  }
}

/**
 * 出勤打刻
 */
export interface ClockInRequest {
  schoolId?: string;
  qrCode?: string;
  latitude?: number;
  longitude?: number;
  notes?: string;
}

export async function clockIn(data?: ClockInRequest): Promise<ClockResponse> {
  return api.post<ClockResponse>('/hr/attendances/clock_in/', data);
}

/**
 * 退勤打刻
 */
export interface ClockOutRequest {
  dailyReport?: string;
  qrCode?: string;
  latitude?: number;
  longitude?: number;
  notes?: string;
}

export async function clockOut(data?: ClockOutRequest): Promise<ClockResponse> {
  return api.post<ClockResponse>('/hr/attendances/clock_out/', data);
}

/**
 * 休憩開始
 */
export async function startBreak(): Promise<ClockResponse> {
  return api.post<ClockResponse>('/hr/attendances/break_start/');
}

/**
 * 休憩終了
 */
export async function endBreak(): Promise<ClockResponse> {
  return api.post<ClockResponse>('/hr/attendances/break_end/');
}

/**
 * 日報更新
 */
export interface UpdateDailyReportRequest {
  dailyReport: string;
}

export async function updateDailyReport(
  attendanceId: string,
  data: UpdateDailyReportRequest
): Promise<AttendanceRecord> {
  return api.patch<AttendanceRecord>(`/hr/attendances/${attendanceId}/`, {
    dailyReport: data.dailyReport,
  });
}

/**
 * 月別勤怠サマリー取得
 */
export async function getAttendanceSummary(
  year: number,
  month: number
): Promise<AttendanceSummary> {
  return api.get<AttendanceSummary>(`/hr/attendances/summary/?year=${year}&month=${month}`);
}

/**
 * 自分の今月の勤怠一覧取得
 */
export async function getMyMonthlyAttendances(
  year?: number,
  month?: number
): Promise<AttendanceRecord[]> {
  const now = new Date();
  const targetYear = year || now.getFullYear();
  const targetMonth = month || now.getMonth() + 1;

  const startDate = `${targetYear}-${String(targetMonth).padStart(2, '0')}-01`;
  const lastDay = new Date(targetYear, targetMonth, 0).getDate();
  const endDate = `${targetYear}-${String(targetMonth).padStart(2, '0')}-${lastDay}`;

  const response = await getAttendances({
    startDate,
    endDate,
    pageSize: 31,
  });

  return response.results;
}

/**
 * 勤務時間をフォーマット（分 → 時間:分）
 */
export function formatWorkTime(minutes: number | undefined): string {
  if (!minutes) return '0:00';
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}:${String(mins).padStart(2, '0')}`;
}
